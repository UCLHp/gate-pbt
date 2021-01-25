# -*- coding: utf-8 -*-
"""
Created on Sun Jan 24 16:44:02 2021
@author: SCOURT01

Methods for interacting with simconfig.ini configuration file

"""
import os
import configparser



def get_req_prims( outputdir, field ):
    """Return required primaries for field"""
    ########## ASSUME CONFIG FILE IN /../data
    parent = os.path.dirname(outputdir)
    configfile = os.path.join(parent,"data","simconfig.ini")
    ########################################
    
    config = configparser.ConfigParser()
    config.read(configfile)
    primaries = config.getint(field, "required_primaries")
    return primaries


def get_ct_path( outputdir ):
    """Return required primaries for field"""
    ########## ASSUME CONFIG FILE IN /../data
    parent = os.path.dirname(outputdir)
    configfile = os.path.join(parent,"data","simconfig.ini")
    ########################################
    
    config = configparser.ConfigParser()
    config.read(configfile)
    ctname = config.get("Image", "ct_name")
    ctpath = os.path.join(parent,"data", ctname)
    return ctpath