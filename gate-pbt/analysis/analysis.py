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
from os.path import join, basename, dirname
import re

import easygui
import itk

import config
import mergeresults
import dosetowater
import mhdtodicom
import dicomtomhd
import gamma
import overrides
from uncertainty_stats import getUncertaintyPlots



def check_integrity( outputdir ):
    """
    TODO
    """
    pass


#def get_field_names( outputdir ):
#    """Return fieldnames contained in directory
#    Corresponds to first part of filename_xx_xx.mhd
#    """
#    fieldnames = []    
#    filelist = os.listdir(outputdir)
#    for entry in filelist:
#        name = entry.split("_")[0]
#        if name not in fieldnames:
#            fieldnames.append(name)
#
#    fieldnames = ["G280_T10_RS0","G80_T270_RS0","G80_T345_RS0"]             
#    return fieldnames
    

def count_prims_simulated( outputdir, field ):
    """Count primaries actually simulated from stat files"""
    filelist = os.listdir(outputdir)
    tot = 0
    for f in filelist:
        if re.search(field+"_\d+(_stat-pat\.txt)",f):
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
    """Scale provided dose image/path and save to output"""   
    img = None 
    if type(mhdfile)==str:
        #Assume we have file path
        img = itk.imread( mhdfile )
    else:
        #Assume we have itk image object
        img = mhdfile       
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


def apply_mask(doseimage, mask):
    """ Element-wise multiplication of dose image and structure mask 
    
    Accepts either file paths or ITK image objects as input
    """
    di = None 
    if type(doseimage)==str:
        di = itk.imread( doseimage )
    else:
        di = doseimage      
    mi = None 
    if type(mask)==str:
        mi = itk.imread( mask )
    else:
        mi = mask      
    
    d = itk.array_view_from_image(di)     
    m = itk.array_view_from_image(mi)
    if( d.shape != m.shape ):
        print( "apply mask: inconsistent shapes of mask and image"  )     
    df = m*d
    df_img = itk.image_view_from_array( df )
    df_img.CopyInformation(di)
    
    return df_img                  
                    


