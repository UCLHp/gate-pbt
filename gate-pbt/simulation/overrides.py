# -*- coding: utf-8 -*-
"""
Created on Thu Nov 21 10:17:18 2019
@author: SCOURT01

Methods to apply HU overrides directly to image pixels. Should:
    (i)  Replace all pixels outside external with air HU=-1000
   (ii)  Replace all pixels within a specified structure

"""

import itk
import pydicom
import gatetools.roi_utils as rt


#testing Gatetools
import roiutils


########################
HU_AIR = -1000
########################


def get_external_name( structure_file ):          ## TODO: MAKE THIS MORE ROBUST; WHAT WILL OUR NAMING CONVENTION BE?
    """Get contour name (BODY or EXTERNAL) """
    contour = ""
    ds = pydicom.dcmread( structure_file )
    rois = rt.list_roinames( ds )
    if "EXTERNAL" not in rois and "EXT" not in rois and "BODY" not in rois:
        print( "\n ERROR: Structure set does not contain EXTERNAL, EXT or BODY\n")
    elif "EXTERNAL" in rois:
        contour = "EXTERNAL"
    elif "EXT" in rois:
        contour = "EXT"
    elif "BODY" in rois:
        contour = "BODY"
    
    return contour



def set_air_external( img_file, structure_file, output_img_file ):
    """Set all HUs outside of BODY/EXTERNAL contour to air HU=-1000
    
    The img_file must be the .mhd
    """

    img = itk.imread( img_file )
    ds = pydicom.dcmread( structure_file )
    
    contour = get_external_name( structure_file )
  
    
    # MODIFYING GATETOOLS; get_mask() disn't work for HFP setup
    aroi = roiutils.region_of_interest(ds,contour)
    mask = aroi.get_mask(img, corrected=False)
    #itk.imwrite(mask, "mask.mhd")
    
    '''
    aroi = rt.region_of_interest( ds, contour)
    mask = aroi.get_mask(img, corrected=False)  
    # NOTE: if corrected=True mask has dtype=np.float32; if not dtype=np.uint8
    ''' 
    
    pix_mask = itk.array_view_from_image(mask)
    pix_img = itk.array_view_from_image(img) 
    
    if( pix_mask.shape!=pix_img.shape ):
        print( "Inconsistent shapes of mask and image"  )
    
    pix_img_flat = pix_img.flatten()
    for i,val in enumerate( pix_mask.flatten() ):
        if val==0:
            pix_img_flat[i] = HU_AIR
    pix_img = pix_img_flat.reshape( pix_img.shape )
    img_modified = itk.image_view_from_array( pix_img )
    
    img_modified.CopyInformation(img)
    
    #img_modified.SetSpacing( img.GetSpacing()  ) # "ElementSpacing" in .mhd
    #img_modified.SetOrigin( img.GetOrigin() )    # "Offset" in .mhd

    itk.imwrite(img_modified, output_img_file )





def override_hu( img_file, structure_file, output_img, structure, hu ):   #MAYBE JUST PASS THE IMAGE OBJECT AND DICOM OBJECT??
    """Override all HUs inside of specified structure"""

    img = itk.imread( img_file )
    ds = pydicom.dcmread( structure_file )
  
    
    # TESTING GATETOOLS
    aroi = roiutils.region_of_interest(ds,structure)
    mask = aroi.get_mask(img, corrected=False)    
    ##aroi = rt.region_of_interest( ds, structure )
    ##mask = aroi.get_mask(img, corrected=False)
    
    pix_mask = itk.array_view_from_image(mask)
    pix_img = itk.array_view_from_image(img) 
    if( pix_mask.shape!=pix_img.shape ):
        print( "Inconsistent shapes of mask and image"  )
    
    pix_img_flat = pix_img.flatten()
    for i,val in enumerate( pix_mask.flatten() ):
        if val==1:
            pix_img_flat[i] = hu
    pix_img = pix_img_flat.reshape( pix_img.shape )
    img_modified = itk.image_view_from_array( pix_img )
    
    img_modified.CopyInformation(img)
    ##img_modified.SetSpacing( img.GetSpacing()  ) # "ElementSpacing" in .mhd
    ##img_modified.SetOrigin( img.GetOrigin() )    # "Offset" in .mhd

    itk.imwrite(img_modified, output_img )

