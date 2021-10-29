# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods to apply HU overrides directly to image pixels. Should:
    (i)  Replace all pixels outside external with air HU=-1000
   (ii)  Replace all pixels within a specified structure

"""

import itk
import pydicom
import gatetools.roi_utils as roiutils
##import roiutils


########################
HU_AIR = -1000
########################


    

def get_external_name( structure_file ):
    """Get contour name of external patient contour"""
    contour = ""
    contains_bolus = False
    ss = pydicom.dcmread( structure_file )    
    for struct in ss.RTROIObservationsSequence:
        if struct.RTROIInterpretedType.lower() == "external":
            contour = struct.ROIObservationLabel
            #print("Found external: {}".format(contour))
        elif struct.RTROIInterpretedType.lower() == "bolus":
            print("\n\nWARNING: Bolus found. It will be overriden with air.\n")
    if contour=="":
        raise Exception("No external structure found. Exiting.")
        exit(1)
    return contour



def set_air_external( image, structure_file ):
    """Set all HUs outside of BODY/EXTERNAL contour to air HU=-1000
    
    The img_file must be the .mhd
    """
    
    img = None 
    if type(image)==str:
        #Assume we have file path
        img = itk.imread( image )
    else:
        #Assume we have itk image object
        img = image   
        
    ds = pydicom.dcmread( structure_file )   
    contour = get_external_name( structure_file )
      
    # get_mask() doesn't work for HFP setup; need to reorientate
    aroi = roiutils.region_of_interest(ds,contour)
    mask = aroi.get_mask(img, corrected=False)
    
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
    return img_modified





def override_hu( image, structure_file, structure, hu ):   #MAYBE JUST PASS THE IMAGE OBJECT AND DICOM OBJECT??
    """Override all HUs inside of specified structure"""

    ds = pydicom.dcmread( structure_file )
    img = None 
    if type(image)==str:
        #Assume we have file path
        img = itk.imread(image)
    else:
        #Assume we have itk image object
        img = image   
    
    aroi = roiutils.region_of_interest(ds,structure)
    mask = aroi.get_mask(img, corrected=False)    
 
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

    #itk.imwrite(img_modified, output_img )
    return img_modified

