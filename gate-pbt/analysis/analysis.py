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
import easygui

import mergeresults
import dosetowater



def check_integrity( outputdir ):
    """
    """


def get_field_names( outputdir ):
    pass




def analyze_all( outputdir ):
    """Automated analysis of all Gate output in specified directory
    """ 
    
    check_integrity( outputdir )
    fieldnames = get_field_names( outputdir )
    
    for field in fieldnames:
        
        print("Analyzing field: ".format(field))

        mergedfiles = mergeresults.merge_results( outputdir, field )
        
        
        
        nsim = count_prims_simulated( outputdir, field )
        nreq = get_prims_required( field )
        dose_scale = nreq / nsim
        
        
        scale_dose( mergedfiles, dose_scale )
        
        dosetowater.convert_dose_to_water( ctimg, dosemhd )
        
        makedcmdose.mhd2dcm( mhdfile, dcmtemplate )
        
        
        
        
        
        
        
    
        
if __name__=="__main__":
    
    # Select directory containing Gate output
    msg = "Select directory containing Gate output files"
    title = "SELECT DIRECTORY"
    if easygui.ccbox(msg, title):
        pass
    else:
        sys.exit(0)
    
    outputdir = easygui.diropenbox()
    analyze_all( outputdir )
    
    
    
    