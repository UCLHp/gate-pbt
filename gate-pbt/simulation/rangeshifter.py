# -*- coding: utf-8 -*-
"""
Created on Thu May  7 16:25:22 2020

Methods related to positioning of rangeshifter

@author: SCOURT01
"""

from math import sin, cos, degrees, radians

######### TODO
#
# 1. Keep 0mm thickness RS in for all plans? Need to move it out of beam?
# 2. Map WET from dicom to physical thickness
# 3. Need exact RS dimensions
# 4. Need RS material composition
# 5. Need  offset RS offset from nozzle exit
# 6.  field.RangeShifterSettingsSequence[0].RangeShifterWaterEquivalentThickness or field.RangeShifterSequence??
#        field.NumberOfRangeShifters
#############



NOZZLE_OFFSET = 18.0  # mm


class Rangeshifter:
    
    def __init__(self, rotation=0, translation=None, thickness=0 ):
        self.rotation = rotation
        self.thickness = thickness 
        if translation is None: 
            translation = [0,0,0]
        self.translation = translation



def get_translation( field, thick, gantryangle ):
    
    #Distance (mm) from isocentre to downstream side of snout
    snout = field.IonControlPointSequence[0].SnoutPosition  
    shift = snout + 0.5*thick + NOZZLE_OFFSET
    
    d_x = shift * sin( radians(gantryangle) )
    d_y = shift * cos( radians(gantryangle) )
    
    translation = [d_x, d_y, 0]
    return translation
    s


def get_props( field ):
    """Return RangeShifter object with all properties for field
    (i.e. IonBeamSequence[i])
    """
    
    has_RS = hasattr( field.IonControlPointSequence[0], "RangeShifterSettingsSequence" )
    ##has_RS_2 = hasattr( field, "RangeShifterSequence" )
    
    # Default zero rangeshifter
    rs = Rangeshifter()
    
    ##if has_RS or has_RS_2:       
    if has_RS:
        # Get properties
        #thick = field.RangeShifterSettingsSequence[0].RangeShifterWaterEquivalentThickness
        thick = 5.0
        gantryangle = field.IonControlPointSequence[0].GantryAngle
        trans = get_translation(field, thick, gantryangle)
        
        print("RS props: {},{},{}".format(gantryangle, trans, thick)   )
        
        rs = Rangeshifter(rotation=gantryangle, translation=trans, thickness=thick)
        
    return rs

        