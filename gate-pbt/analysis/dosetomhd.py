# -*- coding: utf-8 -*-
"""
@author: Steven Court

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
    z_spacing = ds.GridFrameOffsetVector[1]-ds.GridFrameOffsetVector[0]  ##TODO: assumed these are equal but they might not be with our scanner
    pixelspacing = [xy_spacing[0],xy_spacing[1]] + [z_spacing]
    
    # ASSUME THIS IS ALWAYS A DIAGONAL MATRIX WITH VALS +/- 1
    orientation = [ float(x) for x in ds.ImageOrientationPatient]
    zor=None
    # HOW TO DO THIS CORRECTLY! What info is in the dose dicom file!?  TODO
    # Can't use GridFrameOffsetVector as always positive
    if imgpospat[2] < 0:  
        zor = 1
    else:
        zor = -1
    direction = np.array( orientation + [0,0,zor] )
    mhdtransform = direction.reshape(3,3)    

    # Set ITK image properties (for mhd file)
    doseimg = itk.image_from_array( px_data )
    doseimg.SetOrigin( imgpospat )
    doseimg.SetSpacing( pixelspacing )
    doseimg.SetDirection( mhdtransform )
    
    # Save file is outpath specified
    if outpath is None:
        #itk.imwrite(doseimg, "EclipseDose.mhd")
        return doseimg
    else:
        itk.imwrite(doseimg, "EclipseDose.mhd")
 
    
    
    