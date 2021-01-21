# -*- coding: utf-8 -*-
"""
Created on Mon Dec  9 12:59:03 2019
@author: SCOURT01

Code to take 2 dose distributions (in mhd + raw format)
and perform a 3D gamma analysis using the gatetools function.

With the _unequal_ method, images can have different dimensions,
resolutions and origins.
"""


import numpy as np
import itk

import gatetools as gt



## Print gamma pass stats from the gamma image

img = itk.imread("gamma.mhd")
gamma_vals = itk.GetArrayViewFromImage(img)
print( "  Max gamma = {}".format( np.max(gamma_vals) ) )
# Only look at valid gammas (i.e. > 0) for % fail count
print( "  Gamma < 1 = {}%".format( 100.0 - gamma_vals[gamma_vals>1].size/gamma_vals[gamma_vals>0].size*100   )  )




## The gatetools gamma_index() only accepts itk images as input
## imread() automatically detects pixel type and image dimensions
#
#'''
#img1 = itk.imread("test1\KickT2-3d-pat-Dose.mhd")
#img2 = itk.imread("test1\KickTz0-3d-pat-Dose.mhd")
#gamma_img = gt.gamma_index.gamma_index_3d_equal_geometry(img1, img2, dta=5.0, dd=5.0, ddpercent=True)
#'''
#
##img1 = itk.imread("3d-pat-Dose.mhd")
##img2 = itk.imread("zITK333_test.mhd")
#img1 = itk.imread("SummedDose.mhd")
#img2 = itk.imread("letWeightedDose.mhd")
#
#
## Image created will have dims of img2
#gamma_img = gt.gamma_index.gamma_index_3d_unequal_geometry(img1, img2, dta=3.0, dd=3.0, ddpercent=True)
#
## Write mhd+raw image for visualization
#itk.imwrite(gamma_img, "Gamma_3.mhd")
#
#gamma_vals = itk.GetArrayViewFromImage(gamma_img)
#print( "  Max gamma = {}".format( np.max(gamma_vals) ) )
## Only look at valid gammas (i.e. > 0) for % fail count
#print( "  Gamma < 1 = {}%".format( 100.0 - gamma_vals[gamma_vals>1].size/gamma_vals[gamma_vals>0].size*100   )  )
