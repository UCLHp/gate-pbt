# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 11:32:50 2021
@author: SCOURT01

Methods for creating / modifying simulation config file
"""

import configparser


def add_ct_to_config( configfile, ct_name ):
    """Update simconfig.ini with name of ct used in simulation
    """
    config = configparser.ConfigParser()
    config.read(configfile)
    if config.has_section("Image"):
        config["Image"]["ct_name"] = ct_name
    else:
        config["Image"]  =  {"ct_name": ct_name } 
    with open(configfile, "w") as q:
        config.write( q )
        
        

def add_transformmatrix_to_config( configfile, ctmhd ):
    """Store original TransformMatrix of ct image"""
    
    transform = ""
    lines = open(ctmhd, "r").readlines()
    for line in lines:
        if "TransformMatrix" in line:
            transform = line.split("=")[1].strip()    
    
    config = configparser.ConfigParser()
    config.read(configfile)
    if config.has_section("Image"):
        config["Image"]["transform_matrix"] = transform
    else:
        config["Image"]  =  {"transform_matrix": transform } 
    with open(configfile, "w") as q:
        config.write( q )    
        
        
        
def add_prims_to_config( configfile, req_prims ):
    """Update simconfig.ini with required primaries for each field
    strip spaces from field names to match Gate output
    """
    config = configparser.ConfigParser()
    config.read(configfile)
    
    for field in req_prims:
        name = field.replace(" ","")
        prims = round(req_prims[field])
        if config.has_section(name):
            config[name]["required_primaries"] = prims
        else:
            config[name]  =  {"required_primaries": prims }    
        
    with open(configfile, "w") as q:
        config.write( q )



