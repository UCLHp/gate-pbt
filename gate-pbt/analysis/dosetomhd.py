# -*- coding: utf-8 -*-
"""
@author: Steven Court

Method to convert dicom dose file to mhd format for import
into GateTools' gamma analysis function
"""
import numpy as np

import itk
import pydicom


def dcm2mhd( dicomfile, patientposition="HFS", outpath=None ):
    """
    Convert a dcm field dose file into mhd+raw image 
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
    z_spacing = ds.GridFrameOffsetVector[1]-ds.GridFrameOffsetVector[0]  
    ## (assume z spacings equal, but may not be for some protocols)
    pixelspacing = [xy_spacing[0],xy_spacing[1]] + [z_spacing]
    
    # For CT scan this is always a diagonal matrix wiwth vals +/- 1
    orientation = [ float(x) for x in ds.ImageOrientationPatient]
    ##print("XXX ORIENTATION = ",orientation)
    # Directionality of z-axis comes from cross product of x and y directions
    zor = ds.ImageOrientationPatient[0] * ds.ImageOrientationPatient[4]
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
 
    
    
    