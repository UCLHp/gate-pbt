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
import time

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
    #ctimg = overrides.override_hu( ctimg, struct_file, "BODY", 999 )    ##### !!!!!!!!!!!!!!! 
    #itk.imwrite(ctimg, join(sim_dir,"data","ct_orig.mhd")) 
    
    print("Reorientating image to enforce positive directionality")
    ct_reor = reorientate.force_positive_directionality(ctimg)
    itk.imwrite(ct_reor,join(sim_dir, "data", "ct_orig_reorientate.mhd"))   
    
    #t1 = time.perf_counter()
    
    # Crop image to structure
    crop_to_contour = overrides.get_external_name( struct_file )   
    crop_to_contour="Dose0.1%"   
    print("Cropping img to", crop_to_contour)
    ct_cropped = cropimage.crop_to_structure( ct_reor, struct_file, crop_to_contour) #optional margin

        
    print("Overriding all external structures to air")
    ct_cropped = overrides.set_air_external( ct_cropped, struct_file )
    #itk.imwrite(ct_air_override, join(sim_dir,"data","ct_air.mhd"))
    
    #t2 = time.perf_counter();
    #tt = (t2-t1)/60
    #print("  -> Time to override external air = ", tt) 
    
    #
    #structs_to_air = ["zbb", "zBB", "zbbs", "zBBs", "bb", "BB", "bbs", "BBs",
    #                  "zscarwire", "zscar_wire", "zScarWire", "zScar_Wire",
    #                  "z_Wire", "NS_Wire"]
    #for s in structs_to_air:
    #    if structure_exists( struct_file, s ):
    #        print("Overriding",s,"to air")
    #        ct_air_override = overrides.override_hu( ct_air_override, struct_file, s, -1000 )    
      
    # TODO: Check for density overrides and apply
    #override_hu( image, structure_file, structure, hu )
  
    ##### OVERRIDE FOR PSQA
    #ct_air_override = overrides.override_hu( ct_air_override, struct_file, "BODY", 51 )
    #ct_air_override = overrides.override_hu( ct_air_override, struct_file, "zMetal", 4998 )
       
    #itk.imwrite(ct_cropped, join(sim_dir,"data","ct_cropped.mhd"))
    
    # TODO: set automatically for different cropping / override options
    ct_for_simulation = "ct_cropped.mhd"
    ct_sim_path = join(sim_dir,"data",ct_for_simulation)
    itk.imwrite(ct_cropped, ct_sim_path)
    
    
    
    # Add number fractions to config
    nfractions = plandcm.FractionGroupSequence[0].NumberOfFractionsPlanned
    config.add_fractions( configpath, nfractions )
    # Add ct name being used in sim to simconfig.ini
    config.add_ct_to_config( configpath, ct_for_simulation )
    # Add ct transform matrix to simconfig.ini - NO NEED; JUST USE 100010
    #config.add_transformmatrix_to_config( CONFIG, ct_for_simulation )
      
    # Copy over dicom dose files to /data
    print("Copying dcm dose files over")
    copy_dcm_doses( dose_files, join(sim_dir,"data") )   
      
    # Generate all files required for simulation
    print("Generating simulation files")
    #generatefiles.generate_files(ct_files, plan_file, dose_files, TEMPLATE_MAC, TEMPLATE_SOURCE, CONFIG, ct_for_simulation, sim_dir)
    generatefiles.generate_files(ct_files[0], plan_file, dose_files, PATH_TO_TEMPLATES, DATA, configpath, ct_for_simulation, sim_dir)
    

    
    
    
if __name__=="__main__":
    main()
    
    
