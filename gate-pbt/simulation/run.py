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
import json

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
import slurm
import numpy as np




##############################################################################

# Get absolute path to template files and destination of simulation files
base_path = Path(__file__).parent
PATH_TO_TEMPLATES = (base_path / "../templates").resolve()
PATH_TO_SIMFILES = (base_path / "../../data/simulationfiles").resolve()


# System configuration data; see json file for details
DATA = json.load( open(join(PATH_TO_TEMPLATES,"sysconfig.json")) )

##############################################################################



def make_gate_dirs(dir_name, path_to_templates):
    """Make dir structure for gate files and copy fixed files"""
    # Make directory tree
    if not exists(dir_name):
        os.mkdir(dir_name)
        os.mkdir( join(dir_name,"data") )
        os.mkdir( join(dir_name,"mac") )
        os.mkdir( join(dir_name,"output") )    
    # Copy over data files
    for f in DATA["DATA_TO_COPY"]:
        source = join(path_to_templates,f)  
        destination = join(dir_name,"data",f)
        shutil.copyfile(source,destination)
        slurm.dos2unix( destination, destination )
    # Copy over mac files
    for f in DATA["MACS_TO_COPY"]:
        source = join(path_to_templates,f)  
        destination = join(dir_name,"mac",f)  
        shutil.copyfile(source,destination)
        


def copy_dcm_files( dcmfiles, destinationdir ):
    """Copy dcm dose files to simdir/data; needed later for analaysis"""
    if isinstance( dcmfiles, str ):
        dcmfiles = [dcmfiles]
        
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
    
    


def structure_exists( dcmfile, struct ):
    """Checks structure dicom file that "struct" exists and is contoured
    
    Returns boolean"""
    
    exists = False
    
    dcmf = pydicom.dcmread(dcmfile)
    roi_num = None
    for s in dcmf.StructureSetROISequence:
        #if s.ROIName.lower()==struct.lower():
        if s.ROIName==struct:
            roi_num = s.ROINumber
            break

    if roi_num is not None:
        for s in dcmf.ROIContourSequence:
            if s.ReferencedROINumber == roi_num:
                if len(s.ContourSequence)>0:
                    if s.ContourSequence[0].NumberOfContourPoints>3:
                        exists = True
                        break
    return exists


def load_edensity_calibration_file():
    """
    Loads a calibration file that is located in the parent directory under
    data/calibration_files/HOST-10027 e density 20250219_TEXT.
    
    The file is assumed to contain header lines until a line exactly equal to "X Y"
    is found. After that, each subsequent non-empty line is expected to have at least
    two numbers separated by whitespace, representing X and Y respectively.
    
    Returns:
        tuple: Two lists (X, Y) containing the calibration values.
    """
    # Get the current working directory and then its parent
    current_dir = os.getcwd()
    parent_dir = os.path.dirname(current_dir)
    
    # Construct the full path to the calibration file
    file_path = os.path.join(parent_dir, "data", "calibration_files", "TEST.txt")
    
    X, Y = [], []
    data_started = False
    
    # Open and read the file
    with open(file_path, "r") as f:
        for line in f:
            stripped_line = line.strip()
            
            # Look for the line that indicates the start of the data
            if not data_started:
                if stripped_line == "X Y":
                    data_started = True  # Data lines follow after this header line
                continue
            
            # Once data has started, skip empty lines and parse the data
            if stripped_line:
                parts = stripped_line.split()
                if len(parts) >= 2:
                    try:
                        x_val = float(parts[0])
                        y_val = float(parts[1])
                        X.append(x_val)
                        Y.append(y_val)
                    except ValueError:
                        # If conversion fails, ignore the line
                        continue
    return X, Y


def convert_eDensity_HU(x, y, dictionary):
    """
    For each structure in dictionary, converts its electron density (given as a string)
    into a corresponding HU value via linear interpolation on the calibration curve data (x, y).

    Args:
        x (list of float): HU values from the calibration curve.
        y (list of float): Corresponding electron density values.
        dictionary (dict): Dictionary with structure names as keys and electron density values (as strings) as values.

    Returns:
        dict: A dictionary with the same keys but where the values are the interpolated HU values.
    """
    hu_dict = {}
    for key, e_str in dictionary.items():
        e_val = float(e_str)
        # Linear interpolation: for a given electron density e_val, find the corresponding HU value.
        hu_dict[key] = np.interp(e_val, y, x)
    return hu_dict
   






