# -*- coding: utf-8 -*-
"""
Created on Wed Feb 10 15:10:48 2021
@author: SCOURT01

Methods for investigating runtimes / primaries per second (PPS)
of simulations across cluster
"""
from os import listdir
from os.path import join
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

import easygui


def choose_directory():
    """Choose directory containing acquisition files
    """
    msg = "Select data directory"
    title = "Select data directory"
    if easygui.ccbox(msg, title):
        pass
    else:
        exit(0)
    return easygui.diropenbox()


def get_pps( file ):
    """Return PPS from each sim"""
    with open(file, "r") as stat:
        lines = stat.readlines()
        for l in lines:
            if "PPS" in l:
                pps = float(l.split("=")[1].strip())
    return pps     


def get_runtime( file ):
    """Return runtime from stat.txt output"""
    with open(file, "r") as stat:
        lines = stat.readlines()
        for l in lines:
            if "StartDate" in l:
                starttime = datetime.strptime(l.split()[6],"%H:%M:%S")
                #print( type(starttime) )
            elif "EndDate" in l:
                endtime = datetime.strptime(l.split()[6],"%H:%M:%S")
                #print(endtime)
            
        runtime = (endtime - starttime).total_seconds()
        return runtime
    
    

if __name__=="__main__":
    
    
    #outputdir = r"C:\Users\SCOURT01.UCLH\Desktop\Uncertainty moedlling\zzzHFP_test1--Plan1\output"
    outputdir = choose_directory()
    
    times = []
    pps = []
    
    allfiles = listdir(outputdir)
    statfilesonly = [f for f in allfiles if "stat" in f]
    #filelist = sorted(allfiles, key=lambda x: int(x.split("_")[1]) )
    statfiles = sorted(statfilesonly, key=lambda x: int(x.split("_")[1]) )

 
    for file in statfiles:
        path = join(outputdir,file)
        runtime = get_runtime( path )
        times.append(runtime)
        pps.append( get_pps(path) )
    
    
    times = np.array(times) 
    pps = np.array(pps)
    
    totaltimehours = sum(times) / (60*60)
    
    
    print("sim times = ", times)
    print()
    print("Max = ", times.max() )
    print("Min = ", times.min() )
    print("Mean = ", times.mean() )
    print("Total sim time = {} hrs".format(totaltimehours))
    
    print()
    print("PPS = ", pps)
    print("PPS MAX = ", pps.max())
    print("PPS MIN = ", pps.min())
    print("PPS MEAN = ", pps.mean())
    print("PPS STDEV = ", pps.std() )
    
    
    #for f,p in zip(statfiles,pps):
    #    print( f,p )
        
        
    plt.plot(pps)
    plt.xlabel("Simulation")
    plt.ylabel("PPS")
    plt.show()
    
    
    #print()
    #r = times*pps
    #print( r / r.max() )
    
    
    
    
        
