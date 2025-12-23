# -*- coding: utf-8 -*-
"""
@author: Steven Court

Pull dose uncertainty stats from structure
"""

import itk
import numpy as np
import pydicom
import matplotlib.pyplot as plt
import os
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


import numpy as np
import matplotlib.pyplot as plt
import itk

def getUncertaintyPlots(uncertainty_path, dose_path, nsim, nreq):
    """
    Analyze and visualize dose uncertainty data, focusing on clinically relevant regions.
    """
    try:
        ImageType = itk.Image[itk.F, 3]
        
        # Read uncertainty image
        uncert_reader = itk.ImageFileReader[ImageType].New()
        uncert_reader.SetFileName(uncertainty_path)
        uncert_reader.Update()
        doseUncert_img = uncert_reader.GetOutput()
        
        # Read dose image
        dose_reader = itk.ImageFileReader[ImageType].New()
        dose_reader.SetFileName(dose_path)
        dose_reader.Update()
        dose_img = dose_reader.GetOutput()
        
    except RuntimeError as e:
        print(f"Error loading images: {e}")
        raise
    
    # Convert to numpy arrays
    doseUncert = itk.array_view_from_image(doseUncert_img).swapaxes(0, 2)
    dose = itk.array_view_from_image(dose_img).swapaxes(0, 2)



    UncertOrigin = np.array(doseUncert_img.GetOrigin())  # Adjusted for swapped axes
    UncertSpacing = np.array(doseUncert_img.GetSpacing())
    doseOrigin = np.array(dose_img.GetOrigin())
    doseSpacing = np.array(dose_img.GetSpacing())

    '''
    
    # Find maximum dose for threshold calculations
    max_dose = np.max(dose)
    
    # Create masks for different dose levels
    mask_1pct = dose > (0.01 * max_dose)
    mask_10pct = dose > (0.10 * max_dose)
    mask_50pct = dose > (0.50 * max_dose)
    
    # Calculate statistics for different regions
    stats = {
        'all_voxels': {
            'mean': np.mean(doseUncert),
            'median': np.median(doseUncert),
            'std': np.std(doseUncert)
        },
        'above_1pct': {
            'mean': np.mean(doseUncert[mask_1pct]),
            'median': np.median(doseUncert[mask_1pct]),
            'std': np.std(doseUncert[mask_1pct])
        },
        'above_10pct': {
            'mean': np.mean(doseUncert[mask_10pct]),
            'median': np.median(doseUncert[mask_10pct]),
            'std': np.std(doseUncert[mask_10pct])
        },
        'above_50pct': {
            'mean': np.mean(doseUncert[mask_50pct]),
            'median': np.median(doseUncert[mask_50pct]),
            'std': np.std(doseUncert[mask_50pct])
        }
    }
    
    # Create figure with multiple plots
    fig = plt.figure(figsize=(15, 15))
    
    # Adjust the layout to prevent overlap
    plt.subplots_adjust(hspace=0.4, wspace=0.3)
    
    # Plot 1: All voxels
    ax1 = plt.subplot(221)
    ax1.hist(doseUncert.flatten(), bins=100, density=True, alpha=0.75, color='skyblue')
    ax1.set_title('All Voxels', pad=20, fontsize=12, fontweight='bold')
    ax1.set_xlabel('Relative Uncertainty', fontsize=10)
    ax1.set_ylabel('Density', fontsize=10)
    mean_line = ax1.axvline(stats['all_voxels']['mean'], color='red', linestyle='--', 
                label=f"Mean: {stats['all_voxels']['mean']:.3f}")
    ax1.legend(loc='upper right')
    
    # Plot 2: >1% max dose
    ax2 = plt.subplot(222)
    ax2.hist(doseUncert[mask_1pct].flatten(), bins=100, density=True, alpha=0.75, color='lightgreen')
    ax2.set_title('Voxels >1% of Max Dose', pad=20, fontsize=12, fontweight='bold')
    ax2.set_xlabel('Relative Uncertainty', fontsize=10)
    ax2.set_ylabel('Density', fontsize=10)
    mean_line = ax2.axvline(stats['above_1pct']['mean'], color='red', linestyle='--', 
                label=f"Mean: {stats['above_1pct']['mean']:.3f}")
    ax2.legend(loc='upper right')
    
    # Plot 3: >10% max dose
    ax3 = plt.subplot(223)
    ax3.hist(doseUncert[mask_10pct].flatten(), bins=100, density=True, alpha=0.75, color='salmon')
    ax3.set_title('Voxels >10% of Max Dose', pad=20, fontsize=12, fontweight='bold')
    ax3.set_xlabel('Relative Uncertainty', fontsize=10)
    ax3.set_ylabel('Density', fontsize=10)
    mean_line = ax3.axvline(stats['above_10pct']['mean'], color='red', linestyle='--', 
                label=f"Mean: {stats['above_10pct']['mean']:.3f}")
    ax3.legend(loc='upper right')
    
    # Plot 4: >50% max dose
    ax4 = plt.subplot(224)
    ax4.hist(doseUncert[mask_50pct].flatten(), bins=100, density=True, alpha=0.75, color='plum')
    ax4.set_title('Voxels >50% of Max Dose', pad=20, fontsize=12, fontweight='bold')
    ax4.set_xlabel('Relative Uncertainty', fontsize=10)
    ax4.set_ylabel('Density', fontsize=10)
    mean_line = ax4.axvline(stats['above_50pct']['mean'], color='red', linestyle='--', 
                label=f"Mean: {stats['above_50pct']['mean']:.3f}")
    ax4.legend(loc='upper right')
    
    # Add grid to all plots
    for ax in [ax1, ax2, ax3, ax4]:
        ax.grid(True, alpha=0.3)
    
    # Add a main title to the figure
    plt.suptitle('Dose Uncertainty Distribution Analysis', fontsize=14, fontweight='bold', y=0.95)
    
    plt.show()
    '''

    top_indices = np.argsort(dose.flatten())[-10:]
    max_dose_median = np.median(dose.flatten()[top_indices])

    fifty_mask = dose >= 0.5 * (max_dose_median)
    fifty_uncert = doseUncert[fifty_mask] * 100
    
    ninety_mask = dose >= 0.9 * (max_dose_median)
    ninety_uncert = doseUncert[ninety_mask] * 100
    
    over50_vol = np.sum(fifty_mask) * doseSpacing[0] * doseSpacing[1]* doseSpacing[2]

    
    results = {
        'top50%_mean': np.mean(fifty_uncert),
        'top50%_median': np.median(fifty_uncert),
        'top90%_mean': np.mean(ninety_uncert),
        'top90%_median': np.median(ninety_uncert),
        'voxel_size_x': doseSpacing[0],
        'voxel_size_y': doseSpacing[1],
        'voxel_size_z': doseSpacing[2],
        'n_primaries': nsim,
        'n_primaries_req': nreq,
        'total_voxels': dose.size,
        'over50DoseVol': over50_vol
    }
    
    
    return results


#if __name__=="__main__":
#    main()




    