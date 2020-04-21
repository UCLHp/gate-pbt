# -*- coding: utf-8 -*-
"""
Created on Tue Nov 19 10:35:57 2019

@author: SCOURT01

Script to generate the necessary Gate code to (i) define materials in the 
GateMaterials.db file and (ii) create blocks of these materials in a simulation
in order to extract stopping powers.
"""

import pandas as pd


def element_count(row, elements):
    """Get number of different elements in a tissue"""
    #tot=13
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



# WW tissue compositions
ww_data = pd.read_csv("Tissue_compositions_WW.csv")
# Output file GateMaterials.db
out = open("WW_tissues_GateMaterials.txt","w")
# Output file for simulation .mac file
out_box = open("WW_tissues_GateBoxes.txt","w")

# All elements present in WW data
elements=["Hydrogen","Carbon","Nitrogen","Oxygen","Sodium","Magnesium",
          "Phosphor","Sulfur","Chlorine","Potassium","Calcium","Iron","Iodine"]

for i,row in ww_data.iterrows():
    gate_box_txt( row["Tissue"], i, out_box  )
    n = element_count(row,elements)
    out.write( "{}: d={} g/cm3 ; n={}\n".format(row["Tissue"].strip(),row["density"],n)  )
    for e in elements:
        if float(row[e])>0.0001:
            out.write( "        +el: name={}; f={}\n".format(e, round(row[e]/100,3) ) )
    out.write("\n")        
    
out.close()
out_box.close()
