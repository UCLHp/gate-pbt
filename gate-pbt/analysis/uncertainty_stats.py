# -*- coding: utf-8 -*-
"""
@author: Steven Court

Pull dose uncertainty stats from structure
"""

import itk
import numpy as np
import pydicom
import matplotlib.pyplot as plt

import gatetools.roi_utils as roiutils


def get_stats_struct( uncertpath, dicom_struct, struct_name):
    """Generate stats from a dose image and uncertainty image;
    but only for pixels inside specified structure
    """
    uncertimg = itk.imread(uncertpath)
    uncert_flat = itk.array_from_image(uncertimg).flatten()      
    ds = pydicom.dcmread( dicom_struct )
      
    aroi = roiutils.region_of_interest(ds,struct_name)
    mask = aroi.get_mask(uncertimg, corrected=False)    
    mask_voxels_flat = itk.array_view_from_image(mask).flatten()
     
    relevant_uncerts = []
    for i,val in enumerate(mask_voxels_flat):
        if val==1:
            relevant_uncerts.append( uncert_flat[i] )
            
    relevant_uncerts = np.array( relevant_uncerts )
    
    print()
    print("Number of voxels in {} = {}".format(struct_name,len(relevant_uncerts)))
    print("Mean uncertainty = {}".format(relevant_uncerts.mean() ) )
    print("Median = {}".format(np.median(relevant_uncerts)))
    print("Max = {}".format(relevant_uncerts.max()))
    print("Min = {}".format(relevant_uncerts.min()))
    print("Std dev = {}".format(relevant_uncerts.std() ) )
           
    # Make histogram
    ymax = int(relevant_uncerts.max() * 100 + 2)
    binsize = 0.01
    bins = [i*binsize for i in range( int(ymax/binsize) ) ]
    plt.hist( 100*relevant_uncerts, bins=bins )
    plt.xlabel("Dose uncertainty (%)")
    plt.show()
     
    

  
def main():
    
    # Specify paths to uncertainty image, RS dicom file, plus structure name
    uncertimgpath = r""
    rsdcmfile = r""   
    STRUCT_NAME = ""

    get_stats_struct(uncertimgpath, rsdcmfile, STRUCT_NAME)




if __name__=="__main__":
    main()




    