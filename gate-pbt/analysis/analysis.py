# -*- coding: utf-8 -*-
"""
@author: Steven Court
Automated analysis of Gate simulation output:
  - Check of data integrity
  - Merging all results
  - Any post-sim corrections (i.e. Offset field in mhd file)
  - Scaling for absolute dose
  - Conversion of dose-to-material to dose-to-water
  - Conversion from mhd/raw to dicom for import into TPS
"""

import sys
import os
from os.path import join, basename
from pathlib import Path

import easygui
import itk

import config
import mergeresults
import dosetowater
import mhdtodicom
import dicomtomhd
import gamma



def check_integrity( outputdir ):
    """
    TODO
    """
    pass


def get_field_names( outputdir ):
    """Return fieldnames contained in directory
    Corresponds to first part of filename_xx_xx.mhd
    """
    fieldnames = []    
    filelist = os.listdir(outputdir)
    for entry in filelist:
        name = entry.split("_")[0]
        if name not in fieldnames:
            fieldnames.append(name)                
    return fieldnames
    

def count_prims_simulated( outputdir, field ):
    """Count primaries actually simulated from stat files"""
    filelist = os.listdir(outputdir)
    tot = 0
    for f in filelist:
        if "stat-pat.txt" in f:
            if field in f:
                file = join(outputdir,f)
                lines = open(file).readlines()
                for line in lines:
                    if "NumberOfEvents" in line:
                        prims = int(line.split("=")[1].strip())
                        tot += prims
    if tot<=0:
        print("  ERROR; no simulated primaries in ", field, outputdir)
        exit(3)
    return tot
    


def write_scaled_dose( mhdfile, output, scalefactor):
    """Scale provided dose image and save to output"""
    img = itk.imread(mhdfile)
    dose = itk.array_from_image( img )
    dosescaled = dose * scalefactor
    newimg = itk.image_view_from_array( dosescaled )
    newimg.CopyInformation(img)
    itk.imwrite(newimg,output)
    


def correct_transform_matrix( mergedfiles ):
    """Set mhd TransformMatrix to 100010001 for all files in list
    Have to do this since Gate will write couch kicks here
    """  
    # In preparation stage we ensure all images are oriented as 100010001 
    transform = "1 0 0 0 1 0 0 0 1"   
    for mf in mergedfiles:
        file = open(mf, "r")
        lines = file.readlines()
        file.close()
        with open(mf,"w") as out:
            for line in lines:
                if "TransformMatrix" in line:
                    out.write("TransformMatrix = {}\n".format(transform))
                else:
                    out.write(line)
                    
                    


def full_analysis( outputdir ):
    """Automated analysis of all Gate output in specified directory
    """ 
    print("\nData directory: ",outputdir)


    # Get absolute path to template/data files
    base_path = Path(__file__).parent
    path_to_templates = (base_path / "../../data/templates").resolve()
    
    #TODO: read this from config file
    material_db = "patient-HUmaterials_UCLHv1.db"
    material_db_path = join(path_to_templates, material_db)

    ## check_integrity( outputdir )  #TODO
        
    fieldnames = get_field_names( outputdir )
    print("Fields found: ", fieldnames)
    
    for field in fieldnames:
        
        print("Analyzing field: ", field)

        print("  Merging results...")
        mergedfiles = mergeresults.merge_results( outputdir, field )
        print("  Merged files: ", [basename(f) for f in mergedfiles])
        
        print("  Correcting mhd TransformMatrix in merged files")
        correct_transform_matrix(mergedfiles)
                
        nsim = count_prims_simulated( outputdir, field )
        nreq = config.get_req_prims( outputdir, field )
        nfractions = config.get_fractions( outputdir )
        
        scalefactor = (nreq / nsim) * nfractions  ## * 1.1 ## For RBE
        
        print("  Primaries simulated: ",nsim)
        print("  Primaries required: ",nreq)
        print("  Fractions planned: ",nfractions)
        
        dose = field+"_merged-Dose.mhd"
        if dose in [basename(f) for f in mergedfiles]:
            print("  Scaling merged-Dose.mhd")
            doseimg = join(outputdir, dose)
            scaledimg = join(outputdir, field+"_AbsoluteDose.mhd")
            write_scaled_dose( doseimg, scaledimg, scalefactor )
            
            print("  Converting dose2material to dose2water")
            ctpath = config.get_ct_path( outputdir )
            ##ctpath = os.path.join( outputdir, ctname )
            d2wimg = join(outputdir, field+"_AbsoluteDoseToWater.mhd")
            dosetowater.convert_dose_to_water( ctpath, scaledimg, material_db_path, output=d2wimg )
            
            print("  Converting mhd dose to dicom")
            beamref = config.get_beam_ref_no( outputdir, field )
            print("    beam_ref_no = ",beamref)
            path_to_dcmdose = mhdtodicom.get_dcm_file_path( outputdir, beamref )
            ##print("XXX ", path_to_dcmdose)
            dcm_out = join(outputdir, field+"_AbsoluteDoseToWater.dcm")
            mhdtodicom.mhd2dcm( d2wimg, path_to_dcmdose, dcm_out )
                     
            print("  Performing gamma analysis")
            tps_dose = dicomtomhd.dcm2mhd( path_to_dcmdose ) 
            gamma_img = gamma.gamma_image(  d2wimg, tps_dose )
            itk.imwrite(gamma_img, join(outputdir, field+"_Gamma.mhd") )
            pass_rate = gamma.get_pass_rate( gamma_img )
            print("    gamma pass rate = {}%".format( round(pass_rate,2) ))
            #
            # Make dcm for gamnma image for visualizaiton
            print("  Converting gamma image to dicom")
            gamma_dcm = join(outputdir, field+"_Gamma.dcm")
            mhdtodicom.mhd2dcm( gamma_img, path_to_dcmdose, gamma_dcm )

            
            
        dose2water = field+"_merged-DoseToWater.mhd"
        if dose2water in [basename(f) for f in mergedfiles]:
            print("  Scaling merged-DoseToWater.mhd")
            doseimg = join(outputdir, dose2water)
            scaledimg = join(outputdir, field+"_Gate_DoseToWater.mhd")
            write_scaled_dose( doseimg, scaledimg, scalefactor )
            
            print("  Converting Gate dose-to-water to dicom")
            beamref = config.get_beam_ref_no( outputdir, field )
            path_to_dcmdose = mhdtodicom.get_dcm_file_path( outputdir, beamref )
            ##print("XXX ", path_to_dcmdose)
            dcm_out = join(outputdir, field+"_Gate_DoseToWater.dcm")
            mhdtodicom.mhd2dcm( scaledimg, path_to_dcmdose, dcm_out )

        

        
        
        
        
        
        
        
    
        
if __name__=="__main__":
    
    # Select directory containing Gate output
    msg = "Select directory containing Gate output files"
    title = "SELECT DIRECTORY"
    if easygui.ccbox(msg, title):
        pass
    else:
        sys.exit(0)
    
    outputdir = easygui.diropenbox()
    full_analysis( outputdir )
    
    
    
    