def main():
     
    # Select directory containing the DICOM files
    msg = "Select directory containing DICOM files"
    #msg += "\nCT files must be contained in a subdirectory called \"ct\""
    title = "Select directory containing dicom files."
    if easygui.ccbox(msg, title):
        pass
    else:
        sys.exit(0)
        
    dicom_dir = easygui.diropenbox()
    #mac_template = join(path_to_templates, DATA["MAC_TEMPLATE"])
   
    #Check all images belong to same image and that only one plan and one structure set are present
    ct_files,plan_file,dose_files,struct_file = search_dcm_dir(dicom_dir)
    
    skip = True

    if skip:
    

        # Make Gate directory structure and copy fixed files
        print("Making directories")
        plandcm = pydicom.dcmread(plan_file)    
        pat_id = plandcm.PatientID.replace("/","").replace("\\","")
        identifier = pat_id+"--"+(plandcm.RTPlanLabel).replace(" ","_")
        sim_dir = join(PATH_TO_SIMFILES, identifier)
        make_gate_dirs(sim_dir, PATH_TO_TEMPLATES)   
        
        # Define simconfig.ini configuration file
        configpath = join(sim_dir, "data", DATA["CONFIG_FILE"])
        patient_position = pydicom.dcmread(ct_files[0]).PatientPosition
        config.add_patient_position( configpath, patient_position )
        
        print("Converting dcm CT files to mhd image")
        ctimg = read_dicom( ct_files )
        
        print("Reorientating image to enforce positive directionality")
        ct_reor = reorientate.force_positive_directionality(ctimg)
        #itk.imwrite(ct_reor,join(sim_dir, "data", "ct_orig_reorientate.mhd"))   
        
        # Crop image to structure
        #crop_to_contour="Dose 0.1[%]" 
        crop_to_contour="BODY"  
        print("Cropping img to", crop_to_contour)
        ct_cropped = cropimage.crop_to_structure( ct_reor, struct_file, crop_to_contour) #optional margin
        
        
        print("Overriding all external structures to air")

        print(f"Type after overrides: {type(ct_cropped)}")
        ct_cropped = overrides.set_air_external( ct_cropped, struct_file )

        #ct_cropped = overrides.override_hu( ct_cropped, struct_file, 'zWire', 5000)
        #ct_cropped = overrides.override_hu( ct_cropped, struct_file, 'test_override1', 5000)
        #ct_cropped = overrides.override_hu( ct_cropped, struct_file, 'test_override2', 5000)

        print(f"Type after overrides: {type(ct_cropped)}")
        print('Overriding -1000')

        ###
        ###

        
        #itk.imwrite(ct_air_override, join(sim_dir,"data","ct_air.mhd"))
        
        #structs_to_air = ["zbb", "zBB", "zbbs", "zBBs", "bb", "BB", "bbs", "BBs",
        #                  "zscarwire", "zscar_wire", "zScarWire", "zScar_Wire",
        #                  "z_Wire", "NS_Wire"]
        #for s in structs_to_air:
        #    if structure_exists( struct_file, s ):
        #        print("Overriding",s,"to air")
        #        ct_air_override = overrides.override_hu( ct_air_override, struct_file, s, -1000 )    
            





    # TODO: Check for density overrides and apply
    
    # Dictionary to store ROI identifiers and their REL_ELEC_DENSITY values
    roi_density_dict = {}

    # Check if the RS has the RT ROI Observations Sequence


    
    # Search for the attribute
    structdcm = pydicom.dcmread(struct_file)
    
    # Create a mapping of ROI Number to ROI Name
    roi_name_dict = {
        roi_item.ROINumber: roi_item.ROIName
        for roi_item in structdcm.StructureSetROISequence
    }
    roi_density_dict = {}
    for roi_obs in structdcm.RTROIObservationsSequence:
        if hasattr(roi_obs, "ROIPhysicalPropertiesSequence"):
            for prop in roi_obs.ROIPhysicalPropertiesSequence:
                if getattr(prop, "ROIPhysicalProperty", None) == "REL_ELEC_DENSITY":
                    density_value = getattr(prop, "ROIPhysicalPropertyValue", None)
                    if density_value is not None:
                        roi_id = getattr(roi_obs, "ReferencedROINumber", None)
                        
                        # Get the structure name from roi_name_dict
                        structure_name = roi_name_dict.get(roi_id, f"ROI_{roi_id}") if roi_id is not None else "Unknown"

                        # Store in dictionary with structure name as key
                        roi_density_dict[structure_name] = density_value

    # Print or use the dictionary as needed
    print(roi_density_dict)
    # Get HU FROM ELEC DENSITY function using calib files
    

   
    X, Y = load_edensity_calibration_file()
    #print(X, Y)
    hu_dict = convert_eDensity_HU(X, Y, roi_density_dict)
    

    for structure, hu_value in hu_dict.items():
        overrides.override_hu(ct_cropped, struct_file, structure, hu_value)
    
  




    # TODO: set automatically for different cropping / override options
    ct_for_simulation = "ct_cropped.mhd"
    ct_sim_path = join(sim_dir,"data",ct_for_simulation)
    itk.imwrite(ct_cropped, ct_sim_path)
    
    
    

    print("Generate dose mask from zSurface for gamma analysis")
    dosemask = overrides.get_structure_mask( ct_cropped, struct_file, "zSurface" )
    itk.imwrite( dosemask, join(sim_dir,"data","DoseMask.mhd") )
    
    
    # Add number fractions to config
    nfractions = plandcm.FractionGroupSequence[0].NumberOfFractionsPlanned
    config.add_fractions( configpath, nfractions )
    # Add ct name being used in sim to simconfig.ini
    config.add_ct_to_config( configpath, ct_for_simulation )
    # Add ct transform matrix to simconfig.ini - NO NEED; JUST USE 100010
    #config.add_transformmatrix_to_config( CONFIG, ct_for_simulation )
      
    # Copy over dicom dose files to /data
    print("Copying dcm dose files over")
    copy_dcm_files( dose_files, join(sim_dir,"data") )
    print("Copying dcm structure file over")
    copy_dcm_files( struct_file, join(sim_dir,"data") )
    #config.add_structure_to_config( configpath, struct_file )

      
    # Generate all files required for simulation
    print("Generating simulation files")
    #generatefiles.generate_files(ct_files, plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, ct_for_simulation, sim_dir)
    generatefiles.generate_files(ct_files[0], plan_file, dose_files, PATH_TO_TEMPLATES, DATA, configpath, ct_for_simulation, sim_dir)
    

    
    
    
if __name__=="__main__":
    main()
    
    
