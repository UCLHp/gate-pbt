# -*- coding: utf-8 -*-
"""
Created on Sun Jan 24 16:44:02 2021
@author: SCOURT01

Methods for interacting with simconfig.ini configuration file

"""
import os
import configparser



def get_fractions( outputdir ):
    """Return required primaries for field"""
    ########## ASSUME CONFIG FILE IN /../data
    parent = os.path.dirname(outputdir)
    configfile = os.path.join(parent,"data","simconfig.ini")
    ########################################
    
    config = configparser.ConfigParser()
    config.read(configfile)
    fractions = config.getint("Plan", "fractions")
    return fractions


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


def get_beam_ref_no( outputdir, field ):
    """Return beam reference number (used in dcm)"""
    ########## ASSUME CONFIG FILE IN /../data
    parent = os.path.dirname(outputdir)
    configfile = os.path.join(parent,"data","simconfig.ini")
    ########################################
    
    config = configparser.ConfigParser()
    config.read(configfile)
    beamref = config.getint(field, "beam_ref_no")
    return beamref


def get_ct_path( outputdir ):
    """Return path to ct image used in simulation"""
    ########## ASSUME CONFIG FILE IN /../data
    parent = os.path.dirname(outputdir)
    configfile = os.path.join(parent,"data","simconfig.ini")
    ########################################
    
    config = configparser.ConfigParser()
    config.read(configfile)
    ctname = config.get("Image", "ct_name")
    ctpath = os.path.join(parent,"data", ctname)
    return ctpath


def get_transform_matrix( outputdir ):
    """Return transofrm matrix of original ct"""
    ########## ASSUME CONFIG FILE IN /../data
    parent = os.path.dirname(outputdir)
    configfile = os.path.join(parent,"data","simconfig.ini")
    ########################################
    
    config = configparser.ConfigParser()
    config.read(configfile)
    transform = config.get("Image", "transform_matrix")
    return transform