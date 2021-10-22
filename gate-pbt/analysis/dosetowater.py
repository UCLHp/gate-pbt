# -*- coding: utf-8 -*-
"""
@author: Steven Court

Method to retrospectively convert MC dose to material -> dose to water
for comparison with planning system.
See Paganetti2009 "Dose to water versus dose to medium in proton beam
therapy".
"""

import itk
import numpy as np



def resample( img, refimg ):
    """ Resample image to same dimensions as reference """ 

    spacing = refimg.GetSpacing()
    origin = refimg.GetOrigin()
    direction = refimg.GetDirection()
    size = refimg.GetLargestPossibleRegion().GetSize()
       
    resampleFilter = itk.ResampleImageFilter.New(Input=img)
    resampleFilter.SetOutputSpacing(spacing)
    resampleFilter.SetOutputOrigin(origin)
    resampleFilter.SetOutputDirection(direction)
    resampleFilter.SetSize(size)
    
    #Default interpolation is LinearInterpolateImageFunction<InputImageType, TInterpolatorPrecisionType>, 
    #which is reasonable for ordinary medical images. However, some synthetic images have pixels 
    #drawn from a finite prescribed set. An example would be a mask indicating the segmentation of a 
    #brain into a small number of tissue types. For such an image, one does not want to interpolate between
    #different pixel values, and so NearestNeighborInterpolateImageFunction< InputImageType, TCoordRep > would be a better choice.   

    resampleFilter.Update()
    return resampleFilter.GetOutput()



def get_rsps_from_emcalc(emcalcpath):
    """Return dictionary of materials and RSPs found in simulation"""
    lines = open(emcalcpath,"r").readlines()
    
    # Get mass stopping power of water
    msp_water = 5.30047  # default I=78 and density 1g/cm3   
    for line in lines:
        if "G4_WATER" in line:
            cols = line.split()
            msp_water = float(cols[7])
            print("    msp_water = ",msp_water)
      
    # Form dictionary of RSPs
    rsps = {}
    start_reading = False
    for line in lines:
        if start_reading and "#" not in line and len(line)>1:
            cols = line.split()
            material = cols[0]
            #rsp = float(cols[7])*float(cols[1])  / msp_water
            rsp = float(cols[7])  / msp_water
            rsps[material] = rsp
            print("    material={}; rsp={}; dens={}".format(material,round(rsps[material],3),cols[1]  )  )
        if "worldDefaultAir" in line:
            start_reading = True
    
    return rsps




def convert_dose_to_water(ctpath, dosepath, emcalcpath, hu2matpath, output=None):
    """Convert a doseimg (to material) to dose-to-water
       Divide dose-to-tissue by RSP; see Paganetti2019
       
    Input: paths to ct image and doseToMaterial image   
    """
    
    rsps = get_rsps_from_emcalc(emcalcpath)
    hu2mat = open(hu2matpath,"r").readlines()
    
    # Read lower HU bracket and physical density from materials database
    #hu_lims, den_lims = read_densities(materialdbpath)
       
    ctimg = itk.imread( ctpath )
    doseimg = itk.imread( dosepath )
    
    # Resample CT image to match voxel resolution of dose image
    resampledimg = resample( ctimg, doseimg )
    #itk.imwrite(resampledimg, "resampled_ct.mhd")  
    
    hus = itk.array_from_image( resampledimg )
    doses = itk.array_from_image( doseimg )
    shape = hus.shape 
    
    hus_flat = hus.flatten()    
    doses_flat = doses.flatten() 
    d2water = np.zeros(len(hus_flat))
     
    if len(hus_flat)!=len(doses_flat):
        print("ERROR: resampled image does not match dose image dimensions")
        exit()
    else:
        for i,hu in enumerate(hus_flat):

            # Get material name from HU
            material=""
            for line in hu2mat:
                cols = line.split()
                if hu < float(cols[1]):
                    material = cols[2]
                    break
            if material=="":
                print(" NO MATERIAL ASSIGNED for HU={}".format(hu))
                material = "Adiposetissue3"
                        
            rsp = rsps[material]
            d2w = doses_flat[i] / rsp
       
            if d2w<0:
                print("  WARNING: d2water < 0 detected")
            d2water[i] = d2w
         
        d2water_arr = d2water.reshape( shape )
        
        dosetowater = itk.image_view_from_array( d2water_arr )
        dosetowater.CopyInformation(doseimg)
        
        if output is not None:
            itk.imwrite(dosetowater, output)      
        return dosetowater
    
    
    


def main():
    
    ctimg = "ct_air.mhd"
    doseimg = "merged-Dose.mhd"
    
    ###ctimg = itk.imread("ct_air.mhd")
    ###doseimg = itk.imread("merged-Dose.mhd")

    dosetowaterimg = convert_dose_to_water(ctimg, doseimg)

    itk.imwrite(dosetowaterimg, "dose2water.mhd")
    
    
    
if __name__=="__main__":
    main()