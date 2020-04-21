# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 10:25:04 2020
@author: SCOURT01

Methods to split the Gate simulations up
for running on the cluster.
"""



def split_by_primaries( macfile, N ):
    """
    Splits a mac file into N separate simulations
    with equal number of primaries
    """    
    maclines = open(macfile).readlines()

    totprims = 0    
    for l in maclines:
        if "TotalNumberOfPrimaries" in l and "#" not in l:
            totprims = int( l.split()[1] )
    
    for i in range(1,N+1):
        filename = macfile.replace( ".mac", "_"+str(i)+".mac")
        with open(filename, 'w') as out:
            for l in maclines:
                if "output" in l:
                    out.write( l.replace("output/", "output/"+str(i)+"_") )
                elif "TotalNumberOfPrimaries" in l:
                    prims = str( int(totprims/N) )
                    out.write("/gate/application/setTotalNumberOfPrimaries {}\n".format(prims))
                else:
                    out.write(l)
        out.close()




def split_by_energies( macfile, plandescfile ):
    """
    Split in some sensible way accounting for fact that higher energy layers
    will be deeper and have more primaries and so will be slower to simulate.
    
    * This method will need to create new PlanDescriptionFiles too *
    """
    pass






#split_by_primaries( "TESTFILE.mac", 5 )