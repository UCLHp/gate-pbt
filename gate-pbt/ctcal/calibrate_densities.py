# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 12:40:48 2019
@author: Steven Court

Script to read in HU-RSP data from CT calibration along with 
stopping powers calculated in Gate. Calculate the density of 
each material in Gate so as to force RSP match with CT data
"""

import pandas as pd

#############################################################
# Stopping power data from Gate's EMCalculatorActor
EM_CALC = "example_emcalc.txt"

# HU-RSP relations from CT calibration curve
RSP_FROM_CT = "example_ct_data.csv"
#############################################################



def read_RSPs( emCalc_filename, sp_water ):
    f = open( emCalc_filename )
    """Reads in the Sw/Si ratio from an EmCalculatorActor file
    returns a dictionary"""
    lines = f.readlines()
    swsi = {}
    #Ignore file header info --
    data = lines[7:]
    for l in data:
        cols = l.strip().split()
        #print(cols)
        swsi[cols[0]] = sp_water/float(cols[7])
    f.close()
    return swsi    



def get_sp_water( emCalc_filename )   :
    """Get stopping power of water"""
    f = open( emCalc_filename )
    lines = f.readlines()
    #Ignore file header info --
    data = lines[7:]
    sp_water = -999
    for l in data:
        cols = l.strip().split()
        #print(cols)
        if cols[0].lower()=="water":
            sp_water = float(cols[7])
    f.close()
    if sp_water==999:
        print("ERROR - NO WATER ENTRY IN DATA")
    #print(sp_water)
    return sp_water
    

def read_calibration_HUs( fname ):
    """Read in CT calibration data
    Dictionary of wwTissue and HU values"""
    calib_hus = {}
    f = open( fname )
    lines = f.readlines()[1:]
    for l in lines:
        cols = l.split(",")
        calib_hus[ cols[0].strip("'") ] = float(cols[1])
    return calib_hus

def read_calibration_RSPs( fname ):
    """Read in CT calibration data
    Dictionary of wwTissue and RSP"""
    calib_rsp = {}
    f = open( fname )
    lines = f.readlines()[1:]
    for l in lines:
        cols = l.split(",")
        calib_rsp[ cols[0].strip("'") ] = float(cols[2])    
    return calib_rsp

def read_calibration_densities( fname ):
    """Read in CT calibration data
    Dictionary of wwTissue and density values"""
    calib_hus = {}
    f = open( fname )
    lines = f.readlines()[1:]
    for l in lines:
        cols = l.split(",")
        calib_hus[ cols[0].strip("'") ] = float(cols[3])
    return calib_hus


##############################

def main():
        
    # Stopping power data from Gate's EMCalculatorActor
    emCalc_file = EM_CALC
    # HU-RSP relations from CT calibration curve
    rsp_calib_data = RSP_FROM_CT
    
    output = "calibrated_densities.csv"
    
    #Get stopping power of water
    sp_water = get_sp_water( emCalc_file )    
    #Get Sw/Si ratio needed for density calculation
    swsi = read_RSPs( emCalc_file, sp_water )
    
    #Get CT calibration RSP values
    rsps = read_calibration_RSPs( rsp_calib_data )
    #Get calibration HU values
    hus = read_calibration_HUs( rsp_calib_data )
    #Get physical densities
    densities = read_calibration_densities( rsp_calib_data )
    
    
    #Calculated corrected densities
    ## rho_i = Pi rho_w Sw/Si
    cal_dens = {}
    for tissue in swsi:
        if tissue in rsps:
            cal_dens[tissue] = rsps[tissue]*1.0*swsi[tissue]
            cal_dens[tissue] = rsps[tissue]*1.0*swsi[tissue]

            
    # Print all calibrated data
    out = open(output,"w")
    out.write("Tissue,HU,RSP,Original density,Calibrated density,Density diff (%)\n")
    for t in densities:
        out.write( "{},{},{},{},{},{}\n".format(t, hus[t], rsps[t],
                densities[t], cal_dens[t],
                100*(cal_dens[t]-densities[t])/densities[t] )
        )
    out.close()
    
    
    
    
if __name__=="__main__":
    main()
            