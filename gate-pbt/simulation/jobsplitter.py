# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods to split the Gate simulations up for running on cluster.
"""

import os

def split_by_primaries( macfilepath, primaries=None, splits=1 ):
    """
    Splits setTotalNumberOfPrimaries property in macfile
    If primaries not specified, value in template mac file will be taken
    """    
    
    #Take fieldname from macfile and add to output files
    macfilename = os.path.basename( macfilepath )
    fieldname, ext = os.path.splitext( macfilename )

    maclines = open(macfilepath).readlines()

    totprims = 0
    if primaries is None:
        for l in maclines:
            if "TotalNumberOfPrimaries" in l and "#" not in l:
                totprims = int( l.split()[1] )
    else:
        totprims = primaries
        
    if splits >= 1:
        #filename = macfilepath.replace( ".mac", "_"+str(i)+".mac")
        with open( macfilepath, 'w') as out:
            for l in maclines:
                if "output" in l:
                   out.write( l.replace("output/", "output/"+str(fieldname)+"_") )
                elif "TotalNumberOfPrimaries" in l:
                    prims = str( int(totprims/splits) )
                    out.write("/gate/application/setTotalNumberOfPrimaries {}\n".format(prims))
                else:
                    out.write(l)
        out.close()
    else:
        print("Number of split jobs is <= 0; invalid")
        exit()




def split_by_energies( macfile, plandescfile ):
    """
    Split in some sensible way accounting for fact that higher energy layers
    will be deeper and have more primaries and so will be slower to simulate.
    
    * This method will need to create new PlanDescriptionFiles too *
    """
    pass

