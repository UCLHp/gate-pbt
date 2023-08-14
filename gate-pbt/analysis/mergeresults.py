# -*- coding: utf-8 -*-
"""
@author: Steven Court

Methods to merge cluster simulation results:
    - Summing doses
    - Combining LETd distributions
"""
from os import listdir
from os.path import isfile, join, basename
import math
import re

import easygui
import itk
import numpy as np



def sum_dose( filelist, imgoutput=None  ):
    """
    Sum mhd/raw absolute doses; generate image if output specified or
    return array of values otherwise
    """
    total = None
    
    if len(filelist)==0:
        print("No files given to sum_dose")
    elif len(filelist)==1:
        total = itk.array_from_image(itk.imread(filelist[0]))
    else:
        # Take first
        ff = filelist[0]
        total = itk.array_from_image(itk.imread(ff))
        # Loop through rest
        for n in range(1,len(filelist)):
            file = filelist[n]
            total += itk.array_from_image(itk.imread(file))
    
    if imgoutput==None:
        return total
    else:    
        sumimg = itk.image_from_array(total)
        # Take properties from any; TODO: should check they're all the same?
        sumimg.CopyInformation( itk.imread(filelist[0]) ) 
        itk.imwrite(sumimg, imgoutput)

    
    

def combine_uncertainty(dosefiles, dosesquaredfiles, statfiles, output):
    """
    Calculate dose uncertainty as in Chetty2006
    """

    #Gate uncertainty calculation uses NUMBER OF PRIMARIES in simulation, 
    #not the numberOfHits per voxel
    N = get_tot_primaries(statfiles)

    # Get shape and image info
    img1 = itk.imread(dosefiles[0])
    shape = itk.array_from_image( img1 ).shape
    nvoxels = shape[0]*shape[1]*shape[2]
    
    sumdose = None
    sumdosesq = None
    
    if len(dosefiles)!=len(dosesquaredfiles):
        print("Uncertainty not combined; unequal number of dose and dosesquared files") 
        exit(3)
    if len(dosefiles)==0:
        print("No files given to sum_uncertainty method")
        exit(3)
    else:
        sumdose = sum_dose( dosefiles )
        sumdosesq = sum_dose( dosesquaredfiles )

    sumdose = sumdose.flatten()
    sumdosesq = sumdosesq.flatten()
    uncertainty = np.ones( nvoxels )
    
    for i in range(len(uncertainty)):
        #Using Eq(2) from Chetty2006, "Reporting and analyzing statistical uncertainties in MC-based 
        #treatment planning" and dividing by dose/N for relative uncertainty...
        if sumdosesq[i]!=0 and sumdose[i]!=0 and N>1: 
            uncertainty[i] = math.sqrt( 1.0/(N-1) * (sumdosesq[i]/N - (sumdose[i]/N)**2) ) / (sumdose[i]/N)

    combinedUncert = uncertainty.reshape( shape )
    uncertimg = itk.image_from_array( combinedUncert.astype(np.float32)  ) ## ITK CANNOT WRITE DOUBLES, MUST CAST TO FLOAT
    uncertimg.CopyInformation( img1 )
    
    itk.imwrite( uncertimg, output )





def combine_let( dosefiles, letfiles, outname):
    """
    Combine LET distributions from multiple simulations in a
    dose-weighted fashion
    
    NOTE: The order of dosefiles and letfiles must match,
    i.e the index corresponds to a specific simulation! TODO: CHECK THIS
    """
    
    # Get shape and image info
    img1 = itk.imread(dosefiles[0])
    shape = itk.array_from_image( img1 ).shape
    nvoxels = shape[0]*shape[1]*shape[2]
    
    sumdose = sum_dose( dosefiles )
    sumdose = sumdose.flatten()
    
    if len(dosefiles)!=len(letfiles):
        print("Unequal number of dose and LET files") 
    if len(dosefiles)==0:
        print("No files given to combine_let method")
    else:  
        totlet = np.zeros( nvoxels )      
        # File lists must be in same order - TODO: CHECK
        for fdose,flet in zip(dosefiles, letfiles):
            dose = itk.array_from_image(itk.imread(fdose)).flatten()
            let = itk.array_from_image(itk.imread(flet)).flatten()               
            for i in range(len(totlet)):
                if sumdose[i]!=0:
                    totlet[i] += let[i]*(dose[i]/sumdose[i])

    combinedlet = totlet.reshape( shape )
    ## ITK cannot write doubles, must cast to float
    letimg = itk.image_from_array( combinedlet.astype(np.float32)  )   
    letimg.CopyInformation( img1 )
    
    itk.imwrite( letimg, outname )



    
