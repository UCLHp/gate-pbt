# -*- coding: utf-8 -*-
"""
@author: Steven Court

Code to take 2 dose distributions (in mhd + raw format)
and perform a 3D gamma analysis using the gatetools function.

With the _unequal_ method, images can have different dimensions,
resolutions and origins.
"""

import random
import numpy as np
import itk

import pydicom
import gatetools as gt


DTA = 3                 # mm
DD = 3                  # %

DOSE_THRESHOLD = 0.1    # Absolute dose; TODO: change to % prescription)



def gamma_image( ref_dose, target_dose ):
    """ Gamma analysis of MC and TPS beam dose using GateTools
    
    Return accepts ITK-like image, or path to image
    Returns image matching dimensions of target
    Set ref -> TPS, target -> Monte Carlo
    """
    
    tps, mc = None, None
    
    if type(ref_dose)==str:
        #Assume we have file path
        tps = itk.imread( ref_dose )
    else:
        #Assume we have image file
        tps = ref_dose
    if type(target_dose)==str:
        mc = itk.imread( target_dose )
    else:
        mc = target_dose    
        
        
    max_tps_dose = np.max( tps )
    ##print("    max tps dose = ", max_tps_dose)
    gamma_threshold = max_tps_dose * DOSE_THRESHOLD  ## TODOD: SENSIBLE THRESHOLD??
    
      
    # Gamma img will have dimensions of MC img
    gamma = gt.get_gamma_index( tps, mc, dta=DTA, dd=DD, ddpercent=True, threshold=gamma_threshold)
    #gamma = gt.get_gamma_index( mc, tps, dta=DTA, dd=DD, ddpercent=True, threshold=gamma_threshold)

    
    return gamma


    
    
def get_pass_rate( gamma_img ):
    """Return gamma pass rate
    """

    gamma_vals = itk.GetArrayViewFromImage(gamma_img)
    max_gam = float(np.max(gamma_vals))
    print( "  Max gamma = {}".format( round(max_gam,2)  ) )
    # Only look at valid gammas (i.e. > 0) for % fail count
    pass_rate = 100.0 - 100*gamma_vals[gamma_vals>1].size / gamma_vals[gamma_vals>0].size
    #print( "  Gamma < 1 = {}%".format( pass_rate )  )  
    
    return pass_rate





#########################################################################
#TODO; THIS WILL ONLY WORK IF MHD DOSE IS SAME DIMENSIONS ETC AS DCMFILE
#########################################################################
    
#TODO; THESE ARE ALREADY IN dosetodicom.py; combine

def rand_digits_str( digits_to_modify ):
    """
    Return a zero-padded random 4 digit string to modify the dicom UIDs
    """
    limit = 10**digits_to_modify - 1
    return str( int(random.random()*limit) ).zfill(digits_to_modify)


def mhd2dcm(mhdFile, dcmFile, output, dosescaling=None):
    """
    Takes mhd dose from Gate and the dicom dose file corresponding field,
    modifes appropriate dicom fields for import into Eclipse.
    
    Optional scaling of dose    
    """
    
    if dosescaling==None:
        #print("No dose scaling specified")
        dosescaling = 1
    
    dcm = pydicom.dcmread(dcmFile)
    mhd=None
    if type(mhdFile)==str:
        mhd = itk.imread(mhdFile)
    else:
        #Assume image
        mhd = mhdFile  ##TODO: TIDY THIS
    
    ###### Alter UID tags  -- TODO: what exactly needs changed?
    digits_to_modify = 4
    digits = rand_digits_str( digits_to_modify )
    
    sopinstanceuid = dcm.SOPInstanceUID 
    dcm.SOPInstanceUID = sopinstanceuid[:-digits_to_modify] + digits
    
    studyinstanceuid = dcm.StudyInstanceUID 
    dcm.StudyInstanceUID = studyinstanceuid[:-digits_to_modify] + digits
    
    seriesinstanceuid = dcm.SeriesInstanceUID 
    dcm.SeriesInstanceUID = seriesinstanceuid[:-digits_to_modify] + digits
    #####################################################
    
    # NOT NECESSARY; USING ORIGINAL FIELD DICOM DOSE
    dcm.PixelSpacing = list( mhd.GetSpacing() )[0:2]
    dcm.ImagePositionPatient =  list( mhd.GetOrigin() )

    mhdpix = itk.array_from_image(mhd)
    
    
    # REPLACE THE -1 DEFAULT GAMMA VALUES  TODO: more robust
    mhdpix[ mhdpix<0 ] = 0
    
    
    # mhd.GetLargestPossibleRegion().GetSize() gives [cols, rows, slices]
    # pixel_array.shape gives [slices, rows, cols]
    dcm.NumberOfFrames = mhdpix.shape[0]
    dcm.Rows = mhdpix.shape[1]            # ARE THESE CORRECT WAY ROUND?
    dcm.Columns = mhdpix.shape[2]
    
    #Is GridFrameOffsetVector always in "relative interpretations"?
    # TODO: check this is safe
    dcm.GridFrameOffsetVector = [ x*mhd.GetSpacing()[2] for x in range(mhdpix.shape[0]) ]
         
    dose_abs = mhdpix * dosescaling
    
    scale_to_int = 1E4   
    mhd_scaled = dose_abs * scale_to_int
    mhd_scaled = mhd_scaled.astype(int)       
    dcm.PixelData = mhd_scaled.tobytes()
    
    dcm_scaling = 1.0/scale_to_int
    dcm.DoseGridScaling = dcm_scaling  
   
    dcm.save_as( output )


