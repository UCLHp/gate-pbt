# -*- coding: utf-8 -*-
"""
@author: Steven Court
Modified method from GateTools here (thanks):
https://github.com/OpenGATE/GateTools/blob/master/gatetools/gamma_index.py

Takes two dose distributions (in mhd + raw format) and performs
a 3D gamma analysis using the gatetools function.

If images are of different dimensions the method will force a match by
resampling the MC dose to match the dimensions of the TPS dose.
(Doing this because the _unequal_geometry method in GateTools does not work
for certain non-HFS patient positions).

Low 1998 uses TPS dose as target and measured dose as ref
       -> Use TPS as target and Monte Carlo as ref
"""

import numpy as np
import itk

#from gatetools import gamma_index as gi
import gamma_index

import reorientate


########################################################################
#DTA = 3                 # mm
#DD = 3                  # %
DOSE_THRESHOLD = 0.1    # Absolute threshold = this * max tps dose
########################################################################



def gamma_image( ref_dose, target_dose, dta_val, dd_val ):
    """ Gamma analysis of MC and TPS beam dose using GateTools
    
    Accepts ITK-like image, or path to image
    Returns image matching dimensions of target
    Set ref -> MC dose, target -> TPS dose
    """    
    ref, targ = None, None 
    if type(ref_dose)==str:
        #Assume we have file path
        ref = itk.imread( ref_dose )
    else:
        #Assume we have image file
        ref = ref_dose
    if type(target_dose)==str:
        targ = itk.imread( target_dose )
    else:
        targ = target_dose    
        
        
    # Force +ve axes directionality for gatetools methods
    #   --> No need to resample dose images
    targ = reorientate.force_positive_directionality( targ )
    #ref = reorientate.force_positive_directionality( ref )
    
             
    max_tps_dose = np.max( targ )
    ##print("    max tps dose = ", max_tps_dose)
    gamma_threshold = max_tps_dose * DOSE_THRESHOLD   
    #gamma = gi.get_gamma_index( ref, targ, dta=DTA, dd=DD, ddpercent=True, threshold=gamma_threshold)  
    gamma = gamma_index.get_gamma_index( ref, targ, dta=dta_val, dd=dd_val, ddpercent=True, threshold=gamma_threshold)  
    
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


    
    
    
if __name__=="__main__":
    tps_dose = itk.imread("EclipseDose.mhd")
    mc_dose = itk.imread("Gatedose.mhd")
    
    # Low 1998 uses TPS dose as target and measured dose as ref
    #        -> Use TPS as target and monte carlo as ref
    gamma_img = gamma_image( mc_dose, tps_dose )  #(ref, targ)
    itk.imwrite(gamma_img, "gamma_img.mhd")
 
    pass_rate = get_pass_rate( gamma_img )
    print("  Gamma pass rate = {}%".format( round(pass_rate,2) ))




'''
def resample( img, refimg ):
    """ Resample image to same dimensions as reference 
    
    No: Can we just simply resample a dose grid like this?
        Should there not be some mas-weighting?
    """ 

    spacing = refimg.GetSpacing()
    origin = refimg.GetOrigin()
    direction = refimg.GetDirection()
    size = refimg.GetLargestPossibleRegion().GetSize()
       
    resampleFilter = itk.ResampleImageFilter.New(Input=img)
    resampleFilter.SetOutputSpacing(spacing)
    resampleFilter.SetOutputOrigin(origin)
    resampleFilter.SetOutputDirection(direction)
    resampleFilter.SetSize(size)
    
    #Default interpolation is LinearInterpolateImageFunction<InputImageType, TInterpolatorPrecisionType>, 
    #which is reasonable for ordinary medical images. However, some synthetic images have pixels 
    #drawn from a finite prescribed set. An example would be a mask indicating the segmentation of a 
    #brain into a small number of tissue types. For such an image, one does not want to interpolate between
    #different pixel values, and so NearestNeighborInterpolateImageFunction< InputImageType, TCoordRep > would be a better choice.   

    resampleFilter.Update()
    return resampleFilter.GetOutput()
'''



