# -*- coding: utf-8 -*-
"""
Created on Sat Jan 30 17:05:33 2021
@author: SCOURT01

Method to convert dicom dose file to mhd format for import
into GateTools' gamma analysis function
"""
import numpy as np

import itk
import pydicom


def dcm2mhd( dicomfile, outpath=None ):
    """
    Convert a dcm dose file into mhd+raw image 
    """           
    
    ds = pydicom.dcmread( dicomfile )
    # Must cast to numpy.float32 for ITK to write mhd with ElementType MET_FLOAT
    px_data = ds.pixel_array.astype(np.float32)   
    
    #print( "\n***Generating mhd from dose dicom ***")
    #print( "  PixelData shape = {}".format(px_data.shape) )

    # DoseGridScaling * pixel_value gives dose in DoseUnits
    # Gives total plan dose for field, not fraction dose.
    scale = ds.DoseGridScaling   
    #units = ds.DoseUnits 
    #print("  DoseUnits: {}".format(units))  
    #print("  DoseGridScale: {}".format(scale))
    #print("  DoseImageDims: {}".format(px_data.shape))

    #print("  Scaling dose to {}".format(units) )
    px_data = px_data * scale     
    #print("  Max scaled dose = {}Gy".format( np.max(px_data) ) )  
        
    imgpospat = ds.ImagePositionPatient
    xy_spacing = ds.PixelSpacing
    ##orientation = ds.ImageOrientationPatient?
    z_spacing = ds.GridFrameOffsetVector[1]-ds.GridFrameOffsetVector[0]  ##TODO: assumed these are equal but they might not be with our scanner
    pixelspacing = [xy_spacing[0],xy_spacing[1]] + [z_spacing]
    
    # 3D ITK image 
    doseimg = itk.image_from_array( px_data )
    doseimg.SetOrigin( imgpospat )
    doseimg.SetSpacing( pixelspacing )
    ##doseimg.SetDirection( orientation )
    
    # Save file is outpath specified
    if outpath is None:
        return doseimg
    else:
        itk.imwrite(doseimg, "EclipseDose.mhd")
 
    
    
    