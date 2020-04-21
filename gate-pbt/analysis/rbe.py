# -*- coding: utf-8 -*-
"""
Created on Mon Jan 27 12:41:48 2020
@author: SCOURT01

Script to combine a Gate dose image and LET image
"""

import itk


def let_mcmahon2018( doseimg, letimg ):
    """ Produce dose-weighted LET using: dose*(1+k*LET)
    
    From Gate:
    LET = keV/um
    Dose = Gy (but may be normalised to max or specified as dose to water)
    k (kappa) = 0.055 um/keV from McMahon2018
    """
    
    #TODO: CHECK UNITS ARE CORRECT (DOSE, KAPPA, LET)   
    #TODO: CHECK DOSE AND LET IMGS HAVE SAME INFORMATION (resolution,size,type,etc)
    
    #dosenp = itk.array_view_from_image(doseimg)
    #letnp = itk.array_view_from_image(letimg)
    dosenp = itk.array_from_image(doseimg)
    letnp = itk.array_from_image(letimg)
    
    weightednp = dosenp*( 1 + 0.055*letnp )
    weightedimg = itk.image_from_array(weightednp)
    weightedimg.CopyInformation(doseimg)
    
    return weightedimg




#doseimg = itk.imread(r"M:\vGATE-GEANT4\ClusterSimulationTesting\EarCanal_LET\Total_merged-Dose.mhd")
#letimg = itk.imread(r"M:\vGATE-GEANT4\ClusterSimulationTesting\EarCanal_LET\Total_merged-LET.mhd")

doseimg = itk.imread(r"M:\vGATE-GEANT4\gatefileprep\sobp_hfs_results\merged-Dose.mhd")
letimg = itk.imread(r"M:\vGATE-GEANT4\gatefileprep\sobp_hfs_results\merged-LET.mhd")

weightedimg = let_mcmahon2018(doseimg, letimg)

itk.imwrite(weightedimg, "Total_McMahonLET.mhd")






'''
## Check pixel multiplaaction worked
pix = itk.array_view_from_image(doseimg) 
print(pix[40][60][150])
pix2 = itk.array_view_from_image(letimg) 
print(pix2[40][60][150])
pix3 = itk.array_view_from_image(weightedimg) 
print(pix3[40][60][150])
'''
