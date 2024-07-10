# -*- coding: utf-8 -*-
"""
Created on Tue May 21 09:25:36 2024
@author: SCOURT01

Function that converts an ITK image with (short int) HU values
into an float32 image with density values.

Code modified from:
  https://github.com/OpenGATE/IDEAL/blob/main/ideal/utils/mass_image.py
 -----------------------------------------------------------------------------
  Copyright (C): MedAustron GmbH, ACMIT Gmbh and Medical University Vienna
   This software is distributed under the terms
   of the GNU Lesser General  Public Licence (LGPL)
   See LICENSE for further details
 -----------------------------------------------------------------------------
"""

import numpy as np
import itk
#import logging
#logger=logging.getLogger(__name__)


def get_dlut(humaterials_path):
    """
    Generate density-material lookup table from HUmaterials file.
    Output is list of lists [density_lower, tissue]
    """
    f = open(humaterials_path, "r")
    lines = f.readlines()
    dlut=[]
    for line in lines:
        if "d=" in line:
            tissue = line.split(":")[0].strip()
            density_lower = float(line.split("d=")[1].split()[0].strip())
            if "mg/cm3" in line:
                density_lower = density_lower / 1000
            dlut.append( [density_lower, tissue] )
    return dlut



def get_hlut(humaterials_path):
    """
    Generate numpy array of HU-density lookup table from HUmaterials file 
    used in gate simulation
    """
    f = open(humaterials_path, "r")
    lines = f.readlines()
    
    hlut=[]
    entry=[]
    for l in lines:
        if("d=" in l):
            dens = float( l.split("d=")[1].split()[0].strip() );
            if ("mg/cm3") in l:
                dens = dens / 1000
            entry.append(dens)
            hlut.append(entry)
            entry=[]
        if("H=[" in l):
            # GATE DOESNT FORCE THERSE TO BE INTEGERS??
            hu_low = float( l.split("H=[")[1].split(";")[0].strip() );  
            hu_high = float( l.split("H=[")[1].split(";")[1].split("]")[0].strip() );
            entry.append(hu_low)
            entry.append(hu_high)
    
    np_hlut = np.array( [np.array(xi) for xi in hlut] )        
    return np_hlut

        



def create_density_image(ct,hlut,overrides=dict()):
    """
    This function creates a density image based on the HU values in a ct image, a
    Hounsfield-to-density lookup table and (optionally) a dictionary of
    override densities for specific HU values.

    If the HU-to-density lookup table has 3 columns, then it is interpreted as
    a step-wise density table, with a constant density within each successive
    interval (no interpolation).
    """
    #HLUT = np.loadtxt(hlut_path)
    #logger.debug("table shape is {}".format(HLUT.shape))
    #logger.debug("table data type is {}".format(HLUT.dtype))
    #assert len(HLUT.shape)==2, "HU lookup table has wrong dimension (should be 2D)"
    #assert HLUT.shape[1]//2==1, "HU lookup table has wrong number of columns (should be 2 or 3)"
    
    act=itk.GetArrayFromImage(ct)
    adensity=np.zeros(act.shape,dtype=np.float32)
    done=np.zeros(act.shape,dtype=bool)

    n = hlut.shape[0]
    HUfrom = hlut[:,0]
    HUtill = hlut[:,1]
    rho = hlut[:,2]
    #assert (HUfrom<HUtill).all(),"inconsistent HU interval"
    #assert (rho>0).all(),"rho should be positive"
    
    if n>1:
        assert (HUfrom[1:]==HUtill[:-1]).all(),"HU intervals should be contiguous"
        
    d=(act>=HUfrom[0])   
    assert d.all(),"Some HU values in the CT are less than the minimum in the HU table."
    
    for hu0,hu1,rho0 in zip(HUfrom,HUtill,rho):
        d=(act>=hu0)*(act<hu1)
        assert not (d*done).any(), "programming error"
        adensity[d]=rho0
        done|=d
            
    for hu,rho in overrides.items():
        assert hu==int(hu), "overrides must be given for integer HU values"
        assert rho>=0, "override density values must be non-negative"
        d=(act==hu)
        adensity[d]=rho
        done|=d
        
    if not done.all():
        #logger.warn("not all voxels got a mass, some voxels are 0")
        pass
    
    density=itk.GetImageFromArray(adensity)
    density.CopyInformation(ct)
    return density

