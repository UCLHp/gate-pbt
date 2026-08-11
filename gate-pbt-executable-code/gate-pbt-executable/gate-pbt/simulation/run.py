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

import sys
from pathlib import Path
import easygui


# ============================================================================
# DEBUG UTILITY FUNCTION
# ============================================================================
def debug_print(message):
    """Print debug message to both stdout and stderr for visibility"""
    # Encode with error handling to avoid Unicode issues
    try:    
        print(f"[DEBUG] {message}", flush=True)
        sys.stderr.write(f"[DEBUG] {message}\n")
        sys.stderr.flush()
    except UnicodeEncodeError:
        # Fallback: replace problematic characters
        safe_message = message.encode('ascii', errors='replace').decode('ascii')
        print(f"[DEBUG] {safe_message}", flush=True)
        sys.stderr.write(f"[DEBUG] {safe_message}\n")
        sys.stderr.flush()

# ============================================================================
# STARTUP DEBUG INFO
# ============================================================================
debug_print("="*80)
debug_print("EXECUTABLE STARTED")
debug_print("="*80)
debug_print(f"Python version: {sys.version}")
debug_print(f"sys.executable: {sys.executable}")
debug_print(f"sys.argv: {sys.argv}")
debug_print(f"Number of arguments: {len(sys.argv)}")
debug_print(f"Frozen (running as exe): {getattr(sys, 'frozen', False)}")
if hasattr(sys, '_MEIPASS'):
    debug_print(f"_MEIPASS: {sys._MEIPASS}")
debug_print(f"Current working directory: {os.getcwd()}")
debug_print(f"__file__ available: {__name__ == '__main__' and '__file__' in dir()}")
debug_print("="*80)



from pathlib import Path
import sys
import os
import json

##############################################################################

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    debug_print(f"get_resource_path called with: {relative_path}")
    
    if getattr(sys, 'frozen', False):
        # Running as executable - use _MEIPASS (PyInstaller's extracted location)
        base_path = Path(sys._MEIPASS)
        debug_print(f"Using _MEIPASS: {base_path}")
    else:
        # Running as script - use relative to script location
        base_path = Path(os.getcwd())
        debug_print(f"Running as script, base_path: {base_path}")
    
    resolved = (base_path / relative_path).resolve()
    debug_print(f"Final resolved path: {resolved}")
    debug_print(f"Path exists: {resolved.exists()}")
    return resolved

# For templates (bundled with executable)
debug_print("\n--- Setting up PATH_TO_TEMPLATES ---")
PATH_TO_TEMPLATES = get_resource_path("templates")
debug_print(f"PATH_TO_TEMPLATES: {PATH_TO_TEMPLATES}")
debug_print(f"PATH_TO_TEMPLATES exists: {PATH_TO_TEMPLATES.exists()}")

# For simulation files - create relative to executable location
debug_print("\n--- Setting up PATH_TO_SIMFILES ---")
if getattr(sys, 'frozen', False):
    # When running as executable, create output folder next to the exe
    PATH_TO_SIMFILES = Path(sys.executable).parent / "data" / "simulationfiles"
    debug_print(f"Running as exe, PATH_TO_SIMFILES: {PATH_TO_SIMFILES}")
    PATH_TO_SIMFILES.mkdir(parents=True, exist_ok=True)
    debug_print(f"Created/verified PATH_TO_SIMFILES directory")
else:
    # When running as script, use original relative path
    base_path = Path(__file__).parent
    PATH_TO_SIMFILES = (base_path / "../../data/simulationfiles").resolve()
    debug_print(f"Running as script, PATH_TO_SIMFILES: {PATH_TO_SIMFILES}")

debug_print(f"Final PATH_TO_SIMFILES: {PATH_TO_SIMFILES}")
debug_print(f"PATH_TO_SIMFILES exists: {PATH_TO_SIMFILES.exists()}")

# System configuration data
debug_print("\n--- Loading system configuration ---")
config_file = PATH_TO_TEMPLATES / "sysconfig.json"
debug_print(f"Config file path: {config_file}")
debug_print(f"Config file exists: {config_file.exists()}")

