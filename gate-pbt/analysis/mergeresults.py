# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 08:56:32 2020
@author: SCOURT01

Methods to merge cluster simulation results:
    - Summing doses
    - Combining LETd distributions
"""

from os import listdir
from os.path import isfile, join
import math

import easygui
import itk
import numpy as np



def sum_dose( filelist, outname  ):
    """
    Sum mhd/raw absolute doses and generate image
    """
    
    # BE CAREFUL USING THIS IF YOU ARE SUMMING BEAMS (THEY SHOULD BE WEIGHTED 
    # APPROPRIATELY) OR IF SIMULATIONS HAD DIFFERENT NUMBERS OF PRIMARIES
    
    dosearrays=[]
    if len(filelist)==0:
        print("No files given to sum_dose")
    else:
        for f in filelist:
            imgarr = itk.array_from_image(itk.imread(f))
            dosearrays.append( imgarr )

    sumdose = sum(dosearrays)
    
    sumimg = itk.image_from_array(sumdose)
    sumimg.CopyInformation( itk.imread(filelist[0]) ) #CHECK ALL ARE SAME?
    itk.imwrite(sumimg, outname)

  
    
    
def combine_let( dosefiles, letfiles, outname):
    """
    Combine LET distributions from multiple simulations in a
    dose-weighted fashion
    
    NOTE: The order of dosefiles and letfiles must match,
    i.e the index corresponds to a specific simulation!
    """
    #Store FLATTENED image arrays
    dosearrays=[]
    letarrays=[]
    
    # Get shape and image info
    img1 = itk.imread(dosefiles[0])
    shape = itk.array_from_image( img1 ).shape
    
    if len(dosefiles)!=len(letfiles):
        print("Unequal number of dose and LET files") 
    if len(dosefiles)==0:
        print("No files given to combine_let method")
    else:
        for f in dosefiles:
            dosearrays.append( itk.array_from_image(itk.imread(f)).flatten() )
        for f in letfiles:
            letarrays.append( itk.array_from_image(itk.imread(f)).flatten()  )
    
    sumdose = sum(dosearrays)
      
    #itk.imread(dosefiles[0])
    totlet = np.zeros( len(letarrays[0]) )
    for i in range(len(totlet)):
        tot = 0
        for j in range(len(dosearrays)):
            if sumdose[i]!=0:            #TODO this ok for floats?
                tot = tot + letarrays[j][i]*(dosearrays[j][i]/sumdose[i])
        totlet[i] = tot    

    
    combinedlet = totlet.reshape( shape )
    letimg = itk.image_from_array( combinedlet.astype(np.float32)  )   ## ITK CANNOT WRITE DOUBLES, MUST CAST TO FLOAT
    letimg.CopyInformation( img1 )
    
    itk.imwrite( letimg, outname )
    




def combine_uncertainty(dosefiles, dosesquaredfiles, statfiles, output):
    """
    How to combine dose uncertainties from simulations?
    """
    dosearrays=[]
    dosesq=[]
    
    #Gate uncertainty calculation uses NUMBER OF PRIMARIES in simulation, 
    #not the numberOfHits per voxel
    N = get_tot_primaries(statfiles)

    # Get shape and image info
    img1 = itk.imread(dosefiles[0])
    shape = itk.array_from_image( img1 ).shape

    if len(dosefiles)!=len(dosesquaredfiles):
        print("Unequal number of dose and dosesquared files") 
    if len(dosefiles)==0:
        print("No files given to sum_uncertainty method")
    else:
        for f in dosefiles:
            dosearrays.append( itk.array_from_image(itk.imread(f)).flatten() )
        for f in dosesquaredfiles:
            dosesq.append( itk.array_from_image(itk.imread(f)).flatten()  )
    
    sumdose = sum(dosearrays)
    sumdosesq = sum(dosesq)  
    
    uncertainty = np.ones( len(dosearrays[0]) )
    for i in range(len(uncertainty)):
        #Using Eq(2) from Chetty2006, "Reporting and analyzing statistical uncertainties in MC-based 
        #treatment planning" and dividing by dose/N for relative uncertainty...
        if sumdosesq[i]!=0 and sumdose[i]!=0 and N>1: 
            uncertainty[i] = math.sqrt( 1.0/(N-1) * (sumdosesq[i]/N - (sumdose[i]/N)**2) ) / (sumdose[i]/N)

    combinedUncert = uncertainty.reshape( shape )
    uncertimg = itk.image_from_array( combinedUncert.astype(np.float32)  ) ## ITK CANNOT WRITE DOUBLES, MUST CAST TO FLOAT
    uncertimg.CopyInformation( img1 )
    
    itk.imwrite( uncertimg, output )


  
    
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


 

def merge_results( directory ):
    """Take contents on directory and merge all dose, uncertainty
    and LET results if possible
    """
    
    allfiles = [join(directory,f) for f in listdir(directory) if isfile(join(directory,f))]

    dosefiles = [f for f in allfiles if "pat-Dose.mhd" in f ]
    letfiles = [f for f in allfiles if "-doseAveraged.mhd" in f]
    dosesquaredfiles = [f for f in allfiles if "-Dose-Squared.mhd" in f]
    statfiles = [f for f in allfiles if "stat-pat.txt" in f ]
    
    #Need to check files are as expected (size etc)
    
    sum_dose(dosefiles, join(directory,"merged-Dose.mhd"))
    combine_let( dosefiles, letfiles, join(directory,"merged-LET.mhd"))
    combine_uncertainty(dosefiles, dosesquaredfiles, statfiles, join(directory,"merged-Uncertainty.mhd"))

    
    
    
    
    
    
    
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
        sys.exit(0)
    directory = easygui.diropenbox()
  
    merge_results(directory)



if __name__=="__main__":
    main()




    