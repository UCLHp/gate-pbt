# -*- coding: utf-8 -*-
"""
@author: Steven Court

Methods to merge cluster simulation results:
    - Summing doses
    - Combining LETd distributions
"""
from os import listdir
from os.path import isfile, join
import math

import easygui



def sum_vals( filelist, imgoutput=None  ):
    """
    Sum values from txt file outputs
    """
    total = 0    
    if len(filelist)==0:
        print("No files given to sum_dose")
    else:
        for n in range(0,len(filelist)):
            file = filelist[n]
            with open(file,"r") as f:
                lines = f.readlines()
                total += float(lines[-1])
    return total



def combine_uncertainty(edep, edep_sq, nsim):
    """
    Calculate dose uncertainty as in Chetty2006
    """
    uncert = 0
    if edep_sq!=0 and edep!=0 and nsim>1: 
            uncert = math.sqrt( 1.0/(nsim-1) * (edep_sq/nsim - (edep/nsim)**2) ) / (edep/nsim)
    return uncert

    

def get_tot_primaries(statfiles):
    """
    Get total number of primaries from Gate's stat files
    """
    N=0
    for f in statfiles:
        lines = open(f).readlines()
        for line in lines:
            if "NumberOfEvents" in line:
                n = int(line.split("=")[1].strip())
                N = N+n
                break
    return N



def merge_results( directory, fieldname=None ):
    """Take contents on directory and merge all dose, uncertainty
    and LET results if possible
    
    Data integrity should be checked before calling this method
    """
    
    allfiles = [join(directory,f) for f in listdir(directory) if isfile(join(directory,f))]
    
    if fieldname is None:
        fieldfiles = allfiles
        fieldname = ""
    else:
        fieldfiles =  [f for f in allfiles if fieldname in f]     

    #dosefiles = [f for f in fieldfiles if "-Dose.mhd" in f ]
    #dosesquaredfiles = [f for f in fieldfiles if "-Dose-Squared.mhd" in f]
    edepfiles = [f for f in fieldfiles if "-Edep.txt" in f ]
    edepsquaredfiles = [f for f in fieldfiles if "-Edep-Squared.txt" in f ]
    statfiles = [f for f in fieldfiles if "stat.txt" in f ]
    
    edep, edep_sq, nsim = 0,0,0 
    
    if statfiles:
        nsim = get_tot_primaries(statfiles)    
    if edepfiles:
        edep = sum_vals(edepfiles)
    if edepsquaredfiles:
        edep_sq = sum_vals(edepsquaredfiles)
        
    uncertainty = combine_uncertainty(edep, edep_sq, nsim)
        
    return edep, edep_sq, nsim, uncertainty
    
    
    
    
    
    
###################################################
###################################################
  
def main():
    ###directory=r"M:\vGATE-GEANT4\ClusterSimulationTesting\Plan1_Field1_5x5E6_hits"
    # Select directory containing simulation output
    msg = "Directory should contain dose, dosesquared\n let and stat files from cluster"
    title = "Select directory containing results to merge"
    
    if easygui.ccbox(msg, title):
        pass
    else:
        exit(0)
    directory = easygui.diropenbox()
  
    merge_results(directory)



if __name__=="__main__":
    main()




    