def full_analysis( outputdir ):
    """Automated analysis of all Gate output in specified directory
    """ 
    print("\nData directory: ",outputdir)

    # Get absolute path to simulation data files      ## HARD CODED FIX
    parentdir = dirname(outputdir)   
    #TODO: read this from config file
    hu2matfile = "PhilipsBody-HU2mat.txt"
    #hu2matfile = "PSQA-HU2mat.txt"
    emcalc = "emcalc.txt"
    hu2mat_path = join(parentdir,"data",hu2matfile)
    emcalc_path = join(parentdir,"data",emcalc)
    
    ## check_integrity( outputdir )  #TODO
        
    #fieldnames = get_field_names( outputdir )
    fieldnames = config.get_beam_names( outputdir )
    
    
    print("Fields found: ", fieldnames)
    for field in fieldnames:

      
            
        print("\nAnalyzing field: ", field)

        print("  Merging results...")
        mergedfiles = mergeresults.merge_results( outputdir, field )
        print("  Merged files: ", [basename(f) for f in mergedfiles])
        
        print("  Correcting mhd TransformMatrix in merged files")
        correct_transform_matrix(mergedfiles)
                
        nsim = count_prims_simulated( outputdir, field )
        nreq = config.get_req_prims( outputdir, field )
        nfractions = config.get_fractions( outputdir )
        
        scalefactor = (nreq / nsim) * nfractions * 1.1   ## RBE
        
        print("  Primaries simulated: ",nsim)
        print("  Primaries required: ",nreq)
        print("  Fractions planned: ",nfractions)
        
        
        beamref = config.get_beam_ref_no( outputdir, field )
        print("    beam_ref_no = ",beamref)

        
        path_to_dcmdose = mhdtodicom.get_dcm_file_path( outputdir, beamref )
        tps_dose = dicomtomhd.dcm2mhd( path_to_dcmdose )      
        print("  Overriding TPS outside of zSurface to zero for gamma analysis")
        struct_file = mhdtodicom.get_struct_file_path( outputdir )
        tps_dose = overrides.set_external_dose_zero( tps_dose, struct_file, "zSurface" )    ## hard-coded
        
        
        dose = field+"_merged-Dose.mhd"
        if dose in [basename(f) for f in mergedfiles]:
            print("\n")
            print("  Scaling merged-Dose.mhd")
            doseimg_path = join(outputdir, dose)       
            # Read DoseMask to set dose outside zSurface to zero
            dosemask = itk.imread(join(parentdir,"data","DoseMask.mhd"))  # TODO; read from config file
            # Resample dosemask to dose grid resolution - Alternative is just to generate the mask here
            dosemask = dosetowater.resample_nn( dosemask, itk.imread(doseimg_path)  )
            itk.imwrite(dosemask, "resampled_dosemask.mhd")
            # Apply mask to zSurface          
            doseimg = apply_mask(doseimg_path, dosemask)  
                     
            scaledimg_path = join(outputdir, field+"_AbsoluteDose.mhd")
            write_scaled_dose( doseimg, scaledimg_path, scalefactor )
                      
            print("  Converting dose2material to dose2water")
            ctpath = config.get_ct_path( outputdir )
            ##ctpath = os.path.join( outputdir, ctname )
            d2wimg = join(outputdir, field+"_AbsoluteDoseToWater.mhd")
            dosetowater.convert_dose_to_water( ctpath, scaledimg_path, emcalc_path, hu2mat_path, output=d2wimg )
            
            print("  Converting mhd dose to dicom")
            dcm_out = join(outputdir, field+"_AbsoluteDoseToWater.dcm")
            mhdtodicom.mhd2dcm( d2wimg, path_to_dcmdose, dcm_out )
            
            
            ### Override dose outside of patient contour ###
            # Means in Mephysto use panel A (targ) for Eclipse; B (ref) for MC dose
            #print("  Overriding dose outside of body to zero for gamma analysis")
            #struct_file = mhdtodicom.get_struct_file_path( outputdir )
            #body = overrides.get_external_name( struct_file )
            #dose_none_ext = overrides.set_external_dose_zero( d2wimg, struct_file, body )
            #path_to_none_ext =  join(outputdir, field+"_DoseToWater_NoneExt.mhd" )  
            #itk.imwrite(dose_none_ext, path_to_none_ext)      
            #mhdtodicom.mhd2dcm(dose_none_ext, path_to_dcmdose, join(outputdir, field+"_DoseToWater_NoneExt.dcm") )
   
            #'''
            
            print("  Performing gamma analysis 3%/3mm: post-sim D2W vs Eclipse")
            gamma_img = gamma.gamma_image(  d2wimg, tps_dose, 3, 3 )
            itk.imwrite(gamma_img, join(outputdir, field+"_Gamma_33.mhd") )
            pass_rate = gamma.get_pass_rate( gamma_img )
            print("   *** Gamma pass rate @ 3%/3mm = {}%".format( round(pass_rate,2) ))
            
            # Make dcm for gamma image for visualizaiton
            print("  Converting gamma image to dicom")
            gamma_dcm = join(outputdir, field+"_Gamma_33.dcm")
            mhdtodicom.mhd2dcm( gamma_img, path_to_dcmdose, gamma_dcm )
            
            
            print("  Performing gamma analysis 2%/2mm: post-sim D2W vs Eclipse")
            gamma_img_22 = gamma.gamma_image(  d2wimg, tps_dose, 2, 2 )
            itk.imwrite(gamma_img_22, join(outputdir, field+"_Gamma_22.mhd") )
            pass_rate = gamma.get_pass_rate( gamma_img_22 )
            print("   *** Gamma pass rate @ 2%/2mm = {}%".format( round(pass_rate,2) ))

            #'''

        
        dose2water = field+"_merged-DoseToWater.mhd"
        if dose2water in [basename(f) for f in mergedfiles]:
            print("\n")
            print("  Scaling merged-DoseToWater.mhd")
            doseimg_path = join(outputdir, dose2water)

            
            # Read DoseMask to set dose outside zSurface to zero
            dosemask = itk.imread(join(parentdir,"data","DoseMask.mhd"))  # TODO; read from config file
            # Resample dosemask to dose grid resolution - Alternative is just to generate the mask here
            dosemask = dosetowater.resample_nn( dosemask, itk.imread(doseimg_path)  )
            
            # Apply zSurface mask to dose          
            doseimg = apply_mask(doseimg_path, dosemask)                       
            scaledimg_path = join(outputdir, field+"_Gate_DoseToWater.mhd")
            write_scaled_dose( doseimg, scaledimg_path, scalefactor )

            print("  Converting Gate dose-to-water to dicom")
            dcm_out = join(outputdir, field+"_Gate_DoseToWater.dcm")
            mhdtodicom.mhd2dcm( scaledimg_path, path_to_dcmdose, dcm_out )
            
            print("  Performing gamma analysis for GD2W; 3%/3mm")
            gamma_img = gamma.gamma_image(  scaledimg_path, tps_dose, 3, 3 )                   #### NEED SCALED IMAGE HERE
            itk.imwrite(gamma_img, join(outputdir, field+"_Gamma_GD2W_33.mhd") )
            pass_rate = gamma.get_pass_rate( gamma_img )
            print("   *** Gamma GD2W pass rate @ 3%/3mm = {}%".format( round(pass_rate,2) ))          
            print("  Converting gamma image to dicom")
            gamma_dcm = join(outputdir, field+"_Gamma_GD2W_33.dcm")
        

        # Maybe we add uncertainy metrics here?

        dose = field+"_merged-Uncertainty.mhd"
        if dose in [basename(f) for f in mergedfiles]:
            print("\n")
            print("Calculating uncertainty")
            doseUncert_path = join(outputdir, dose)
            dose2W = d2wimg
            print("Number of Primaries Simulated", nsim)
            results = getUncertaintyPlots(doseUncert_path, dose2W, nsim)
            

        # Dose To Water MHD file
        




        
        let = field+"_merged-LET.mhd"
        if let in [basename(f) for f in mergedfiles]:
            print("  Converting LET img to dicom")
            letimg = join(outputdir, let)
            beamref = config.get_beam_ref_no( outputdir, field )
            path_to_dcmdose = mhdtodicom.get_dcm_file_path( outputdir, beamref )
            dcm_out = join(outputdir, field+"_LET.dcm")
            mhdtodicom.mhd2dcm( letimg, path_to_dcmdose, dcm_out )
            
        
        
        
        
        
        
        
    
        
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
    
    
    
    