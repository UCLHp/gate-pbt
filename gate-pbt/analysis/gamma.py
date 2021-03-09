# -*- coding: utf-8 -*-
"""
@author: Steven Court
Modified method from GateTools here (thanks):
https://github.com/OpenGATE/GateTools/blob/master/gatetools/gamma_index.py

Takes two dose distributions (in mhd + raw format) and performs
a 3D gamma analysis using the gatetools function.

If images are of different dimensions the method will force a match by
resampling the MC dose to match the dimensions of the TPS dose.
(Doing this because the _unequal_geometry method in GateTools does not work
for certain non-HFS patient positions).

Low 1998 uses TPS dose as target and measured dose as ref
       -> Use TPS as target and monte carlo as ref
"""

import random
import numpy as np
import itk
import pydicom

#import logging
#logger=logging.getLogger(__name__)




########################################################################
DTA = 3                 # mm
DD = 3                  # %
DOSE_THRESHOLD = 0.1    # Absolute threshold = this * max tps dose
########################################################################




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
      (the dd value is this percentage of the max dose in the reference image)
    * ddpercent is a flag, True (default) means that dd is given in percent, False means that dd is absolute.
    * dta indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * threshold indicates minimum dose value (exclusive) for calculating gamma values
    * verbose is a flag, True will result in a progress bar. All other chatter goes to the "debug" level.
    Returns an image with the same geometry as the target image.
    For all target voxels in the overlap between ref and target that have d>dmin, a gamma index value is given.
    For all other voxels the "defvalue" is given.
    """    
    if (np.allclose(ref.GetOrigin(),target.GetOrigin())) and \
       (np.allclose(ref.GetSpacing(),target.GetSpacing())) and \
       (ref.GetLargestPossibleRegion().GetSize() == ref.GetLargestPossibleRegion().GetSize() ):
        print("Dose images have equal geometry =:)")
        return gamma_index_3d_equal_geometry(ref,target,**kwargs)
    else:
        print("Dose images have different geometry. Correcting...")
        # Output from resample( img, ref ) has dimensions of ref
        resampled_ref = resample( ref, target )
        #itk.imwrite(resampled_ref, "resampled_mc_dose.mhd")
        print("Resampled ref (MC) to match target (TPS)")
        return gamma_index_3d_equal_geometry(resampled_ref,target,**kwargs)        



def gamma_index_3d_equal_geometry(imgref,imgtarget,dta=3.,dd=3., ddpercent=True,threshold=0.,defvalue=-1.):
    """
    Compare two images with equal geometry, using the gamma index formalism as introduced by Daniel Low (1998).
    * ddpercent indicates "dose difference" scale as a relative value, in units percent (the dd value is this percentage of the max dose in the reference image)
    * ddabs indicates "dose difference" scale as an absolute value
    * dta indicates distance scale ("distance to agreement") in millimeter (e.g. 3mm)
    * threshold indicates minimum dose value (exclusive) for calculating gamma values: target voxels with dose<=threshold are skipped and get assigned gamma=defvalue.
    Returns an image with the same geometry as the target image.
    For all target voxels that have d>threshold, a gamma index value is given.
    For all other voxels the "defvalue" is given.
    If geometries of the input images are not equal, then a `ValueError` is raised.
    """
    aref=itk.array_view_from_image(imgref).swapaxes(0,2)
    atarget=itk.array_view_from_image(imgtarget).swapaxes(0,2)
    
    if aref.shape != atarget.shape:
        raise ValueError("input images have different geometries ({} vs {} voxels)".format(aref.shape,atarget.shape))
    if not np.allclose(imgref.GetSpacing(),imgtarget.GetSpacing()):
        raise ValueError("input images have different geometries ({} vs {} spacing)".format(imgref.GetSpacing(),imgtarget.GetSpacing()))
    if not np.allclose(imgref.GetOrigin(),imgtarget.GetOrigin()):
        raise ValueError("input images have different geometries ({} vs {} origin)".format(imgref.GetOrigin(),imgtarget.GetOrigin()))
    if ddpercent:
        dd *= 0.01*np.max(aref)
        
    relspacing = np.array(imgref.GetSpacing(),dtype=float)/dta
    inv_spacing = np.ones(3,dtype=float)/relspacing
    g00=np.ones(aref.shape,dtype=float)*-1
    mask=atarget>threshold
    g00[mask]=np.sqrt(_reldiff2(aref[mask],atarget[mask],dd))
    
    nx,ny,nz = atarget.shape
    #ntot = nx*ny*nz
    #nmask = np.sum(mask)
    #logger.debug("Both images have {} x {} x {} = {} voxels.".format(nx,ny,nz,ntot))
    #logger.debug("{} target voxels have a dose > {}.".format(nmask,threshold))
    g2 = np.zeros((nx,ny,nz),dtype=float)

    for x in range(nx):
        for y in range(ny):
            for z in range(nz):
                if g00[x,y,z] < 0:
                    continue
                igmax=np.round(g00[x,y,z]*inv_spacing).astype(int) # maybe we should use "floor" instead of "round"
                if (igmax==0).all():
                    g2[x,y,z]=g00[x,y,z]**2
                else:
                    ixmin = max(x-igmax[0],0)
                    ixmax = min(x+igmax[0]+1,nx)
                    iymin = max(y-igmax[1],0)
                    iymax = min(y+igmax[1]+1,ny)
                    izmin = max(z-igmax[2],0)
                    izmax = min(z+igmax[2]+1,nz)
                    ix,iy,iz = np.meshgrid(np.arange(ixmin,ixmax),
                                           np.arange(iymin,iymax),
                                           np.arange(izmin,izmax),indexing='ij')
                    g2mesh = _reldiff2(aref[ix,iy,iz],atarget[x,y,z],dd)
                    g2mesh += ((relspacing[0]*(ix-x)))**2
                    g2mesh += ((relspacing[1]*(iy-y)))**2
                    g2mesh += ((relspacing[2]*(iz-z)))**2
                    g2[x,y,z] = np.min(g2mesh)
                   
    g=np.sqrt(g2)
    g[np.logical_not(mask)]=defvalue
    # ITK does not support double precision images by default => cast down to float32.
    # Also: only the first few digits of gamma index values are interesting.
    gimg=itk.image_from_array(g.swapaxes(0,2).astype(np.float32).copy())
    gimg.CopyInformation(imgtarget)
    #logger.debug(f"Computed {nmask} gamma values assuming EQUAL geometry in target and reference")
    return gimg



############################################################################
############################################################################



def gamma_image( ref_dose, target_dose ):
    """ Gamma analysis of MC and TPS beam dose using GateTools
    
    Return accepts ITK-like image, or path to image
    Returns image matching dimensions of target
    Set ref -> MC dose, target -> Monte Carlo dose
    """    
    ref, targ = None, None 
    if type(ref_dose)==str:
        #Assume we have file path
        ref = itk.imread( ref_dose )
    else:
        #Assume we have image file
        ref = ref_dose
    if type(target_dose)==str:
        targ = itk.imread( target_dose )
    else:
        targ = target_dose    
             
    max_tps_dose = np.max( targ )
    ##print("    max tps dose = ", max_tps_dose)
    gamma_threshold = max_tps_dose * DOSE_THRESHOLD   ## TODO: SENSIBLE THRESHOLD??
    
    gamma = get_gamma_index( ref, targ, dta=DTA, dd=DD, ddpercent=True, threshold=gamma_threshold)   
    return gamma



def get_pass_rate( gamma_img ):
    """Return gamma pass rate
    """
    gamma_vals = itk.GetArrayViewFromImage(gamma_img)
    max_gam = float(np.max(gamma_vals))
    print( "  Max gamma = {}".format( round(max_gam,2)  ) )
    # Only look at valid gammas (i.e. > 0) for % fail count
    pass_rate = 100.0 - 100*gamma_vals[gamma_vals>1].size / gamma_vals[gamma_vals>0].size
    #print( "  Gamma < 1 = {}%".format( pass_rate )  )  
    
    return pass_rate



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









#TODO; THESE ARE ALREADY IN dosetodicom.py; combine

def rand_digits_str( digits_to_modify ):
    """
    Return a zero-padded random 4 digit string to modify the dicom UIDs
    """
    limit = 10**digits_to_modify - 1
    return str( int(random.random()*limit) ).zfill(digits_to_modify)


def mhd2dcm(mhdFile, dcmFile, output, dosescaling=None):
    """
    Takes mhd dose from Gate and the dicom dose file corresponding field,
    modifes appropriate dicom fields for import into Eclipse.
    
    Optional scaling of dose    
    """
    
    if dosescaling==None:
        #print("No dose scaling specified")
        dosescaling = 1
    
    dcm = pydicom.dcmread(dcmFile)
    mhd=None
    if type(mhdFile)==str:
        mhd = itk.imread(mhdFile)
    else:
        #Assume image
        mhd = mhdFile  ##TODO: TIDY THIS
    
    ###### Alter UID tags  -- TODO: what exactly needs changed?
    digits_to_modify = 4
    digits = rand_digits_str( digits_to_modify )
    
    sopinstanceuid = dcm.SOPInstanceUID 
    dcm.SOPInstanceUID = sopinstanceuid[:-digits_to_modify] + digits
    
    studyinstanceuid = dcm.StudyInstanceUID 
    dcm.StudyInstanceUID = studyinstanceuid[:-digits_to_modify] + digits
    
    seriesinstanceuid = dcm.SeriesInstanceUID 
    dcm.SeriesInstanceUID = seriesinstanceuid[:-digits_to_modify] + digits
    #####################################################
    
    dcm.PixelSpacing = list( mhd.GetSpacing() )[0:2]
    dcm.ImagePositionPatient =  list( mhd.GetOrigin() )
    d = mhd.GetDirection() * [1,1,1]
    dcm.ImageOrientationPatient = [ d[0],0,0, 0,d[1],0 ]

    mhdpix = itk.array_from_image(mhd)
       
    # REPLACE THE -1 DEFAULT GAMMA VALUES  TODO: more robust
    mhdpix[ mhdpix<0 ] = 0
      
    # mhd.GetLargestPossibleRegion().GetSize() gives [cols, rows, slices]
    # pixel_array.shape gives [slices, rows, cols]
    dcm.NumberOfFrames = mhdpix.shape[0]
    dcm.Rows = mhdpix.shape[1]            
    dcm.Columns = mhdpix.shape[2]
    
    dcm.GridFrameOffsetVector = [ x*mhd.GetSpacing()[2] for x in range(mhdpix.shape[0]) ]
         
    dose_abs = mhdpix * dosescaling
    
    scale_to_int = 1E4   
    mhd_scaled = dose_abs * scale_to_int
    mhd_scaled = mhd_scaled.astype(int)       
    dcm.PixelData = mhd_scaled.tobytes()
    
    dcm_scaling = 1.0/scale_to_int
    dcm.DoseGridScaling = dcm_scaling  
   
    dcm.save_as( output )
    
    
    
    
    
    
    
    
    
if __name__=="__main__":
    tps_dose = itk.imread("EclipseDose.mhd")
    mc_dose = itk.imread("Gatedose.mhd")
    
    # Low 1998 uses TPS dose as target and measured dose as ref
    #        -> Use TPS as target and monte carlo as ref
    gamma_img = gamma_image( mc_dose, tps_dose )  #(ref, targ)
    itk.imwrite(gamma_img, "gamma_img.mhd")
 
    pass_rate = get_pass_rate( gamma_img )
    print("  Gamma pass rate = {}%".format( round(pass_rate,2) ))

