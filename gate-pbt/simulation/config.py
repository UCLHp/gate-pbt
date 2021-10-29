# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods for creating / modifying simulation config file
"""

import configparser



def update_config( configfile, section, key, value ):
    """Update simconfig.ini section and key with value
    
    Value must be written/read as string
    """
    config = configparser.ConfigParser()
    config.read(configfile)
    if config.has_section(section):
        config[section][key] = value
    else:
        config[section]  =  {key: value } 
    with open(configfile, "w") as q:
        config.write( q )
        
        
def add_patient_position( configfile, patpos ):
    """Update simconfig.ini with patient position 
    """
    config = configparser.ConfigParser()
    config.read(configfile)
    if config.has_section("Image"):
        config["Image"]["patient_position"] = patpos
    else:
        config["Image"]  =  {"patient_position": patpos } 
    with open(configfile, "w") as q:
        config.write( q )


def add_fractions( configfile, nfractions ):
    """Update simconfig.ini with number fractions 
    """
    config = configparser.ConfigParser()
    config.read(configfile)
    if config.has_section("Plan"):
        config["Plan"]["fractions"] = nfractions
    else:
        config["Plan"]  =  {"fractions": nfractions } 
    with open(configfile, "w") as q:
        config.write( q )


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
        
        
def add_correct_dose_offset( configfile, beamname, dose_origin):
    """Add correct dose output mhd Offset (from numpy array)
    
    OBSOLETE; just left for checking.
    Now that we reorientate all images so as to have TransformMatrix=100010001
    we no longer have to correct Gate's incorrect Offset calculation
    """
    offset = ""
    for c in dose_origin:
        offset += str(c) + " " 
    offset = offset.strip()
    
    config = configparser.ConfigParser()
    config.read(configfile)
    if config.has_section(beamname):
        config[beamname]["dose_offset"] = offset
    else:
        config[beamname] = {"dose_offset": offset } 
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


def add_beam_ref_no( configfile, field, beamno ):
    """Update simconfig.ini with beam ref number
    """
    config = configparser.ConfigParser()
    config.read(configfile)
    
    name = field.replace(" ","")
    if config.has_section(name):
        config[name]["beam_ref_no"] = str(beamno)
    else:
        config[name]  =  {"beam_ref_no": str(beamno) }    
        
    with open(configfile, "w") as q:
        config.write( q )


