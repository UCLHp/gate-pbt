# -*- coding: utf-8 -*-
"""
@author: Steven Court
Main program to read in all relevant dicom files and 
generate the files required for a Gate simulation.
"""

import sys
import os
from os.path import join, basename, isdir, exists
import shutil
from pathlib import Path

import pydicom
import easygui
import itk
from gatetools.image_convert import read_dicom

import reorientate
#import imageconversion
import overrides
import generatefiles
import config
import cropimage



DATA_TO_COPY = ["GateMaterials.db","UCLH2019DensitiesTable_v1.txt",
                 "UCLH2019MaterialsTable_v1.txt", "patient-HU2mat_UCLHv1.txt",
                 "patient-HUmaterials_UCLHv1.db", "simconfig.ini",
                 "SourceDescriptionFile.txt"]
MAC_TO_COPY =  ["verbose.mac","visu.mac"]



def make_gate_dirs(dir_name, path_to_templates):
    """Make dir structure for gate files and copy fixed files"""
    # Make directory tree
    if not exists(dir_name):
        os.mkdir(dir_name)
        os.mkdir( join(dir_name,"data") )
        os.mkdir( join(dir_name,"mac") )
        os.mkdir( join(dir_name,"output") )    
    # Copy over data files
    for f in DATA_TO_COPY:
        source = join(path_to_templates,f)  
        destination = join(dir_name,"data",f)
        shutil.copyfile(source,destination)
    # Copy over mac files
    for f in MAC_TO_COPY:
        source = join(path_to_templates,f)  
        destination = join(dir_name,"mac",f)  
        shutil.copyfile(source,destination)
        


def copy_dcm_doses( dcmfiles, destinationdir ):
    """Copy dcm dose files to simdir/data; needed later for analaysis"""
    for dcmfile in dcmfiles:
        fname = basename(dcmfile)
        dest = join(destinationdir, fname)
        shutil.copyfile( dcmfile, dest)



def list_all_files(dirName):
    """Return file list within immediate directory"""
    # Create a list of file and sub-dirs in given dir 
    print(dirName)
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = join(dirName, entry)
        if isdir(fullPath):
            # Ignore sub directories
            ##allFiles = allFiles + list_all_files(fullPath) 
            pass
        else:
            allFiles.append(fullPath)
                
    return allFiles



def search_dcm_dir( input_dir ):
    """Confirm dcm files belong to same scan and that only one plan and one 
    structure set are present
    
    Return list of CT images, dcm plan, list of dcm doses, structure set
    """
    
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
    #CT_DIR = join(DICOM_DIR,"ct")
    TEMPLATE_MAC = join(path_to_templates,"TEMPLATE_simulateField.txt")
    TEMPLATE_SOURCE = join(path_to_templates,"TEMPLATE_SourceDescFile.txt")
   
    #Check all images belong to same image and that only one plan and one structure set are present
    ct_files,plan_file,dose_files,struct_file = search_dcm_dir(DICOM_DIR)    
    
    # Make Gate directory structure and copy fixed files
    print("Making directories")
    plandcm = pydicom.dcmread(plan_file)
    identifier = plandcm.PatientID+"--"+plandcm.RTPlanLabel
    sim_dir = join(path_to_simfiles, identifier)
    make_gate_dirs(sim_dir, path_to_templates)   
    
    # Define simconfig.ini configuration file
    CONFIG = join(sim_dir, "data", "simconfig.ini")
 
    #Defining some path names for intermediate images for debugging
    ct_unmod = join(sim_dir,"data","ct_orig.mhd")  ##path or name?
    ct_reorientate = join(sim_dir, "data", "ct_orig_reorientate.mhd")
    ct_air = join(sim_dir,"data","ct_air.mhd")
      
    patient_position = pydicom.dcmread(ct_files[0]).PatientPosition
    config.add_patient_position( CONFIG, patient_position )
    
    print("Converting dcm CT files to mhd image")
    itkimg = read_dicom( ct_files )
    itk.imwrite(itkimg, ct_unmod) 
    
    print("Reorientating image to enforce positive directionality")
    img_reor=reorientate.force_positive_directionality(ct_unmod)
    itk.imwrite( img_reor, ct_reorientate)    
    
    print("Overriding all external structures to air")
    ct_air_path = join(sim_dir,"data",ct_air)
    overrides.set_air_external( ct_reorientate, struct_file, ct_air_path )  #  USE REORIENTATED IMG
      
    # Check for density overrides and apply
    # TODO
    #overrides.override_hu( ct_unmod, struct_file, join(sim_dir,"data",ct_air), "BODY", -43 )
    
    # Crop image to structure
    ext_contour = overrides.get_external_name( struct_file )
    print("Cropping img to ", ext_contour)
    cropped_img_path = join(sim_dir,"data","ct_cropped.mhd")
    cropimage.crop_to_structure( ct_air_path, struct_file, ext_contour, cropped_img_path )  #optional margin

    # TODO: SET THIS AUTOMATICALLY IF CROPPING OR NOT
    #ct_for_simulation = ct_air
    ct_for_simulation = cropped_img_path
    
    # Add number fractions to config
    nfractions = plandcm.FractionGroupSequence[0].NumberOfFractionsPlanned
    config.add_fractions( CONFIG, nfractions )
    # Add ct name being used in sim to simconfig.ini
    config.add_ct_to_config( CONFIG, basename(ct_for_simulation) )
    # Add ct transform matrix to simconfig.ini
    config.add_transformmatrix_to_config( CONFIG, ct_for_simulation )
      
    # Copy over dicom dose files to /data
    print("Copying dcm dose files over")
    copy_dcm_doses( dose_files, join(sim_dir,"data") )   
      
    # Generate all files required for simulation
    print("Generating simulation files")
    #generatefiles.generate_files(ct_files, plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, ct_for_simulation, sim_dir)
    generatefiles.generate_files(ct_files[0], plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, basename(ct_for_simulation), sim_dir)
    

    
    
    
if __name__=="__main__":
    main()
    
    