#def z_combine_let( dosefiles, letfiles, outname):
#    """
#    Combine LET distributions from multiple simulations in a
#    dose-weighted fashion
#    
#    NOTE: The order of dosefiles and letfiles must match,
#    i.e the index corresponds to a specific simulation!
#    """
#    
#    #Store FLATTENED image arrays
#    dosearrays=[]
#    letarrays=[]
#    
#    # Get shape and image info
#    img1 = itk.imread(dosefiles[0])
#    shape = itk.array_from_image( img1 ).shape
#    
#    if len(dosefiles)!=len(letfiles):
#        print("Unequal number of dose and LET files") 
#    if len(dosefiles)==0:
#        print("No files given to combine_let method")
#    else:
#        for f in dosefiles:
#            dosearrays.append( itk.array_from_image(itk.imread(f)).flatten() )
#        for f in letfiles:
#            letarrays.append( itk.array_from_image(itk.imread(f)).flatten()  )
#    
#    sumdose = sum(dosearrays)
#      
#    #itk.imread(dosefiles[0])
#    totlet = np.zeros( len(letarrays[0]) )
#    for i in range(len(totlet)):
#        tot = 0
#        for j in range(len(dosearrays)):
#            if sumdose[i]!=0:            #TODO this ok for floats?
#                tot = tot + letarrays[j][i]*(dosearrays[j][i]/sumdose[i])
#        totlet[i] = tot    
#
#    
#    combinedlet = totlet.reshape( shape )
#    letimg = itk.image_from_array( combinedlet.astype(np.float32)  )   ## ITK CANNOT WRITE DOUBLES, MUST CAST TO FLOAT
#    letimg.CopyInformation( img1 )
#    
#    itk.imwrite( letimg, outname )
    



  
    
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
    
    allfilepaths = [join(directory,f) for f in listdir(directory) if isfile(join(directory,f))]
    
    if fieldname is None:
        fieldfiles = allfilepaths
        fieldname = ""
    else:
        fieldfiles =  [f for f in allfilepaths if fieldname in basename(f)]        

    # REPAINTING BUG: "G160_T0_RS0_1_" and "G160_T0_RS0_B_1_"; first was double counted; use regexp
    dosefiles = [f for f in fieldfiles if re.search(fieldname+"_\d+(_3d-pat-Dose\.mhd)",f) ]
    dosetowaterfiles = [f for f in fieldfiles if re.search(fieldname+"_\d+(_3d-pat-DoseToWater\.mhd)",f) ]
    letfiles = [f for f in fieldfiles if re.match(fieldname+"_\d+(_letActor-doseAveraged.mhd)",f)]
    dosesquaredfiles = [f for f in fieldfiles if re.search(fieldname+"_\d+(_3d-pat-Dose-Squared\.mhd)",f)]
    statfiles = [f for f in fieldfiles if re.search(fieldname+"_\d+(_stat-pat\.txt)",f) ]

    
    filesmade = []
    
    #Need to check files are as expected (size etc)
    if dosefiles:
        out = join(directory, fieldname+"_merged-Dose.mhd")
        filesmade.append(out)
        sum_dose(dosefiles, out)
    if dosetowaterfiles:
        out = join(directory, fieldname+"_merged-DoseToWater.mhd")
        filesmade.append(out)
        sum_dose(dosetowaterfiles, out)
    if dosefiles and letfiles:
        out = join(directory,fieldname+"_merged-LET.mhd")
        filesmade.append(out)
        combine_let( dosefiles, letfiles, out)
    if dosefiles and dosesquaredfiles:
        out = join(directory,fieldname+"_merged-Uncertainty.mhd")
        filesmade.append(out)
        combine_uncertainty(dosefiles, dosesquaredfiles, statfiles, out)

    #return list of files generated by method
    return filesmade
    
    
    
    
    
    
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




    