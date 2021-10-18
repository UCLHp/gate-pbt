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
##from pathlib import Path

import easygui
import itk

#import config
import mergeresults
#import dosetowater
import mhdtodicom
import dicomtomhd
import gamma




def count_prims_simulated( outputdir ):
    """Count primaries actually simulated from stat files"""
    filelist = os.listdir(outputdir)
    tot = 0
    for f in filelist:
        if "stat" in f:
            file = join(outputdir,f)
            lines = open(file).readlines()
            for line in lines:
                if "NumberOfEvents" in line:
                    prims = int(line.split("=")[1].strip())
                    tot += prims
    if tot<=0:
        print("  ERROR; no simulated primaries in ", outputdir)
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
                    
                    


def full_analysis( outputdir, dcmdose, required_primaries ):
    """Automated analysis of all Gate output in specified directory
    """ 

    print("  Merging results...")
    mergedfiles = mergeresults.merge_results( outputdir )
    print("  Merged files: ", [basename(f) for f in mergedfiles])
    
    #print("  Correcting mhd TransformMatrix in merged files")
    #correct_transform_matrix(mergedfiles)
            
    nsim = count_prims_simulated( outputdir )
    nreq = required_primaries
    nfractions = 1
 
    scalefactor = (nreq / nsim) * nfractions * 1.1
    
    print("  Primaries simulated: ",nsim)
    print("  Primaries required: ",nreq)
    print("  Fractions planned: ",nfractions)
    
    dose = "_merged-Dose.mhd"
    if dose in [basename(f) for f in mergedfiles]:
        print("  Scaling merged-Dose.mhd")
        doseimg = join(outputdir, dose)
        scaledimg = join(outputdir, "_AbsoluteDose.mhd")
        write_scaled_dose( doseimg, scaledimg, scalefactor )
        
        print("  Converting mhd dose to dicom")
        dcm_out = join(outputdir, "_AbsoluteDose.dcm")
        mhdtodicom.mhd2dcm( scaledimg, dcmdose, dcm_out )
         
       
        print("  Performing gamma analysis")
        tps_dose = dicomtomhd.dcm2mhd( dcmdose ) 
        gamma_img = gamma.gamma_image(  doseimg, tps_dose )
        itk.imwrite(gamma_img, join(outputdir, "_Gamma.mhd") )
        pass_rate = gamma.get_pass_rate( gamma_img )
        print("    gamma pass rate = {}%".format( round(pass_rate,2) ))
        #
        # Make dcm for gamnma image for visualizaiton
        print("  Converting gamma image to dicom")
        gamma_dcm = join(outputdir, "_Gamma.dcm")
        mhdtodicom.mhd2dcm( gamma_img, dcmdose, gamma_dcm )

            
    
        
if __name__=="__main__":
    
    # Select directory containing Gate output
    msg = "Select directory containing Gate output files"
    title = "SELECT DIRECTORY"
    if easygui.ccbox(msg, title):
        pass
    else:
        sys.exit(0)   
    outputdir = easygui.diropenbox()
    
    
    msg = "Select Eclipse dicom file"
    title = "SELECT FILE"
    dcmdose = easygui.fileopenbox(msg, title)

    
    #required_prims = 206583036427  ## NPL10 208791165462 (beam v1);  ## v2 nmu: 206583036427  
    required_prims = 221090286688  ## NPL 15 (V2 NMU)
    #required_prims = 259240843968   ## NPL25: 261854664857 (beam v1) 259240843968 for IDD normalized by area!
    #required_prims = 19116584729   ## DDNCF 10x02_layer1
    #required_prims = 23664065433   ## DDCNF 20x02_layer1
    #required_prims = 1978059663    ## Single spot 174.857
    
    # 5x5x5 boxes
    #required_prims = 75885464957  ## RS0
    #required_prims = 94286383964## RS2
    #required_prims = 104246069296## RS3
    #required_prims = 120324803109## RS5
    
    full_analysis( outputdir, dcmdose, required_prims )
    
    
    
    