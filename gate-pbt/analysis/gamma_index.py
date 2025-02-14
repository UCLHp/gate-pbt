# -----------------------------------------------------------------------------
#   Copyright (C): OpenGATE Collaboration
#   This software is distributed under the terms
#   of the GNU Lesser General  Public Licence (LGPL)
#   See LICENSE.md for further details
#
# Code taken from GateTools (https://github.com/OpenGATE/GateTools) - thanks!
# Compare two 3D images using the gamma index formalism as introduced by Daniel Low (1998)
# -----------------------------------------------------------------------------

"""
Global gamma analysis between 2 ITK images.
If ddpercent is True, dd is taken as a percentage of the max TPS dose (not ideal if hotspots of 110%).
TODO: Modify for local gamma analysis.
"""

import numpy as np
import itk
from scipy.spatial import cKDTree

def get_gamma_index(ref,target,**kwargs):
    """
    Compare two 3D images using the gamma index formalism introduced by Daniel Low (1998).

    :param ref: Reference image (should behave like an ITK image object)
    :type ref: itk.Image or similar
    :param target: Target image (should behave like an ITK image object)
    :type target: itk.Image or similar
    :param **kwargs: Additional keyword arguments (see below)
    :return: Image containing gamma index values, with the same geometry as the target image
    :rtype: itk.Image

    **Keyword arguments:**

    - **dd**: Dose difference scale as a relative value, in units of percent (default is percentage of the max dose in the target image)
    - **ddpercent**: Boolean flag; True (default) means that dd is given in percent, False means that dd is absolute
    - **dta**: Distance to agreement in millimeters (e.g., 3mm)
    - **threshold**: Minimum dose value (exclusive) for calculating gamma values
    - **verbose**: Boolean flag; True will result in a progress bar. All other output goes to the "debug" level.

    For all target voxels in the overlap between ref and target that have dose > threshold, a gamma index value is given.
    For all other voxels, the "defvalue" is assigned.
    """
    return gamma_index_3d(ref,target,**kwargs)



def closest_voxel_index(coord, origin, spacing):
    """
    Calculates the index of the closest voxel to a given coordinate in physical space.

    :param coord: Physical coordinate (x, y, z)
    :type coord: numpy.ndarray or list of floats
    :param origin: Origin of the image in physical space (x0, y0, z0)
    :type origin: numpy.ndarray or list of floats
    :param spacing: Spacing between voxels along each axis (dx, dy, dz)
    :type spacing: numpy.ndarray or list of floats
    :return: Index of the closest voxel in the image array
    :rtype: numpy.ndarray of ints
    """
    return np.round((coord - origin) / spacing).astype(int)

def GetGamma(d0, d1, x0, x1, y0, y1, z0, z1, Max, dd, dta, gamma_method):
    """
    Calculates the gamma index between two dose points in 3D space.

    :param d0: Dose value at the reference point
    :type d0: float
    :param d1: Dose value at the target point
    :type d1: float
    :param x0: X-coordinate of the reference point
    :type x0: float
    :param x1: X-coordinate of the target point
    :type x1: float
    :param y0: Y-coordinate of the reference point
    :type y0: float
    :param y1: Y-coordinate of the target point
    :type y1: float
    :param z0: Z-coordinate of the reference point
    :type z0: float
    :param z1: Z-coordinate of the target point
    :type z1: float
    :param Max: Maximum dose value used for normalization
    :type Max: float
    :param dd: Dose difference criterion (in percent)
    :type dd: float
    :param dta: Distance to agreement criterion (in millimeters)
    :type dta: float
    :param gamma_method: global or local
    :type spacing: string
    :return: Gamma index value between the two points
    :rtype: float
    """
    if gamma_method == 'local':
        norm_val = d0
    elif gamma_method =='global':
        norm_val = Max
    else:
        print('Please specify gamma method correctly, local or global.')
        return False
    
    return np.sqrt(
        (d1 - d0) ** 2 / (0.01 * dd * norm_val) ** 2 +
        (x1 - x0) ** 2 / dta ** 2 +
        (y1 - y0) ** 2 / dta ** 2 +
        (z1 - z0) ** 2 / dta ** 2
    )

