# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 12:40:48 2019

@author: SCOURT01
"""


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
    print(sp_water)
    return sp_water
    

def read_calibration_RSPs( fname ):
    """Read in CT calibration data
    Dictionary of wwTissue and RSP"""
    calib_rsp = {}
    f = open( fname )
    lines = f.readlines()[1:]
    for l in lines:
        cols = l.split(",")
        calib_rsp[ cols[0].strip("'") ] = float(cols[3])    
    return calib_rsp


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



##############################
##############################


emCalc_file = "WW_tissue_EmCalculatorActor_I=78.txt"
rsp_calib_data = "wwTissue_RSPs.csv"

output = "calibrated_WW_data.csv"

#Get stopping power of water
sp_water = get_sp_water( emCalc_file )    
#Get Sw/Si ratio needed for density calculation
swsi = read_RSPs( emCalc_file, sp_water )
#Get CT calibration RSP values
rsps = read_calibration_RSPs( rsp_calib_data )
#Get calibration HU values
hus = read_calibration_HUs( rsp_calib_data )


#Calculated corrected densities
## rho_i = Pi rho_w Sw/Si
densities = {}
for tissue in swsi:
    if tissue in rsps:
        densities[tissue] = rsps[tissue]*1.0*swsi[tissue]

#print(rsps)
#print(hus) 
#print(densities)
        
# Print all calibrated data
out = open(output,"w")
out.write("Tissue,HU,Calibrated density\n")
for t in densities:
    out.write( "{},{},{}\n".format(t,hus[t],densities[t])   )
out.close()
        