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


# TEMPORARY FIX - REMOVE THIS
# Ignore conversion for air / where HU-RSP extrapolation not reliable.
# Set dose to zero here; below this we'd get -ve RSP and so -ve dose
# USE RSP OF AIR WHEN HU < -950 (OR WHATEVER MIN HU IS IN MATERIALS DB)

HU_CUTOFF = -940        # i.e. what is defined as air in Gate
RSP_AIR = 0.001075      # from materials db and emcalc
DENSITY_AIR = 1.21E-3   # (g/cm^3)





## NEEDS UPDATED; SET IN SOME CALIBRATION FILE
def get_rsp(hu):
    """Return RSP for given HU value from fitted CT calibration curve"""
    # Curve split into 3 straight line segments
    rsp = -9E99
    if hu < HU_CUTOFF:
        rsp = RSP_AIR
    elif hu < -73.4:
        rsp = hu*1.0646E-3 + 1.04290
    elif hu < 128.6:
        rsp = hu*6.0457E-4 + 1.00914
    else:
        rsp = hu*4.4232E-4 + 1.03000
          
    return rsp



## NEEDS UPDATED; SET IN SOME CALIBRATION FILE
def get_density(hu):
    """Return RSP for given HU value from fitted CT calibration curve"""
    # Curve split into 3 straight line segments
    dens = -9E99
    if hu < HU_CUTOFF:
        dens = DENSITY_AIR
    elif hu < -62:
        dens = hu*0.001 + 1.00827
    elif hu < 123:
        dens = hu*0.0008 + 0.9931
    else:
        dens = hu*0.0006 + 1.0050
          
    return dens


'''
def get_density(hus, densities, hu_val):
    """Return physical density for given hu_val
    
    Input ordered and matched lists: lower HU bracket values and densities
    """
    if len(hus)!=len(densities):
        print("  HU and density increment lists do not match")
        exit()
    # TODO: check lists are ordered
    
    index=None
    try:
        # first index larger than hu_val
        fi = next(x[0] for x in enumerate(hus) if x[1]>hu_val)
        # index for correct density bracket
        index = fi-1
        if index == -1:
            print("  Warning: HU/density lower than min HU defined in materials db")
            print("     -- Using minimum density value...")
            index = 0
    except StopIteration:
        # and take largest density bracket value
        print("  Warning: HU/density higher than max HU defined in materials db")
        print("     -- Using maximum density value...")
        index = -1
    density = densities[index]
    return density
'''


def read_densities(filename):
    """Read HUs and densities from Gate's patient-HUmaterials.db file
    
    Return list of lower HU in range and corresponding density
    """
    hu_lims=[]
    density_lims=[] 
    with open(filename, "r") as f:
        all_lines = f.readlines()
        for line in all_lines:
            # Line containing HU limits
            if "Material corresponding to H=" in line:
                lower_hu = line.split("H=")[1].strip("[").strip("]").strip().split(";")[0].strip()
                hu_lims.append( float(lower_hu)  )
            # line containing material density
            if ": d=" in line:
                d = float(line.split("d=")[1].split(" ")[0].strip())            
                unit = line.split(" ")[2].strip(";").strip()
                # want density in g/cm3
                if unit=="mg/cm3":
                    d = d/1000.0
                elif unit=="g/cm3":
                    pass
                else:
                    print("  XXX: density unit {} not accounted for".format(unit))
                density_lims.append(d)
                
    return hu_lims, density_lims
                



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




def convert_dose_to_water(ctpath, dosepath, materialdbpath, output=None):
    """Convert a doseimg (to material) to dose-to-water
       Divide dose-to-tissue by RSP; see Paganetti2019
       
    Input: paths to ct image and doseToMaterial image   
    """
    
    # Read lower HU bracket and physical density from materials database
    hu_lims, den_lims = read_densities(materialdbpath)
       
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
            ###if hu < HU_CUTOFF:
            ###    doses_flat[i] = 0
            ###else:
            ###density = get_density(hu_lims, den_lims, hu )
            rsp = get_rsp( hu )
            density = get_density( hu )
            d2water = doses_flat[i] * density / rsp
            if d2water<0:
                print("  WARNING: d2water < 0 detected")
            doses_flat[i] = d2water              
            
        d2water_arr = doses_flat.reshape( shape )
        
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