def gamma_index_3d(imgref, imgtarget, dta=3., dd=3., ddpercent=True, threshold=0., defvalue=-1., verbose=False):
    gamma_method = 'global'
    """
    Computes the global gamma index between two 3D images using different interpolation methods.

    :param imgref: Reference image (ITK image object)
    :type imgref: itk.Image
    :param imgtarget: Target image (ITK image object)
    :type imgtarget: itk.Image
    :param dta: Distance to agreement criterion in millimeters (default 3.0 mm)
    :type dta: float
    :param dd: Dose difference criterion; if ddpercent is True, dd is in percent (default 3.0)
    :type dd: float
    :param ddpercent: If True, dd is interpreted as a percentage of the maximum dose in the target image (default True)
    :type ddpercent: bool
    :param threshold: Minimum dose value (exclusive) for calculating gamma values (default 0.0)
    :type threshold: float
    :param defvalue: Default gamma index value for voxels outside the calculation (default -1.0)
    :type defvalue: float
    :param verbose: If True, outputs progress information (default False)
    :type verbose: bool
    :return: Image with gamma index values, matching the geometry of the target image
    :rtype: itk.Image

    The target image is the array over which we loop; each voxel in this array must pass or fail.
    The reference image is the array we search over to find similarity to a given target voxel.

    This function iterates over the closest reference voxels and perturbs them along each dimension.
    The optimal position between voxels is found and checked to see if the gamma criteria are met.
    It utilizes both linear and cubic interpolation methods for comparison.
    """
    referenceImage = imgtarget # REFERENCE - WE SEARCH OVER THIS ONE
    targetImage = imgref # TARGET - WE LOOP OVER EACH VOXEL AND PASS OR FAIL

    # Get arrays and adjust the axes
    referenceArray = itk.array_view_from_image(referenceImage).swapaxes(0, 2)
    targetArray = itk.array_view_from_image(targetImage).swapaxes(0, 2)

    gamma_array = np.full(targetArray.shape, -1.0, dtype=float)

    max_targ = np.max(targetArray) # Maximum target dose value, use for finding 10% cut off
    
    if len(referenceArray.shape) != 3 or len(targetArray.shape) != 3: # classic check
        return None

    # Get the origins and spacings, and swap axes accordingly
    referenceArrayOrigin = np.array(referenceImage.GetOrigin())  # Adjusted for swapped axes
    referenceArraySpacing = np.array(referenceImage.GetSpacing())
    targetArrayOrigin = np.array(targetImage.GetOrigin())
    targetArraySpacing = np.array(targetImage.GetSpacing())
    
    # Get dimensions
    I, J, K = referenceArray.shape
    I_t, J_t, K_t = targetArray.shape

    # Create coordinate arrays for the reference array in its physical space
    x_ref = referenceArrayOrigin[0] + np.arange(I) * referenceArraySpacing[0]
    y_ref = referenceArrayOrigin[1] + np.arange(J) * referenceArraySpacing[1]
    z_ref = referenceArrayOrigin[2] + np.arange(K) * referenceArraySpacing[2]


    X_ref, Y_ref, Z_ref = np.meshgrid(x_ref, y_ref, z_ref, indexing='ij')
    ref_coords = np.vstack([X_ref.ravel(), Y_ref.ravel(), Z_ref.ravel()]).T

    # Create KDTree for efficient nearest neighbor search on source coordinates
    tree = cKDTree(ref_coords)

    # Target coordinates
    x_tgt = targetArrayOrigin[0] + np.arange(I_t) * targetArraySpacing[0]
    y_tgt = targetArrayOrigin[1] + np.arange(J_t) * targetArraySpacing[1]
    z_tgt = targetArrayOrigin[2] + np.arange(K_t) * targetArraySpacing[2]
    

    
    gamma, gammaLocal, total = 0, 0, 0 # for gamma calc in testing
    
    # Loop over each target position 
    for Xt in x_tgt:
        for Yt in y_tgt:
            for Zt in z_tgt:
                point = np.array([Xt, Yt, Zt])

                #  the correspoding array index
                tgt_index = closest_voxel_index(point, targetArrayOrigin, targetArraySpacing) 
                tgt_index = np.clip(tgt_index, [0, 0, 0], np.array(targetArray.shape) - 1)
                
                # the target dose value
                tgt_value = targetArray[tuple(tgt_index)]

                
                
                # only calculate over 10 % of maximum target dose
                
                if tgt_value < 0.1*max_targ:
                    continue
                total+=1

                # we are now considering this voxel - Gamma is instantiated as fail

                gamma_array[tuple(tgt_index)] = 1.1 
                                

                # Find the 4 closest points in the source grid
                distances, indices = tree.query(np.array([Xt, Yt, Zt]), k=4) # 4 chosen for speed, recall voxels share z coord

               
                found = False  # Flag to indicate when to exit all loops
                foundLoc = False

                # iterate over 4 closest references voxels
                for idx in indices:
                    if foundLoc:
                        if found:
                            break  # Exit the outer loop if found
                    
                    closest_ref_point = ref_coords[idx]  # (x, y, z) coordinates of closest reference point
                    X, Y, Z = closest_ref_point[0], closest_ref_point[1], closest_ref_point[2]

                    # Calculate the corresponding index in the reference array
                    i_ref = int((X - referenceArrayOrigin[0]) / referenceArraySpacing[0])
                    j_ref = int((Y - referenceArrayOrigin[1]) / referenceArraySpacing[1])
                    k_ref = int((Z - referenceArrayOrigin[2]) / referenceArraySpacing[2])

                    # Get the exact dose value at the reference point
                    ref_value = referenceArray[i_ref, j_ref, k_ref]
                                        
                    # First pass
                    # strictly speaking, this is not a first filter, as we only loop over 4 voxels
                    # in reality, we would need to loop over all voxels within dta and check for filter 1
                    Gamma = GetGamma(tgt_value, ref_value, Xt, X, Yt, Y, Zt, Z, max_targ, dd, dta, gamma_method)
                    GammaLocal = GetGamma(tgt_value, ref_value, Xt, X, Yt, Y, Zt, Z, max_targ, dd, dta, 'local')
                    if GammaLocal <=1:
                        gammaLocal +=1
                        foundLoc = True
                        
                    if Gamma <= 1: 
                        gamma += 1
                        found = True
                        # update gamma array values for each method
                        gamma_array[tuple(tgt_index)] = Gamma
                        #break  # Exit the outer loop
                    
                    if foundLoc:
                        if found:
                            break

                    dirns = [+1, -1]

                    # loop over 3 dimensions
                    for D in range(3):

                        # loop over both directions, i.e. +X or -X
                        for dirn in dirns:
                            x,y,z = X,Y,Z
                            xLoc,yLoc,zLoc = X,Y,Z
                            # interpolating in X
                            if D == 0:
                                # check we are not at a boundary
                                if i_ref + dirn > referenceArray.shape[D]:
                                    continue
                                elif i_ref + dirn <= 0:
                                    continue
                                # get dose value at next voxel
                                ref_value_next = referenceArray[int(i_ref + dirn), j_ref, k_ref]

                                #calculate the optimum x position, and the corresponding dose value
                                x, interpolated_value = min_gamma(X, X + dirn*referenceArraySpacing[D], ref_value, ref_value_next, Xt, tgt_value, dd, dta, max_targ, referenceArraySpacing[D], gamma_method)
                                xLoc, interpolated_valueLoc = min_gamma(X, X + dirn*referenceArraySpacing[D], ref_value, ref_value_next, Xt, tgt_value, dd, dta, max_targ, referenceArraySpacing[D], 'local')

                                # simple check to see if x is within bounds of approximation
                                if x == False:
                                    continue
                            # interpolating in Y
                            elif D == 1:
                                if j_ref + dirn > referenceArray.shape[D]:
                                    continue
                                elif j_ref + dirn <= 0:
                                    continue
                                ref_value_next = referenceArray[i_ref, int(j_ref + dirn), k_ref]
                                y, interpolated_value = min_gamma(Y, Y + dirn*referenceArraySpacing[D], ref_value, ref_value_next, Yt, tgt_value, dd, dta, max_targ, referenceArraySpacing[D], gamma_method)
                                yLoc, interpolated_valueLoc = min_gamma(Y, Y + dirn*referenceArraySpacing[D], ref_value, ref_value_next, Yt, tgt_value, dd, dta, max_targ, referenceArraySpacing[D], 'local')
                                if y == False:
                                    continue
                            # interpolating in Z
                            elif D == 2:
                                if k_ref + dirn > referenceArray.shape[D]:
                                    continue
                                elif k_ref + dirn  <= 0:
                                    continue
                                ref_value_next = referenceArray[i_ref, j_ref, int(k_ref + dirn)]
                                if ref_value == ref_value_next:
                                    continue
                                z, interpolated_value = min_gamma(Z, Z + dirn*referenceArraySpacing[D], ref_value, ref_value_next, Zt, tgt_value, dd, dta, max_targ, referenceArraySpacing[D], gamma_method)
                                zLoc, interpolated_valueLoc = min_gamma(Z, Z + dirn*referenceArraySpacing[D], ref_value, ref_value_next, Zt, tgt_value, dd, dta, max_targ, referenceArraySpacing[D], 'local')
                                if z == False:
                                    continue

                            # simple gamma calc function
                            Gamma = GetGamma(tgt_value, interpolated_value, Xt, x, Yt, y, Zt, z, max_targ, dd, dta, gamma_method)
                            GammaLocal = GetGamma(tgt_value, interpolated_valueLoc, Xt, xLoc, Yt, yLoc, Zt, zLoc, max_targ, dd, dta, 'local')
                            
                            
                            
                            # do they pass?
                            if GammaLocal <=1:
                                gammaLocal +=1
                                foundLoc =True
                            if Gamma <= 1:
                                gamma += 1
                                found = True
                                gamma_array[tuple(tgt_index)] = Gamma
                            if foundLoc:
                                if found:
                                    break
                        if foundLoc:
                            if found:
                                break  # Exit the outer loop if inner loop condition was met
                    if foundLoc:
                        if found:
                            break
    
    print('Global Gamma - linear interpolation method = ',100.0 - 100*gamma_array[gamma_array>1].size / gamma_array[gamma_array>0].size, '%')
    print('Local Gamma - linear interpolation method = ', gammaLocal/total * 100, '%')
    
    # convert to image, note we copy information from targetimage
    gimg=itk.image_from_array(gamma_array.swapaxes(0,2).astype(np.float32).copy())
    gimg.CopyInformation(targetImage)

    return gimg