try:
    DATA = json.load(open(config_file))
    debug_print(f"Config loaded successfully")
except Exception as e:
    debug_print(f"ERROR loading config: {e}")
    raise
##############################################################################


def make_gate_dirs(dir_name, path_to_templates):
    """Make dir structure for gate files and copy fixed files"""
    debug_print(f"\n--- make_gate_dirs called ---")
    debug_print(f"dir_name: {dir_name}")
    debug_print(f"path_to_templates: {path_to_templates}")
    
    # Make directory tree
    if not exists(dir_name):
        debug_print(f"Creating directory structure at: {dir_name}")
        os.mkdir(dir_name)
        os.mkdir( join(dir_name,"data") )
        os.mkdir( join(dir_name,"mac") )
        os.mkdir( join(dir_name,"output") )
        debug_print("Directories created successfully")
    else:
        debug_print(f"Directory already exists: {dir_name}")
        
    # Copy over data files
    debug_print(f"Copying {len(DATA['DATA_TO_COPY'])} data files")
    for f in DATA["DATA_TO_COPY"]:
        source = join(path_to_templates,f)  
        destination = join(dir_name,"data",f)
        debug_print(f"  Copying: {source} -> {destination}")
        shutil.copyfile(source,destination)
        slurm.dos2unix( destination, destination )
        
    # Copy over mac files
    debug_print(f"Copying {len(DATA['MACS_TO_COPY'])} mac files")
    for f in DATA["MACS_TO_COPY"]:
        source = join(path_to_templates,f)  
        destination = join(dir_name,"mac",f)
        debug_print(f"  Copying: {source} -> {destination}")
        shutil.copyfile(source,destination)


def copy_dcm_files( dcmfiles, destinationdir ):
    """Copy dcm dose files to simdir/data; needed later for analaysis"""
    debug_print(f"\n--- copy_dcm_files called ---")
    debug_print(f"destinationdir: {destinationdir}")
    
    if isinstance( dcmfiles, str ):
        dcmfiles = [dcmfiles]
    
    debug_print(f"Copying {len(dcmfiles)} DCM files")
    for dcmfile in dcmfiles:
        fname = basename(dcmfile)
        dest = join(destinationdir, fname)
        debug_print(f"  Copying: {dcmfile} -> {dest}")
        shutil.copyfile( dcmfile, dest)


def list_all_files(dirName):
    """Return file list within immediate directory"""
    debug_print(f"\n--- list_all_files called ---")
    debug_print(f"Directory: {dirName}")
    debug_print(f"Directory exists: {os.path.exists(dirName)}")
    debug_print(f"Is directory: {os.path.isdir(dirName)}")
    
    listOfFile = os.listdir(dirName)
    debug_print(f"Found {len(listOfFile)} items in directory")
    debug_print(f"First 10 items: {listOfFile[:10]}")
    
    allFiles = list()
    for entry in listOfFile:
        fullPath = join(dirName, entry)
        if not isdir(fullPath):
            allFiles.append(fullPath)
    
    debug_print(f"Total files (not dirs): {len(allFiles)}")
    return allFiles


