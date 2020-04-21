# -*- coding: utf-8 -*-
"""
Created on Tue Oct 22 09:30:48 2019

@author: scourt01
"""

import pydicom
import os

################################################################################
# TODO: 
#   (1) Have I got Rows/Columns x/y correct way round throughout?
#   (2) Do I need to fix ImagePositionPatient for our purposes?
#       (or just manually correct the Offset in the CT's mhd file)
#   (3) Should I be making half-pixel shifts?
################################################################################


def crop_dicom( input_dir, output_dir, rowStrt, rowEnd, colStrt, colEnd):
    """Method to crop a series of dicom images to a defined range in X,Y
    
    Will crop all images in the directory to within the row/col boundaries 
    specified.
    """
    
    allfiles = [ f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir,f)) and "CT" in f  ]  
    #print(allfiles)
    #TODO: THIS IS NOT GOOD SAFE TO CHECK IF FILE IS A CT DICOM FILE
           
    for f in allfiles:       
        ds = pydicom.dcmread( os.path.join(input_dir,f) )
        pxdata = ds.pixel_array
        cropped_img = pxdata[ colStrt:colEnd, rowStrt:rowEnd ]
        #plt.imshow(cropped_img, cmap=plt.cm.bone)
        #plt.show()
    
        ds.PixelData = cropped_img.tobytes()
        
        # Set Rows and Columns in dicom
        ds.Rows = cropped_img.shape[0]
        ds.Columns = cropped_img.shape[1]
        
        ds.save_as(  os.path.join(output_dir,f)  )
        
    print("Cropped img rows={}, cols={}".format( cropped_img.shape[0] ,cropped_img.shape[1]  ) )
    
    

def find_roi_limits( RSFile, structure ):
    """ Return dictionary of X,Y,Z min and max coords for given structure
    """
    # Get X,Y min and max from structure dicom
    ds = pydicom.dcmread( RSFile )
    if not ds.Modality=="RTSTRUCT":
        print("Not a dicom structure file!")
    else:
        ## Get relevant ContourSequence
        roi_num=None
        for ss in ds.StructureSetROISequence:
            if ss.ROIName.lower()==structure.lower():  ## WHAT IS IT CALLED?
            #if ss.ROIName.lower()=="external" or ss.ROIName.lower()=="ext":  
                roi_num = ss.ROINumber

        cont_seq=None
        for cs in ds.ROIContourSequence:
            if cs.ReferencedROINumber==roi_num:
                cont_seq = cs.ContourSequence
        
        xmin, xmax = get_limits( cont_seq, "X" )
        ymin, ymax = get_limits( cont_seq, "Y" )
        zmin, zmax = get_limits( cont_seq, "Z" )

        dct = {"minX":xmin, "maxX":xmax, "minY":ymin, "maxY":ymax, "minZ":zmin, "maxZ":zmax }
        return dct


def get_limits( cs, axis ):
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
        coords = cis.ContourData[strt::3]  #Format is [x,y,z,x,y,z....]
        for v in coords:
            if v<minLim:
                minLim = v
            if v>maxLim:
                maxLim = v
                       
    return minLim, maxLim



def find_image_limits( input_dir ):
    """Limits of image in dicom coords
    """
    allfiles = [ f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir,f)) and "CT" in f  ]    
    
    xmin, xmax = 99999.0, -99999.0
    ymin, ymax = 99999.0, -99999.0
    zmin, zmax = 99999.0, -99999.0  
       
    for i,f in enumerate(allfiles):
        
        ds = pydicom.dcmread( os.path.join(input_dir,f) )
        
        z = ds.SliceLocation
        if z<zmin:
            zmin = z
        if z>zmax:
            zmax = z
            
        if i==0:
            #Only get x and y 1 time
            rows = ds.Rows
            cols = ds.Columns
            
            xmin = ds.ImagePositionPatient[0]  ###NO- THIS IS NOT THE MIN; IT CHANGES WITH PATIENT SET UP
            ymin = ds.ImagePositionPatient[1]
            
            xmax = xmin + cols * ds.PixelSpacing[0]
            ymax = ymin + rows * ds.PixelSpacing[1]
         
    dct = {"minX":xmin, "maxX":xmax, "minY":ymin, "maxY":ymax, "minZ":zmin, "maxZ":zmax }
    return dct




