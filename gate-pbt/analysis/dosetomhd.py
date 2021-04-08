# -*- coding: utf-8 -*-
"""
@author: Steven Court

Method to convert dicom field dose file to mhd format for use
into GateTools' gamma analysis function
"""

from math import isclose
import numpy as np
import itk
import pydicom


def get_transform_matrix( ds ):
    """Return 3x3 TransformMatrix for mhd image from dicom field dose
    """ 
    # Directionality of z-axis (+/- 1) can be defined in two ways as described 
    # here: https://dicom.innolitics.com/ciods/rt-dose/rt-dose/3004000c
    zdir=None
    if hasattr(ds, "GridFrameOffsetVector"):
        if (ds.ImageOrientationPatient==[1,0,0,0,1,0] and 
         isclose(ds.ImagePositionPatient[2],ds.GridFrameOffsetVector[0]) ):
            # then z-directionality from GridFrameOffsetVector
            diff = ds.GridFrameOffsetVector[0] - ds.GridFrameOffsetVector[1]
            if diff>0:
                zdir = -1
            elif diff<0:
                zdir = 1
        elif isclose(0,ds.GridFrameOffsetVector[0]):
            # then z-directionality from cross product of x and y directions
            zdir = ds.ImageOrientationPatient[0]*ds.ImageOrientationPatient[4]
        else:
            print("ERROR: z-directionality not defined")          
    else:
        print("ERROR: no GridFrameOffsetVector in dicom field dose")

    # For CT scan orientation always a diagonal matrix wiwth vals +/- 1
    orientation = [ float(x) for x in ds.ImageOrientationPatient]
    direction = np.array( orientation + [0,0,zdir] )
    mhdtransform = direction.reshape(3,3)  
    return mhdtransform



def dcm2mhd( dcmfilepath, outpath=None ):
    """
    Convert a dcm field dose file into mhd+raw image 
    """   
    
    ds = pydicom.dcmread( dcmfilepath ) 
    
    # Only want absolute dose (Gy)
    if ds.DoseUnits != "GY":
        print("WARNING: Dose units in {} not Gy".format(dcmfilepath))

    # Must cast to numpy.float32 for ITK to write mhd with ElementType MET_FLOAT
    px_data = ds.pixel_array.astype(np.float32)  
    # DoseGridScaling * pixel_value gives dose in DoseUnits
    # Total plan dose for field, not fraction dose
    scale = ds.DoseGridScaling   
    px_data = px_data * scale     
            
    xy_spacing = ds.PixelSpacing      
    ## Assume z spacings equal, but may not be for some protocols
    z_spacing = ds.GridFrameOffsetVector[1]-ds.GridFrameOffsetVector[0]  
    
    pixelspacing = [xy_spacing[0],xy_spacing[1]] + [z_spacing]
    mhdtransform = get_transform_matrix( ds )
    imgpospat = ds.ImagePositionPatient
    
    # Set ITK image properties for mhd file
    doseimg = itk.image_from_array( px_data )
    doseimg.SetOrigin( imgpospat )
    doseimg.SetSpacing( pixelspacing )
    doseimg.SetDirection( mhdtransform )
    
    # Save file if outpath specified
    if outpath is None:
        #itk.imwrite(doseimg, "EclipseDose.mhd")
        return doseimg
    else:
        itk.imwrite(doseimg, "EclipseDose.mhd")
 
    
    
    