def search_dcm_dir( input_dir ):
    """Confirm dcm files belong to same scan and that only one plan and one 
    structure set are present
    
    Return list of CT images, dcm plan, list of dcm doses, structure set
    """
    debug_print(f"\n--- search_dcm_dir called ---")
    debug_print(f"input_dir: {input_dir}")
    
    allfiles = list_all_files( input_dir )
    dcmfiles = [ f for f in allfiles if f[-4:]==".dcm" ]
    debug_print(f"Found {len(dcmfiles)} .dcm files")
    
    if len(dcmfiles) == 0:
        debug_print("ERROR: No .dcm files found!")
        raise Exception("No DICOM files found in directory")
    
    cnt_CT, cnt_plan, cnt_struct, cnt_dose = 0,0,0,0
    
    debug_print(f"Reading first DCM file: {dcmfiles[0]}")
    studyInstanceUID = pydicom.dcmread(dcmfiles[0]).StudyInstanceUID
    debug_print(f"StudyInstanceUID: {studyInstanceUID}")
    
    problem = False
    ct_files = []
    plan_file = ""
    dose_files = []
    struct_file = ""
    
    debug_print("\nScanning all DCM files...")
    for f in dcmfiles:        
        dcm = pydicom.dcmread(f)
        
        if dcm.StudyInstanceUID != studyInstanceUID:
            problem = True
            debug_print(f"ERROR: File {f} has inconsistent StudyInstanceUID")
        
        modality = dcm.Modality
        if modality == "CT":
            cnt_CT += 1
            ct_files.append(f)
        elif modality == "RTPLAN":
            plan_file = f
            cnt_plan += 1
            debug_print(f"Found RTPLAN: {f}")
        elif modality == "RTDOSE":
            cnt_dose += 1
            dose_files.append(f)
        elif modality == "RTSTRUCT":
            cnt_struct += 1
            struct_file = f
            debug_print(f"Found RTSTRUCT: {f}")
        else:
            debug_print(f"Found unusual modality '{modality}' in file: {f}")
    
    debug_print(f"\nDICOM file summary:")
    debug_print(f"  CT files: {cnt_CT}")
    debug_print(f"  RTPLAN files: {cnt_plan}")
    debug_print(f"  RTDOSE files: {cnt_dose}")
    debug_print(f"  RTSTRUCT files: {cnt_struct}")
    
    if cnt_plan > 1:
        problem = True
        debug_print(f"ERROR: {cnt_plan} dicom plan files detected (expected 1)")
    if cnt_struct > 1:
        problem = True
        debug_print(f"ERROR: {cnt_struct} dicom structure files detected (expected 1)")

    if problem:
        debug_print("ERROR: Dicom directory does not contain correct data")
        raise Exception("Dicom directory does not contain correct data")
    else:
        debug_print("DICOM directory validation passed")
        return ct_files, plan_file, dose_files, struct_file


def get_dicom_directory():
    """Get DICOM directory path from command line argument or GUI."""
    debug_print(f"\n--- get_dicom_directory called ---")
    debug_print(f"sys.argv: {sys.argv}")
    debug_print(f"Current working directory: {os.getcwd()}")
    
    # Get path from argument or GUI
    if len(sys.argv) > 1:
        dicom_dir = _get_path_from_argument(sys.argv[1])
    else:
        debug_print("No DICOM directory provided as argument -> Opening GUI")
        dicom_dir = _get_path_from_gui()
    
    # Validate the path exists
    if not dicom_dir or not Path(dicom_dir).exists():
        _handle_invalid_path(dicom_dir)
    
    debug_print(f"Using DICOM directory: {dicom_dir}")
    return str(dicom_dir)


def _get_path_from_argument(path_input):
    """Resolve and normalize a path from command line argument."""
    debug_print(f"Argument provided: {path_input}")
    
    dicom_dir = Path(path_input)
    debug_print(f"As Path object: {dicom_dir}")
    debug_print(f"Is absolute: {dicom_dir.is_absolute()}")
    
    # Resolve relative paths from CWD
    if not dicom_dir.is_absolute():
        dicom_dir = Path.cwd() / dicom_dir
        debug_print(f"Resolved from CWD: {dicom_dir}")
    
    dicom_dir = dicom_dir.resolve()
    debug_print(f"Final resolved path: {dicom_dir}")
    debug_print(f"Path exists: {dicom_dir.exists()}")
    
    return dicom_dir


def _get_path_from_gui():
    """Open GUI to select DICOM directory."""
    msg = "Select directory containing DICOM files"
    title = "Select directory containing dicom files."
    
    if not easygui.ccbox(msg, title):
        sys.exit(0)
    
    dicom_dir = easygui.diropenbox()
    return dicom_dir


