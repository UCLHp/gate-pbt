# -*- coding: utf-8 -*-
"""
@author: Steven Court
Method converting dicom CT series to 3D mhd image
"""

import sys
from os.path import join

import itk

from gatetools.image_convert import read_dicom



def dcm2mhd_gatetools(ct_files):
    """Testing gatetools; matches below method"""
    itk_img = read_dicom( ct_files )
    itk.imwrite(itk_img, "ct_gatetools.mhd") 



def dcm2mhd( dirName, output ):
    """Convert series of 2D dicom images to mhd + raw files

    Code taken from: https://itk.org/ITKExamples/src/IO/GDCM/ReadDICOMSeriesAndWrite3DImage/Documentation.html

    Need to aovid case of multiple seriesUIDs being found: if dose is different
    from CT then wrong voxel sizes / image dims will be used
    """

    ## Using MET_SHORT will half the file size in comparison to
    ## MET_FLOAT. Allows values -32768 to 32767. 
    ## Is this sufficient for an extended CT range?
    PixelType = itk.ctype('signed short')  
    #PixelType = itk.ctype('float')  
    Dimension = 3
    ImageType = itk.Image[PixelType, Dimension]
    
    namesGenerator = itk.GDCMSeriesFileNames.New()
    namesGenerator.SetUseSeriesDetails(True)
    namesGenerator.AddSeriesRestriction("0008|0021")
    namesGenerator.SetGlobalWarningDisplay(False)
    namesGenerator.SetDirectory(dirName)
    
    seriesUID = namesGenerator.GetSeriesUIDs()
    
    if len(seriesUID) < 1:
        print('No DICOMs in: ' + dirName)
        sys.exit(1)
    
    print('The directory: ' + dirName)
    print('Contains the following DICOM Series: ')
    for uid in seriesUID:
        print(uid)
    
    seriesFound = False
    for uid in seriesUID:
        seriesIdentifier = uid
        print('Reading: ' + seriesIdentifier)
        fileNames = namesGenerator.GetFileNames(seriesIdentifier)
    
        reader = itk.ImageSeriesReader[ImageType].New()
        dicomIO = itk.GDCMImageIO.New()
        reader.SetImageIO(dicomIO)
        reader.SetFileNames(fileNames)
    
        writer = itk.ImageFileWriter[ImageType].New()
    
        outFileName = join(output)
    
        writer.SetFileName(outFileName)
        writer.SetInput(reader.GetOutput())
        print('Writing: ' + outFileName)
        writer.Update()
    
        if seriesFound:
            break


       


#def dose_dcm2mhd_norm(ds):
#    """
#    Method to convert a dcm dose file into mhd+raw image 
#    Dose is normalized to max
#    """            
#    # Must cast to numpy.float32 for ITK to write mhd with ElementType MET_FLOAT
#    px_data = ds.pixel_array.astype(np.float32)   
#    
#    print( "\n***Generating mhd from dose dicom ***")
#    print( "  PixelData shape = {}".format(px_data.shape) )
#
#    # DoseGridScaling * pixel_value gives dose in DoseUnits
#    # Gives total plan dose for field, not fraction dose.
#    scale = ds.DoseGridScaling   
#    units = ds.DoseUnits 
#    print("  DoseUnits: {}".format(units))  
#    print("  DoseGridScale: {}".format(scale))
#    print("  DoseImageDims: {}".format(px_data.shape))
#
#    print("  Scaling dose to {}".format(units) )
#    px_data = px_data * scale     
#    print("  Max scaled dose = {}Gy".format( np.max(px_data) ) )  
#    
#    # TODO: Can I normalize or should we be comparing absolute doses?
#    # Gate DoseActor gives us option to normalize to max so we could compare these?
#    mx = np.max( px_data )
#    px_data = px_data / mx
#        
#    imgpospat = ds.ImagePositionPatient
#    xy_spacing = ds.PixelSpacing
#    ##orientation = ds.ImageOrientationPatient?
#    z_spacing = ds.GridFrameOffsetVector[1]-ds.GridFrameOffsetVector[0]  ##TODO: assumed these are equal but they might not be with our scanner
#    pixelspacing = [xy_spacing[0],xy_spacing[1]] + [z_spacing]
#    
#    # 3D ITK image 
#    doseimg = itk.image_from_array( px_data )
#    doseimg.SetOrigin( imgpospat )
#    doseimg.SetSpacing( pixelspacing )
#    ##doseimg.SetDirection( orientation )
#    
#    itk.imwrite(doseimg, "EclipseDose.mhd")



