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
 - Global gamma analysis between 2 ITK images
 - If ddpercent, take as % of max TPS dose (not ideal if hotspots of 110%)
 - TODO: modify for local gamma analysis
"""


import numpy as np
import itk


def _reldiff2(dref,dtarget,ddref):
    """
    Convenience function for implementation of the following functions.
    The arguments `dref` and `dtarget` maybe scalars or arrays.
    The calling code is responsible for avoiding division by zero (make sure that ddref>0).
    """
    ddiff=dtarget-dref
    reldd2=(ddiff/ddref)**2
    return reldd2


def get_gamma_index(ref,target,**kwargs):
    """
    Compare two 3D images using the gamma index formalism as introduced by Daniel Low (1998).
    The positional arguments 'ref' and 'target' should behave like ITK image objects.
    Possible keyword arguments include:
    * dd indicates "dose difference" scale as a relative value, in units of percent
      (the dd value is this percentage of the max dose in the target (TPS dose) image)
    * ddpercent is a flag, True (default) means that dd is given in percent, False means that dd is absolute.
    * dta indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * threshold indicates minimum dose value (exclusive) for calculating gamma values
    * verbose is a flag, True will result in a progress bar. All other chatter goes to the "debug" level.
    Returns an image with the same geometry as the target image.
    For all target voxels in the overlap between ref and target that have d>dmin, a gamma index value is given.
    For all other voxels the "defvalue" is given.
    """
    return gamma_index_3d(ref,target,**kwargs)



def gamma_index_3d(imgref,imgtarget,dta=3.,dd=3.,ddpercent=True,threshold=0.,defvalue=-1.,verbose=False):
    """
    Compare 3-dimensional arrays with possibly different spacing and different origin, using the
    gamma index formalism, popular in medical physics.
    We assume that the meshes are *NOT* rotated w.r.t. each other.
    * `dd` indicates by default the "dose difference" scale as a relative value,
      in units percent (the dd value is this percentage of the max dose in the reference image).
    * If `ddpercent` is False, then dd is taken as an absolute value.
    * `dta` indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * `threshold` indicates minimum dose value (exclusive) for calculating gamma values
    Returns an image with the same geometry as the target image.
    For all target voxels that are in the overlap region with the refernce image and that have d>threshold,
    a gamma index value is given. For all other voxels the "defvalue" is given.
    """
    # get arrays
    aref = itk.array_view_from_image(imgref).swapaxes(0,2)
    atarget = itk.array_view_from_image(imgtarget).swapaxes(0,2)

    if ddpercent:
        #dd *= 0.01*np.max(atarget)   # Our TPS dose
        dd *= 0.01*np.max(aref)

    print("    dd (Gy) = ",dd)

    # test consistency: both must be 3D
    # it would be cool to make this for 2D as well (and D>3), but not now
    if len(aref.shape) != 3 or len(atarget.shape) != 3:
        return None
    #bbref  = bounding_box(imgref)
    #bbtarget = bounding_box(imgtarget)
    areforigin = np.array(imgref.GetOrigin())
    arefspacing = np.array(imgref.GetSpacing())
    atargetorigin = np.array(imgtarget.GetOrigin())
    atargetspacing = np.array(imgtarget.GetSpacing())
    nx,ny,nz = atarget.shape
    mx,my,mz = aref.shape
    ntot = nx*ny*nz
    mtot = mx*my*mz
    dta2  = dta**2
    mask  = atarget>threshold
    nmask=np.sum(mask)
    if nmask==0:
        #logger.error("target has no dose over threshold.")
        dummy = itk.image_from_array((np.ones(atarget.shape)*defvalue).swapaxes(0,2).copy())
        dummy.CopyInformation(imgtarget)
        return dummy
    # now define the indices of the target image voxel centers
    ixtarget, iytarget, iztarget = np.meshgrid(np.arange(nx),np.arange(ny),np.arange(nz),indexing='ij')
    xtarget = atargetorigin[0]+ixtarget*atargetspacing[0]
    ytarget = atargetorigin[1]+iytarget*atargetspacing[1]
    ztarget = atargetorigin[2]+iztarget*atargetspacing[2]
    # indices ref image voxel centers that are closest to the target image voxel centers
    ixref = np.round((xtarget-areforigin[0])/arefspacing[0]).astype(int)
    iyref = np.round((ytarget-areforigin[1])/arefspacing[1]).astype(int)
    izref = np.round((ztarget-areforigin[2])/arefspacing[2]).astype(int)
    # keep within range
    overlap = (ixref>=0)*(iyref>=0)*(izref>=0)*(ixref<mx)*(iyref<my)*(izref<mz)
    mask *= overlap
    noverlap = np.sum(overlap)
    nmask=np.sum(mask)
    if nmask==0:
        #logger.error("images do not seem to overlap.")
        dummy = itk.image_from_array((np.ones(atarget.shape)*defvalue).swapaxes(0,2).copy())
        dummy.CopyInformation(imgtarget)
        return dummy
    #logger.debug("Reference image has {} x {} x {} = {} voxels.".format(mx,my,mz,mtot))
    #logger.debug("Target image has {} x {} x {} = {} voxels.".format(nx,ny,nz,ntot))
    #logger.debug("{} target voxels are in the intersection of target and reference image.".format(noverlap))
    #logger.debug("{} of these have dose > {}.".format(nmask,threshold))

    # grid of "close points" in reference image
    xref = areforigin[0]+ixref*arefspacing[0]
    yref = areforigin[1]+iyref*arefspacing[1]
    zref = areforigin[2]+izref*arefspacing[2]
    # get a gamma value on this closest point
    gclose2 = np.zeros([nx,ny,nz],dtype=float)
    gclose2[mask] = _reldiff2(aref[ixref[mask],iyref[mask],izref[mask]],atarget[mask],dd) + \
                                              ((xtarget[mask]-xref[mask])**2 + \
                                               (ytarget[mask]-yref[mask])**2 + \
                                               (ztarget[mask]-zref[mask])**2)/dta2
    gclose = np.array(np.sqrt(gclose2))
    #igclose = np.array(np.ceil(np.sqrt(gclose2)),dtype=int)
    g2=np.zeros([nx,ny,nz],dtype=float)
    #print("going to loop over {} voxels with large enough dose in reference image".format(np.sum(mask)))
    for mixref,miyref,mizref,mixtarget,miytarget,miztarget,mgclose in zip(ixref[mask], iyref[mask], izref[mask],
                                                                    ixtarget[mask],iytarget[mask],iztarget[mask],gclose[mask]):
        #dtarget = atarget[mixtarget,miytarget,miztarget]
        #dref = aref[mixref,miyref,mizref]
        ixyztarget = np.array((mixtarget,miytarget,miztarget))
        ixyzref = np.array((mixref,miyref,mizref))
        targetpos = atargetorigin + ixyztarget*atargetspacing
        refpos = areforigin  + ixyzref*arefspacing
        dixyz = np.floor(mgclose*dta/arefspacing).astype(int) # or round, or ceil?
        imax = np.minimum(ixyzref+dixyz+1,(mx,my,mz))
        imin = np.maximum(ixyzref-dixyz  ,( 0, 0, 0))
        mixnear,miynear,miznear = np.meshgrid(np.arange(imin[0],imax[0]),
                                              np.arange(imin[1],imax[1]),
                                              np.arange(imin[2],imax[2]),
                                              indexing='ij')
        g2near  = _reldiff2(aref[mixnear,miynear,miznear],atarget[mixtarget,miytarget,miztarget],dd)
        g2near += (areforigin[0]+mixnear*arefspacing[0]-targetpos[0])**2/dta2
        g2near += (areforigin[1]+miynear*arefspacing[1]-targetpos[1])**2/dta2
        g2near += (areforigin[2]+miznear*arefspacing[2]-targetpos[2])**2/dta2
        g2[mixtarget,miytarget,miztarget] = np.min(g2near)

    g=np.sqrt(g2)
    g[np.logical_not(mask)]=defvalue
    # ITK does not support double precision images by default => cast down to float32.
    # Also: only the first few digits of gamma index values are interesting.
    gimg=itk.image_from_array(g.swapaxes(0,2).astype(np.float32).copy())
    gimg.CopyInformation(imgtarget)
    #logger.debug(f"Computed {nmask} gamma values assuming UNEQUAL geometry in target and reference")
    return gimg