def min_gamma(x1, x2, y1, y2, tx, ty, dd, dta, Max, spacing, gamma_method):
    """
    Finds the optimal position along a dimension to minimize the gamma index contribution.

    :param x1: Coordinate of the first reference point (could be x, y, or z)
    :type x1: float
    :param x2: Coordinate of the second reference point
    :type x2: float
    :param y1: Dose value at the first reference point
    :type y1: float
    :param y2: Dose value at the second reference point
    :type y2: float
    :param tx: Coordinate of the target point along the same dimension
    :type tx: float
    :param ty: Dose value at the target point
    :type ty: float
    :param dd: Dose difference criterion (percent)
    :type dd: float
    :param dta: Distance to agreement criterion (mm)
    :type dta: float
    :param Max: Maximum dose value used for normalization
    :type Max: float
    :param spacing: Spacing along the dimension
    :type spacing: float
    :param gamma_method: global or local
    :type spacing: string
    :return: Tuple containing the optimal coordinate (`x_opto`) and interpolated dose value (`interpolated_value`), or (False, False) if invalid
    :rtype: tuple

    This function solves for the linear fit parameters for the dose relationship with position.
    It calculates the optimal position such that the gamma contribution is minimized.
    If the optimal position is not between the two reference voxels, it returns False.
    """
    

    # y = grad * x + c
    grad = (y2-y1)/(x2-x1)
    c = y2 - grad*x2
    # optimal x position ( or y or z when iterating over those dimensions )
    
    # optimal x position for local or global gamma
   
    if gamma_method == 'local':
        x_opto= (grad*ty/(dd*0.01*ty)**2 + tx*1/(dta)**2 - grad*c/(dd*0.01*ty)**2)/(grad**2/(dd*0.01*ty)**2 + 1/dta**2)
    elif gamma_method == 'global':
        x_opto = (grad*ty/(dd*0.01*Max)**2 + tx*1/(dta)**2 - grad*c/(dd*0.01*Max)**2)/(grad**2/(dd*0.01*Max)**2 + 1/dta**2)
    else:
        print('Please specify gamma method correctly, local or global.')
        return False, False
    
    if (min(x1, x2) > x_opto) or (x_opto > max(x1, x2)): # point is invalid
        # not in limit
        return False, False
    elif min(x1, x2) < x_opto < max(x1, x2):
        return x_opto, grad*x_opto+c