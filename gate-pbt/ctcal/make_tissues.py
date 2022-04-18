# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 10:35:57 2019
@author: Steven Court

Script to generate the necessary Gate code to:
    (i) define materials in the GateMaterials.db file 
    (ii) create blocks of these materials in a simulation
in order to extract stopping powers.
"""

import pandas as pd
import numpy as np


#########################################################################
# All elements as labelled in WW tissue data file
ELEMENTS=["Hydrogen","Carbon","Nitrogen","Oxygen","Sodium","Magnesium",
          "Phosphor","Sulfur","Chlorine","Potassium","Calcium","Iron","Iodine"]
#ELEMENTS=["h","c","n","o","f","na","mg","si","p","s","cl","k","ca","fe","i"]
#  (KC additionally has Si and F?)
    
# Data file
#WW_TISSUE_DATA = "example_WW_tissues_compositions.csv"
#WW_TISSUE_DATA = "tissue_compositions_KC20211101.csv"
WW_TISSUE_DATA = "tissue_compositions_WW.csv"
#########################################################################



def element_count(row, elements):
    """Get number of different elements present in tissue"""
    tot=len(elements)
    for e in elements:
        if row[e]<0.00001:
            tot=tot-1
    return tot


def gate_box_txt(tissue, i, f):
    """Gate code needed to generate a 1cm box of a tissue"""
    name = "{}_box".format( tissue.lower().strip() )
    f.write("/gate/world/daughters/name    {}\n".format(name )  )
    f.write("/gate/world/daughters/insert    box\n")
    f.write("/gate/{}/geometry/setXLength    1 cm\n".format(name))
    f.write("/gate/{}/geometry/setYLength    1 cm\n".format(name))
    f.write("/gate/{}/geometry/setYLength    1 cm\n".format(name))
    f.write("/gate/{}/placement/setTranslation {} 0 0 cm\n".format(name, -50+i)  )
    f.write("/gate/{}/setMaterial    {}\n\n".format(name, tissue.strip() )  )



def main():    
    # Read WW tissue compositions and densities
    ww_data = pd.read_csv(WW_TISSUE_DATA)
    
    # Output file GateMaterials.db
    out = open("WW_tissues_GateMaterials.txt","w")
    # Output file for simulation .mac file
    out_box = open("WW_tissues_GateBoxes.txt","w")
    
    
    for i,row in ww_data.iterrows():
        gate_box_txt( row["Tissue"], i, out_box  )
        n = element_count(row,ELEMENTS)
        out.write( "{}: d={} g/cm3 ; n={}\n".format(row["Tissue"].strip(),row["Density"],n)  )
        sum_fraction = 0
        for e in ELEMENTS:
            if float(row[e])>0.0001:
                frac = row[e]/100
                sum_fraction += frac
                out.write( "        +el: name={}; f={}\n".format(e, round(frac,3) ) )
        out.write("\n")  
        
        # Check elemental fractions sum to 1
        if not np.isclose( sum_fraction, 1):
            print("ERROR: elemental composiiton for {} doesn't sum to \
                  unity but to {}".format(row["Tissue"],sum_fraction) )
        
    out.close()
    out_box.close()
    
    
    
if __name__=="__main__":
    main()