def get_img_properties( input_dir ):
    """Method to retrieve Rows, Columns, pixelSpacing"""
    
    properties = {}
    
    ct_files = [ f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir,f)) and "CT" in f  ]
    
    ds = pydicom.dcmread( os.path.join(input_dir,ct_files[0]) )
    
    properties["Rows"] = ds.Rows
    properties["Columns"] = ds.Columns
    properties["PixelSpacing_x"] = ds.PixelSpacing[0]
    properties["PixelSpacing_y"] = ds.PixelSpacing[1]
    properties["SliceThickness"] = ds.SliceThickness

    return properties


 



def main():
    
    #input_dir = "CTdata"
    input_dir = "zzzPaedCranio02_data"
    output_dir = "croppedImg_PaedCranio02"
    
    #### Get Rows, Columns, PixelSpacing(_x,_y) and SliceThickness
    img_properties = get_img_properties( input_dir )
    
    
    #### Find limits of structure (i.e. external) in dicom coords
    dicomRS = "zzzPaedCranio02_data/RS.1.2.246.352.205.4615613331539572209.13800723537771029437.dcm"
    #dicomRS = "CTdata/RS_fullPLan.dcm"
    structure = "external"
    slimits = find_roi_limits( dicomRS, structure )
    #print( "Struct limits: ", slimits["minX"], slimits["maxX"], slimits["minY"], slimits["maxY"], slimits["minZ"], slimits["maxZ"] )
    
    
    #### Find limits of the full image as well as X,Y pixel spacing
    ilimits = find_image_limits( input_dir )
    #print( "Image limits: ", ilimits["minX"], ilimits["maxX"], ilimits["minY"], ilimits["maxY"], ilimits["minZ"], ilimits["maxZ"] )
    
    
    #### Perform cropping and save files
    # Convert ilimits and slimits (COORDS) to get row/columns (ints) for cropping
    xcrop1 = int( (slimits["minX"]-ilimits["minX"])/img_properties["PixelSpacing_x"] )
    xcrop2 = int( img_properties["Columns"] - int( (ilimits["maxX"]-slimits["maxX"])/img_properties["PixelSpacing_x"] ) ) 
    ycrop1 = int( (slimits["minY"]-ilimits["minY"])/img_properties["PixelSpacing_y"] )
    ycrop2 = int( img_properties["Rows"] - int( (ilimits["maxY"]-slimits["maxY"])/img_properties["PixelSpacing_y"] ) ) 

    
    
    
    
    margin = 0 ## TODO: NEED TO CHECK THIS DOESNT GO OUT OF RANGE
    
    #Set the pixel cropping manually
    #margin = 0
    #xcrop1 = 50
    #xcrop2 = 512-50
    #ycrop1 = 50
    #ycrop2 = 512-50        
    
    print("xcrop1, xcrop2, ycrop1, ycrop2: {}, {}, {}, {}".format(xcrop1, xcrop2, ycrop1, ycrop2)   )
    #crop_dicom( input_dir, output_dir, 100, 400, 100, 400 )  # set manually
    crop_dicom( input_dir, output_dir, xcrop1-margin, xcrop2+margin, ycrop1-margin, ycrop2+margin )
    ####
    

    #If we have asymmetrically cropped the image we will have moved the centre
    #position. Image centre is placed at the World's origin in Gate, so we 
    #need an additional shift to the isocentre to account for this
    left_crop = xcrop1-margin
    right_crop = img_properties["Columns"] - (xcrop2+margin)
    top_crop = ycrop1-margin
    bottom_crop = img_properties["Rows"] - (ycrop2+margin)

    if(left_crop-right_crop==0 and top_crop-bottom_crop==0 ):
        print("Symmetric cropping; no additional iso shifts needed")
    else:
        xs = (left_crop-right_crop)/2.0
        ys = (top_crop-bottom_crop)/2.0
        print("Further iso shifts in Gate needed due to asymmetric cropping: ")
        print("    Shift x: {} pixels = {} mm".format(xs, round(xs*img_properties["PixelSpacing_x"],2) ) )
        print("    Shift y: {} pixels = {} mm".format(ys, round(ys*img_properties["PixelSpacing_y"],2) ) )    
    

    
    
if __name__=="__main__":
    main()