def _handle_invalid_path(dicom_dir):
    """Handle invalid or non-existent paths with helpful error messages."""
    debug_print(f"✗ ERROR: DICOM path does not exist!")
    debug_print(f"  Provided: {dicom_dir}")
    debug_print(f"  Current working directory: {Path.cwd()}")
    
    # List contents of CWD to help debugging
    debug_print(f"\nContents of current directory ({Path.cwd()}):")
    try:
        for item in Path.cwd().iterdir():
            debug_print(f"  - {item.name} ({'dir' if item.is_dir() else 'file'})")
    except Exception as e:
        debug_print(f"  Error listing directory: {e}")
    
    sys.exit(1)


def structure_exists( dcmfile, struct ):
    """Checks structure dicom file that "struct" exists and is contoured
    
    Returns boolean"""
    exists = False
    
    dcmf = pydicom.dcmread(dcmfile)
    roi_num = None
    for s in dcmf.StructureSetROISequence:
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
    Loads a calibration file that is located in templates/TEST.txt
    """
    debug_print(f"\n--- load_edensity_calibration_file called ---")
    
    # Use get_resource_path to find the file (same as other template files)
    file_path = PATH_TO_TEMPLATES / "TEST.txt"
    debug_print(f"Calibration file path: {file_path}")
    debug_print(f"Calibration file exists: {file_path.exists()}")
    
    X, Y = [], []
    data_started = False
    
    # Open and read the file
    with open(file_path, "r") as f:
        for line in f:
            stripped_line = line.strip()
            
            if not data_started:
                if stripped_line == "X Y":
                    data_started = True
                continue
            
            if stripped_line:
                parts = stripped_line.split()
                if len(parts) >= 2:
                    try:
                        x_val = float(parts[0])
                        y_val = float(parts[1])
                        X.append(x_val)
                        Y.append(y_val)
                    except ValueError:
                        continue
    
    debug_print(f"Loaded {len(X)} calibration points")
    return X, Y

def convert_eDensity_HU(x, y, dictionary):
    """
    For each structure in dictionary, converts its electron density (given as a string)
    into a corresponding HU value via linear interpolation on the calibration curve data (x, y).
    """
    debug_print(f"\n--- convert_eDensity_HU called ---")
    debug_print(f"Converting {len(dictionary)} structures")
    
    hu_dict = {}
    for key, e_str in dictionary.items():
        e_val = float(e_str)
        hu_val = np.interp(e_val, y, x)
        hu_dict[key] = hu_val
        debug_print(f"  {key}: eDensity {e_val} -> HU {hu_val:.2f}")
    
    return hu_dict


def main():
    debug_print("\n" + "="*80)
    debug_print("MAIN FUNCTION STARTED")
    debug_print("="*80)
    
    debug_print(f"Current working directory: {os.getcwd()}")

    # Check all images belong to same image and that only one plan and one structure set are present
    dicom_dir = get_dicom_directory()
    debug_print(f"\n DICOM directory confirmed: {dicom_dir}")
    
    ct_files, plan_file, dose_files, struct_file = search_dcm_dir(dicom_dir)
    debug_print(f"\n DICOM files parsed successfully")
  
    skip = True

    if skip:
        # Make Gate directory structure and copy fixed files
        debug_print("\n--- Making directories ---")
        plandcm = pydicom.dcmread(plan_file)    
        pat_id = plandcm.PatientID.replace("/","").replace("\\","")
        identifier = pat_id+"--"+(plandcm.RTPlanLabel).replace(" ","_")
        sim_dir = join(PATH_TO_SIMFILES, identifier)
        debug_print(f"Simulation directory: {sim_dir}")
        make_gate_dirs(sim_dir, PATH_TO_TEMPLATES)   
        
        # Define simconfig.ini configuration file
        configpath = join(sim_dir, "data", DATA["CONFIG_FILE"])
        patient_position = pydicom.dcmread(ct_files[0]).PatientPosition
        config.add_patient_position( configpath, patient_position )
        
        debug_print("\n--- Converting dcm CT files to mhd image ---")
        ctimg = read_dicom( ct_files )
        
        debug_print("--- Reorientating image to enforce positive directionality ---")
        ct_reor = reorientate.force_positive_directionality(ctimg)

        debug_print(f"Type after reorientate: {type(ct_reor)}")
        debug_print('Overriding -1000')

        # TODO: Check for density overrides and apply
        debug_print("\n--- Processing ROI density overrides ---")
        roi_density_dict = {}

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
                            structure_name = roi_name_dict.get(roi_id, f"ROI_{roi_id}") if roi_id is not None else "Unknown"
                            roi_density_dict[structure_name] = density_value
                            debug_print(f"Found ROI strucutre {structure_name}, with density value {density_value}")

        debug_print(f"Found {len(roi_density_dict)} ROIs with density overrides:")
        for struct_name, density in roi_density_dict.items():
            debug_print(f"  {struct_name}: {density}")
        
        X, Y = load_edensity_calibration_file()
        hu_dict = convert_eDensity_HU(X, Y, roi_density_dict)
        
        debug_print("\n--- Applying HU overrides ---")
        for structure, hu_value in hu_dict.items():
            debug_print(f"Overriding {structure} to HU {hu_value:.2f}")
            ct_reor = overrides.override_hu(ct_reor, struct_file, structure, hu_value)

        # NOW crop after all overrides are applied
        
        # Crop image to structure
        crop_to_contour="Dose 0.1[%]"
        debug_print(f"\n--- Cropping img to {crop_to_contour} ---")
        ct_cropped = cropimage.crop_to_structure(ct_reor, struct_file, crop_to_contour)
        
        debug_print("\n--- Overriding all external structures to air ---")
        debug_print(f"Type after overrides: {type(ct_cropped)}")
        ct_cropped = overrides.set_air_external( ct_cropped, struct_file )

        
        
        # TODO: set automatically for different cropping / override options
        ct_for_simulation = "ct_cropped.mhd"
        ct_sim_path = join(sim_dir,"data",ct_for_simulation)
        debug_print(f"\n--- Writing CT for simulation: {ct_sim_path} ---")
        itk.imwrite(ct_cropped, ct_sim_path)
        
        debug_print("\n--- Generate dose mask from zSurface for gamma analysis ---")
        dosemask = overrides.get_structure_mask( ct_cropped, struct_file, "zSurface" ) # using 0.1 % dose to get something running - zSurface should be used
        itk.imwrite( dosemask, join(sim_dir,"data","DoseMask.mhd") )
        
        # Add number fractions to config
        nfractions = plandcm.FractionGroupSequence[0].NumberOfFractionsPlanned
        config.add_fractions( configpath, nfractions )
        # Add ct name being used in sim to simconfig.ini
        config.add_ct_to_config( configpath, ct_for_simulation )
        
        # Copy over dicom dose files to /data
        # Copy over dicom dose files to /data
        debug_print("\n--- Copying dcm dose files over ---")
        dest_data_dir = join(sim_dir, "data")
        debug_print(f"Ensuring destination directory exists: {dest_data_dir}")
        os.makedirs(dest_data_dir, exist_ok=True)
        debug_print(f"Exists now: {os.path.exists(dest_data_dir)}")

        debug_print(f"Working directory: {os.getcwd()}")
        copy_dcm_files(dose_files, dest_data_dir)

        debug_print("--- Copying dcm structure file over ---")
        copy_dcm_files(struct_file, dest_data_dir)

        
        # Generate all files required for simulation
        debug_print("\n--- Generating simulation files ---")
        generatefiles.generate_files(ct_files[0], plan_file, dose_files, PATH_TO_TEMPLATES, DATA, configpath, ct_for_simulation, sim_dir)
        
        debug_print("\n" + "="*80)
        debug_print(" MAIN FUNCTION COMPLETED SUCCESSFULLY")
        debug_print("="*80)


if __name__=="__main__":
    try:
        main()
        debug_print("\n Script completed successfully")
    except Exception as e:
        debug_print(f"\nFATAL ERROR: {e}")
        import traceback
        debug_print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)