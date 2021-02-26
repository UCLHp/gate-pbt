# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods for cropping images to dicom structures
"""

import numpy as np
import pydicom
import itk



def crop_to_structure( mhdfile, dcm_struct_file, struct_name, outputimg, margin=0 ):
    """Crop mhd img to ROI in dicom structure file
    
    Optional margin (# voxels) applied isotropically
    """
    img = itk.imread( mhdfile )
    # Find limits of roi in dicom coords
    mincorner,maxcorner = roi_bb_corners( dcm_struct_file, struct_name )
    cropped_img = crop_mhd(img, mincorner, maxcorner, margin)
    itk.imwrite( cropped_img, outputimg )
    


def crop_mhd(img, mincorner, maxcorner, margin):
    """
    Crop an image according from mincorner to maxcorner (x,y,z) coords
    """
    
    dims = np.array(img.GetLargestPossibleRegion().GetSize())
    if len(dims) != 3:
        print("only 3D images supported in crop_mhd")
        exit(0)
    
    # Transform corner coords to indices of img array
    min_wrong = np.array(img.TransformPhysicalPointToIndex( mincorner ))
    max_wrong = np.array(img.TransformPhysicalPointToIndex( maxcorner ))
    # Ensure min and max correct for all patient orientations
    min_indices, max_indices = [],[]
    for i,j in zip(min_wrong, max_wrong):
        min_indices.append( min(i,j) ) 
        max_indices.append( max(i,j)  ) 
        
    # Apply optional margin for crop
    min_indices = np.array(min_indices) - margin
    max_indices = np.array(max_indices) + margin
    
    # From/to indices for cropping respecting image limits
    from_index = np.maximum( np.zeros(3,dtype=int), min_indices )
    #    use +1 here since crop method is exclusive
    to_index = np.minimum( dims, max_indices+1 )
            
    cropper = itk.RegionOfInterestImageFilter.New(Input=img)
    region = cropper.GetRegionOfInterest()
    indx=region.GetIndex()
    size=region.GetSize()
    for j in range(3):
        indx.SetElement(j,int(from_index[j]))
        size.SetElement(j,int(to_index[j]-from_index[j]))
    region.SetIndex(indx)
    region.SetSize(size)
    cropper.SetRegionOfInterest(region)
    cropper.Update()
    return cropper.GetOutput()


  
def roi_bb_corners( dcm_struct, structure ):
    """ Return min and max corners [x,y,z] of the bounding box for 
    specified ROI structure and structure dicom file
    """
    # Get X,Y min and max from structure dicom
    ds = pydicom.dcmread( dcm_struct )
    if not ds.Modality=="RTSTRUCT":
        print("Not a dicom structure file!")
    else:
        ## Get relevant ContourSequence
        roi_num=None
        for ss in ds.StructureSetROISequence:
            if ss.ROIName.lower()==structure.lower():  
                roi_num = ss.ROINumber

        cont_seq=None
        for cs in ds.ROIContourSequence:
            if cs.ReferencedROINumber==roi_num:
                cont_seq = cs.ContourSequence
        
        xmin, xmax = get_cs_limits( cont_seq, "X" )
        ymin, ymax = get_cs_limits( cont_seq, "Y" )
        zmin, zmax = get_cs_limits( cont_seq, "Z" )

        mincorner = [xmin,ymin,zmin]
        maxcorner = [xmax,ymax,zmax]

        return mincorner,maxcorner



def get_cs_limits( cs, axis ):
    """ Get min and max values of ContourSequence in a chosen axis (x, y or z)
    """
    minLim, maxLim = 99999.0, -99999.0 
    
    strt=None
    if axis.lower()=="x":
        strt = 0
    elif axis.lower()=="y":
        strt = 1
    elif axis.lower()=="z":
        strt = 2
    else:
        print("invalid axis: must choose X, Y or Z")
        
    #Loop through ContourImageSequences
    for cis in cs:
        #Format is [x,y,z,x,y,z....]
        coords = cis.ContourData[strt::3]
        for v in coords:
            if v<minLim:
                minLim = v
            if v>maxLim:
                maxLim = v
                       
    return minLim, maxLim





#def main():
#    
#    mhdimg = "ct_air.mhd"
#    dicom_struct = "dcmstruct.dcm"
#    structure = "EXT"
#    
#    crop_to_structure( mhdimg, dicom_struct, structure, "test_crop.mhd", margin=10 )
#
#
#if __name__=="__main__":
#    main()

