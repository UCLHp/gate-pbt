# -*- coding: utf-8 -*-
"""
Created on Fri Jan 10 15:13:07 2020
@author: SCOURT01

Main program to read in all relevant dicom files and 
generate all files required for gate simulation.
"""

import sys
import os
import shutil
from pathlib import Path


import pydicom
import easygui

import imageconversion
import overrides
import generatefiles




def make_gate_dirs(dir_name, path_to_templates):
    """Make dir structure for gate files and copy fixed files"""
    # Make directory tree
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
        os.mkdir( os.path.join(dir_name,"data") )
        os.mkdir( os.path.join(dir_name,"mac") )
        os.mkdir( os.path.join(dir_name,"output") )    
    # Copy over data files
    fs = ["GateMaterials.db","UCLH2019DensitiesTable_v1.txt","UCLH2019MaterialsTable_v1.txt"]
    for f in fs:
        source = os.path.join(path_to_templates,f)  
        destination = os.path.join(dir_name,"data",f)
        shutil.copyfile(source,destination)
    ffs = ["verbose.mac","visu.mac"]
    for f in ffs:
        source = os.path.join(path_to_templates,f)  
        destination = os.path.join(dir_name,"mac",f)  
        shutil.copyfile(source,destination)




def list_all_files(dirName):
    """For the given path, get the List of all files in the directory tree"""
    # Create a list of file and sub-dirs in given dir 
    print(dirName)
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory 
        if os.path.isdir(fullPath):
            allFiles = allFiles + list_all_files(fullPath)
        else:
            allFiles.append(fullPath)
                
    return allFiles



def search_dcm_dir( input_dir ):
    """Confirm dcm files belong to same scan and that only one plan and one structure set are present
    Return list of CT images and the Dicom plan file"""
    
    #allfiles = [ f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir,f)) and ".dcm" in f ]  
    allfiles = list_all_files( input_dir )

    cnt_CT, cnt_plan, cnt_struct, cnt_dose = 0,0,0,0   
    #studyInstanceUID = pydicom.dcmread(os.path.join(input_dir,allfiles[0])).StudyInstanceUID
    studyInstanceUID = pydicom.dcmread(allfiles[0]).StudyInstanceUID
    
    problem = False
    ct_files = []
    plan_file = ""
    dose_files = []
    struct_file = ""
    
    for file in allfiles:        
        #dcm = pydicom.dcmread( os.path.join(input_dir,file) )
        dcm = pydicom.dcmread(file)
        
        if dcm.StudyInstanceUID != studyInstanceUID:
            problem = True
            print("File {} has inconsistent StudyInstanceUID".format(file) )
        
        if dcm.Modality=="CT":
            cnt_CT+=1
            ct_files.append(file)
        elif dcm.Modality=="RTPLAN":
            plan_file = file
            cnt_plan+=1
        elif dcm.Modality=="RTDOSE":
            cnt_dose+=1
            dose_files.append(file)
        elif dcm.Modality=="RTSTRUCT":
            cnt_struct+=1
            struct_file = file
        else:
            print("Dicom file of {} modality found".format(dcm.Modality))
        
    if cnt_plan > 1:
        problem = True
        print("{} dicom plan files detected".format(cnt_plan) )
    if cnt_struct > 1:
        problem = True
        print("{} dicom structure files detected".format(cnt_struct) )

    if problem:
        raise Exception("Dicom directory does not contain correct data")
        sys.exit(1)
    else:
        return ct_files,plan_file,dose_files,struct_file





def main():
    
    
    base_path = Path(__file__).parent
    path_to_templates = (base_path / "../../data/templates").resolve()
    path_to_simfiles = (base_path / "../../data/simulationfiles").resolve()

        
    # Select directory containing the DICOM files
    msg = "Select directory containing DICOM files"
    msg += "\nCT files must be contained in a subdirectory called \"ct\""
    title = "Select directory containing dicom files."
    if easygui.ccbox(msg, title):
        pass
    else:
        sys.exit(0)
    DICOM_DIR = easygui.diropenbox()
    
    
    CT_DIR = os.path.join(DICOM_DIR,"ct")
    #TEMPLATE_MAC = os.path.join("templates","TEMPLATE_simulateField.txt")
    #TEMPLATE_SOURCE = os.path.join("templates","TEMPLATE_SourceDescFile.txt")
    TEMPLATE_MAC = os.path.join(path_to_templates,"TEMPLATE_simulateField.txt")
    TEMPLATE_SOURCE = os.path.join(path_to_templates,"TEMPLATE_SourceDescFile.txt")
   
    #Check all images belong to same image and that only one plan and one structure set are present
    ct_files,plan_file,dose_files,struct_file = search_dcm_dir(DICOM_DIR)    
    
    # Make Gate directory structure and copy fixed files
    print("Making directories")
    plan_name = pydicom.dcmread(plan_file).RTPlanLabel
    sim_dir = os.path.join(path_to_simfiles,plan_name)
    make_gate_dirs(sim_dir, path_to_templates)   
 
    
    img_name = os.path.join(sim_dir,"data","ct_air.mhd")        #TODO: SELECT SENSIBLE NAME
    temp_ct = os.path.join(sim_dir,"data","ct_orig.mhd")
    

    # Convert dicom series to mhd + raw
    print("Converting dcm CT files to mhd image")
    imageconversion.dcm2mhd(CT_DIR, temp_ct)
    
    
    
    # roi_utils does not like image properties of HFP set-up
    # Could try manually changing it here so that the TransformMatrix is
    # always 100010001, Origin coords all negative, AntomicalOrientation 
    # is RAI (or whatever i s"standard").
    
    
    
    # Set all external HUs to air
    #print("Overriding all external structures to air")
    overrides.set_air_external( temp_ct, struct_file, os.path.join(sim_dir,"data",img_name) )
    
    # Check for density overrides and apply
    # TODO ??
    
    # Generate all files required for simulation
    print("Generating simulation files")
    generatefiles.generate_files(ct_files, plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, img_name, sim_dir)
    
    
    
    
    
    
    
if __name__=="__main__":
    main()
    
    