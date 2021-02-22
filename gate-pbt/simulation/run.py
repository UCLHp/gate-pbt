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
import config
import cropdicom



DATA_TO_COPY = ["GateMaterials.db","UCLH2019DensitiesTable_v1.txt",
                 "UCLH2019MaterialsTable_v1.txt", "patient-HU2mat_UCLHv1.txt",
                 "patient-HUmaterials_UCLHv1.db", "simconfig.ini",
                 "SourceDescriptionFile.txt"]
MAC_TO_COPY =  ["verbose.mac","visu.mac"]



def make_gate_dirs(dir_name, path_to_templates):
    """Make dir structure for gate files and copy fixed files"""
    # Make directory tree
    if not os.path.exists(dir_name):
        os.mkdir(dir_name)
        os.mkdir( os.path.join(dir_name,"data") )
        os.mkdir( os.path.join(dir_name,"mac") )
        os.mkdir( os.path.join(dir_name,"output") )    
    # Copy over data files
    for f in DATA_TO_COPY:
        source = os.path.join(path_to_templates,f)  
        destination = os.path.join(dir_name,"data",f)
        shutil.copyfile(source,destination)
    # Copy over mac files
    for f in MAC_TO_COPY:
        source = os.path.join(path_to_templates,f)  
        destination = os.path.join(dir_name,"mac",f)  
        shutil.copyfile(source,destination)
        


def copy_dcm_doses( dcmfiles, destinationdir ):
    """Copy dcm dose files to simdir/data; needed later for analaysis"""
    for dcmfile in dcmfiles:
        fname = os.path.basename(dcmfile)
        dest = os.path.join(destinationdir, fname)
        shutil.copyfile( dcmfile, dest)



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
    dcmfiles = [ f for f in allfiles if f[-4:]==".dcm" ]

    cnt_CT, cnt_plan, cnt_struct, cnt_dose = 0,0,0,0   
    studyInstanceUID = pydicom.dcmread(dcmfiles[0]).StudyInstanceUID
    
    problem = False
    ct_files = []
    plan_file = ""
    dose_files = []
    struct_file = ""
    
    for f in dcmfiles:        

        dcm = pydicom.dcmread(f)
        
        if dcm.StudyInstanceUID != studyInstanceUID:
            problem = True
            print("File {} has inconsistent StudyInstanceUID".format(f) )
        
        if dcm.Modality=="CT":
            cnt_CT+=1
            ct_files.append(f)
        elif dcm.Modality=="RTPLAN":
            plan_file = f
            cnt_plan+=1
        elif dcm.Modality=="RTDOSE":
            cnt_dose+=1
            dose_files.append(f)
        elif dcm.Modality=="RTSTRUCT":
            cnt_struct+=1
            struct_file = f
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
    
    # Get absolute path to template files and destination of simulation files
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
    TEMPLATE_MAC = os.path.join(path_to_templates,"TEMPLATE_simulateField.txt")
    TEMPLATE_SOURCE = os.path.join(path_to_templates,"TEMPLATE_SourceDescFile.txt")
   
    #Check all images belong to same image and that only one plan and one structure set are present
    ct_files,plan_file,dose_files,struct_file = search_dcm_dir(DICOM_DIR)    
    
    # Make Gate directory structure and copy fixed files
    print("Making directories")
    plandcm = pydicom.dcmread(plan_file)
    identifier = plandcm.PatientID+"--"+plandcm.RTPlanLabel
    sim_dir = os.path.join(path_to_simfiles, identifier)
    make_gate_dirs(sim_dir, path_to_templates)   
    
    # Define simconfig.ini configuration file
    CONFIG = os.path.join(sim_dir, "data", "simconfig.ini")
 
    ct_unmod = os.path.join(sim_dir,"data","ct_orig.mhd")  ##path or name?
    ct_air = os.path.join(sim_dir,"data","ct_air.mhd")
    
    
    # Convert dicom series to mhd + raw
    print("Converting dcm CT files to mhd image")
    imageconversion.dcm2mhd(CT_DIR, ct_unmod)
    ##imageconversion.dcm2mhd_gatetools(ct_files)
    
    
    # Set all external HUs to air
    print("Overriding all external structures to air")
    ct_air_path = os.path.join(sim_dir,"data",ct_air)
    overrides.set_air_external( ct_unmod, struct_file, ct_air_path )
    
    # Check for density overrides and apply
    # TODO
    #overrides.override_hu( ct_unmod, struct_file, os.path.join(sim_dir,"data",ct_air), "BODY", -43 )
    
    
    # Crop image to structure
    #ext_contour = overrides.get_external_name( struct_file )
    #cropped_img_path = os.path.join(sim_dir,"data","ct_cropped.mhd")
    #cropdicom.crop_to_structure( ct_air_path, struct_file, ext_contour, cropped_img_path )  #optional margin
    
    
    # TODO: SET THIS AUTOMATICALLY IF CROPPING OR NOT
    ct_for_simulation = ct_air
    #ct_for_simulation = cropped_img_path
    
    
    
    # Add number fractions to config
    nfractions = plandcm.FractionGroupSequence[0].NumberOfFractionsPlanned
    config.add_fractions( CONFIG, nfractions )
    # Add ct name being used in sim to simconfig.ini
    config.add_ct_to_config( CONFIG, os.path.basename(ct_for_simulation) )
    # Add ct transform matrix to simconfig.ini
    config.add_transformmatrix_to_config( CONFIG, ct_for_simulation )
    
    
    # Copy over dicom dose files to /data
    print("Copying dcm dose files over")
    copy_dcm_doses( dose_files, os.path.join(sim_dir,"data") )   
    
       
    
    # Generate all files required for simulation; SPLIT JOBS IN HERE
    print("Generating simulation files")
    #generatefiles.generate_files(ct_files, plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, ct_for_simulation, sim_dir)
    generatefiles.generate_files(ct_files[0], plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, os.path.basename(ct_for_simulation), sim_dir)
    

    
    
    
if __name__=="__main__":
    main()
    
    
