# -*- coding: utf-8 -*-
"""
Created on Sat Jan 23 15:50:48 2021

@author: SCOURT01

Automated analysis of Gate simulation output:
  - Check of data integrity
  - Merging all results
  - Any post-sim corrections (i.e. Offset field in mhd file)
  - Scaling for absolute dose
  - Conversion of dose-to-material to dose-to-water
  - Conversion from mhd/raw to dicom for import into TPS
  
  TODO
  - Gamma analysis

"""
import sys
import os

import easygui
import itk

import config
import mergeresults
import dosetowater
import dosetodicom



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
                file = os.path.join(outputdir,f)
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
    """Set mhd TransformMatrix to that of original CT for all files in list
    
    Have to do this since Gate will write couch kicks here
    """
    
    transform = config.get_transform_matrix( outputdir )
    
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

    ## check_integrity( outputdir )  #TODO
    
    fieldnames = get_field_names( outputdir )
    print("Fields found: ", fieldnames)
    
    for field in fieldnames:
        
        print("Analyzing field: ", field)

        # Merge all results and return list of files produced
        mergedfiles = mergeresults.merge_results( outputdir, field )
        print("  Merging results...")
        print("  Merged files: ", [os.path.basename(f) for f in mergedfiles])
        
        print("  Correcting mhd TransformMatrix in merged files")
        correct_transform_matrix(mergedfiles)
        
        # TODO #### Perhaps only necessary if using the mhd?
        #   Could ignore if we just deal with dicom doses (gamma analysis)?
        # print("  Correcting mhd Offset in merged files")
        # correct_offwet(mergedfiles)
                
        nsim = count_prims_simulated( outputdir, field )
        nreq = config.get_req_prims( outputdir, field )
        scalefactor = nreq / nsim
        
        print("  Primaries simulated: ",nsim)
        print("  Primaries required: ",nreq)
        print("  Dose scaling: ",scalefactor)
        
        dose = field+"_merged-Dose.mhd"
        if dose in [os.path.basename(f) for f in mergedfiles]:
            print("  Scaling merged-Dose.mhd")
            doseimg = os.path.join(outputdir, dose)
            scaledimg = os.path.join(outputdir, field+"_AbsoluteDose.mhd")
            write_scaled_dose( doseimg, scaledimg, scalefactor )
            
            print("  Converting dose2material to dose2water")
            ctpath = config.get_ct_path( outputdir )
            ##ctpath = os.path.join( outputdir, ctname )
            d2wimg = os.path.join(outputdir, field+"_AbsoluteDoseToWater.mhd")
            dosetowater.convert_dose_to_water( ctpath, scaledimg, output=d2wimg )
            
            print("  Converting mhd dose to dicom")
            beamref = config.get_beam_ref_no( outputdir, field )
            print("    beam_ref_no = ",beamref)
            path_to_dcmdose = dosetodicom.get_dcm_file_path( outputdir, beamref )
            ##print("XXX ", path_to_dcmdose)
            dcm_out = os.path.join(outputdir, field+"_AbsoluteDoseToWater.dcm")
            dosetodicom.mhd2dcm( d2wimg, path_to_dcmdose, dcm_out )
            
            
        dose2water = field+"_merged-DoseToWater.mhd"
        if dose2water in [os.path.basename(f) for f in mergedfiles]:
            print("  Scaling merged-DoseToWater.mhd")
            doseimg = os.path.join(outputdir, dose2water)
            outname = os.path.join(outputdir, field+"_Gate_DoseToWater.mhd")
            write_scaled_dose( doseimg, outname, scalefactor )

        

        
        
        
        
        
        
        
    
        
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
    
    
    
    