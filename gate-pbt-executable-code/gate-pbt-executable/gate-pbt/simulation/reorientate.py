# -*- coding: utf-8 -*-
"""
Created on Mon Apr 26 17:08:15 2021
@author: Steven Court

Both Gate and GateTools have problems dealing with images in which the
directionality of the axes (TransformMatrix in mhd file) are negative.
This is frequently the case for non-HFS patient positions.

This module will force all axes directions to +1 and appropriately correct
the image Origin as well as rotate the voxel array

TODO: ensure all possible cases are dealt with

TODO: HFS, HFP, FFS, FFP only require 180 degree rotations hence image
        array is always the same shape.  
      Not true for 90 degree rotations, i.e. any decubitus positions
"""

import numpy as np
import itk



def force_positive_directionality( image ):
    """Return altered mhd image with positive axes directionality
    
    Accepts path to mhd image or itk image object
    Returns mhd image
    """
    
    img = None 
    if type( image )==str:
        #Assume we have file path
        img = itk.imread( image )
    else:
        #Assume we have itk image object
        img = image

    print(f"[DEBUG reorient] BEFORE - Origin: {img.GetOrigin()}")
    print(f"[DEBUG reorient] BEFORE - Direction: {np.array(img.GetDirection())}")  

    spacing = img.GetSpacing()
    origin = img.GetOrigin()
    size = img.GetLargestPossibleRegion().GetSize()
    direction = np.array( img.GetDirection()*[1,1,1] )

    print(f"[DEBUG reorient] Input direction diagonal: {direction}")
    print(f"[DEBUG reorient] Input origin: {origin}")
    print(f"[DEBUG reorient] Input size: {size}")
    print(f"[DEBUG reorient] Input spacing: {spacing}")
    
    # Calculate image bounds BEFORE transformation
    end_coords = [origin[i] + (size[i]-1)*spacing[i]*direction[i] for i in range(3)]
    print(f"[DEBUG reorient] BEFORE transform - image Z range: {min(origin[2], end_coords[2])} to {max(origin[2], end_coords[2])}")
    
    new_origin=[]
    for d,o,sz,sp in zip( direction, origin, size, spacing ):
        if d==-1:
            orig = o - (sz-1)*sp
            new_origin.append(orig)
        else:
            new_origin.append( o )
        
        arr = itk.array_from_image( img )
        
    rot_arr = None   
    if np.array_equal( direction, np.array([1,1,1]) ):
        pass  # no need to reorientate        
    elif np.array_equal( direction, np.array([-1,-1,1]) ):
        #(1,2 for z-axes)  (2,1) opposite sense; take care for 90 degrees.
        rot_arr = np.rot90( arr, k=2, axes=(1,2) )   
    elif np.array_equal( direction, np.array([1,-1,-1]) ):
        rot_arr_1 = np.rot90( arr, k=2, axes=(1,2) )   
        rot_arr = np.rot90( rot_arr_1, k=2, axes=(0,2) )   #(0,2 for y-axis)
    else:
        print("TransformMatrix (Direction) of image not handled correctly")
        print("Exiting")
        exit(0)

    if rot_arr is not None:
        new_img = itk.image_from_array( rot_arr )
        new_img.CopyInformation(img)
        new_img.SetOrigin( new_origin )
        new_img.SetDirection( np.array([[1,0,0],[0,1,0],[0,0,1]]) )
        
        new_size = new_img.GetLargestPossibleRegion().GetSize()
        new_end = [new_origin[i] + (new_size[i]-1)*spacing[i] for i in range(3)]
        print(f"[DEBUG reorient] AFTER transform - new origin: {new_origin}")
        print(f"[DEBUG reorient] AFTER transform - image Z range: {new_origin[2]} to {new_end[2]}")
        
        return new_img
    else:
        return img
