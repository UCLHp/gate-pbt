# -*- coding: utf-8 -*-
"""
@author: Steven Court
Automated analysis of Gate simulation output:
  - Check of data integrity
  - Merging all results
  - Any post-sim corrections (i.e. Offset field in mhd file)
  - Scaling for absolute dose
  - Conversion of dose-to-material to dose-to-water
  - Conversion from mhd/raw to dicom for import into TPS
"""

import sys
import os

import math
import easygui

import ddncf_mergeresults


def count_prims_simulated( outputdir ):
    """Count primaries actually simulated from stat files"""
    filelist = os.listdir(outputdir)
    tot = 0
    for f in filelist:
        if "stat.txt" in f:
            lines = open(f).readlines()
            for line in lines:
                if "NumberOfEvents" in line:
                    prims = int(line.split("=")[1].strip())
                    tot += prims
    if tot<=0:
        print("  ERROR; no simulated primaries in ", outputdir)
        exit(3)
    return tot
                    


def full_analysis( required_primaries ):
    """Automated analysis of all Gate output in specified directory
    """ 
    edep, edep_sq, nsim, uncertainty = ddncf_mergeresults.merge_results( outputdir )
    
    #print("edep",edep)

    scalefactor = (required_primaries / nsim) 
    print("Primaries simulated: ",nsim)
    print("Primaries required: ",required_primaries)
    
    # convert Edep to dose to Roos volume (0.5mm thick, 7.5mm radius)
    # edep is MeV
    mev_to_joule = 1.60218E-13
    roos_mass_kg = 0.05*math.pi*0.75**2 / 1000

    dose = edep / roos_mass_kg * mev_to_joule
    
    dose = dose * scalefactor * 1.1
    
    print("\nDose_RBE (Gy) = ", dose)
    print("Uncertainty (%)", uncertainty*100 )
        
            
    
        
if __name__=="__main__":
    
    # Select directory containing Gate output
    msg = "Select directory containing Gate output files"
    title = "SELECT DIRECTORY"
    if easygui.ccbox(msg, title):
        pass
    else:
        sys.exit(0)   
    outputdir = easygui.diropenbox()
    
   
    
    ##############################################################
    # Beam v2; NMU_@2cm    :  N/MU_area_under_curve
    #required_prims =38733283027	#10x02: 38262579951
    #required_prims =105990413789	#10x05: 104751538359

    #required_prims =28535000679	#15x02: 28243100550
    #required_prims =102274718827	#15x05: 101194378132
    #required_prims =319700428536	#15x10: 316283857101

    #required_prims =40052885422	#20x02: 39689655648
    #required_prims =108634872034	#20x05: 107636359938
    #required_prims =337348683363	#20x10: 334144421264
    #required_prims =763595731118	#20x15: 756232411092

    #required_prims =57254920447	#25x02: 56729961354
    #required_prims =163774824159	#25x05: 162280488855
    #required_prims =398762042515	#25x10: 395107459498
    #required_prims =748358187904	#25x15: 741399803286
    #required_prims =1340083756974	#25x20: 1327504996588

    #required_prims =113500748594	#30x05: 112394342852
    #required_prims =425468234723	#30x10: 421402061540
    #required_prims =781027590965	#30x15: 773572674250
    #required_prims =1408962507167	#30x20: 1395437299541

    #required_prims =1050819063718	#35x15: 1040622099595
    #required_prims =1859304870602	#35x20: 1841282321198   
    ################################################################
    
    #### These are from beam model v2, N/MU normalized to area under curve
    #required_prims =  38262579951    #10x02      
    #required_prims = 104751538359   #10x05      
    
    #required_prims =  28243100550   #15x02       
    #required_prims = 101194378132   #15x05  
    #required_prims = 316283857101   #15x10  
    
    #required_prims =  39689655648   #20x02 
    #required_prims = 107636359938   #20x05 
    #required_prims = 334144421264   #20x10
    #required_prims = 756232411092   #20x15 
    
    #required_prims = 56729961354    #25x02
    #required_prims = 162280488855   #25x05  
    #required_prims = 395107459498   #25x10
    #required_prims = 741399803286   #25x15
    #required_prims = 1327504996588  #25x20
    
    #required_prims = 112394342852   #30x05
    #required_prims = 421402061540   #30x10  
    #required_prims = 773572674250   #30x15
    #required_prims = 1395437299541  #30x20

    #required_prims = 1040622099595   #35x15
    required_prims =  1841282321198  #35x20    
    
    
      
    full_analysis( required_prims )
    
    
    
    