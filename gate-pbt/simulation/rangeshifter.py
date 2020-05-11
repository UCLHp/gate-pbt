# -*- coding: utf-8 -*-
"""
Created on Thu May  7 16:25:22 2020
@author: SCOURT01


Methods related to positioning of rangeshifter.

Gate simulates the beam from the nozzle exit. Hence if a rangeshifter is
in place we must first position this correctly wrt the patient and then
offset the beam so that it passes through the rangeshifter. (The number to
offset is the nozzle to exit distance in the source description file).

"""

from math import sin, cos, radians


######### TODO
#
# 1. Keep 0mm thickness RS in for all plans? Need to move it out of beam?
# 2. Need exact RS dimensions
#
#########


# dictionary of rangeshifter WET to physical thicknesses in use (since
# dicom file will only contain WET)
RS_THICKNESS = { 57.0:50 }



class Rangeshifter:
    
    def __init__(self, rotation=0, translation=None, thickness=0 ):
        self.rotation = rotation
        self.thickness = thickness 
        if translation is None: 
            translation = [0,0,0]
        self.translation = translation
    

    
def get_translation( iso_to_rs, thick, gantryangle ):
    """Get translation vector required to correctly shift RS in Gate"""
    
    shift = iso_to_rs + 0.5*thick
    
    d_x = shift * sin( radians(gantryangle) )
    d_y = -1.0 * shift * cos( radians(gantryangle) )
    
    translation = [d_x, d_y, 0]
    return translation



def get_props( field ):
    """Return RangeShifter object with all relevant properties
    """
    
    has_RS = hasattr( field.IonControlPointSequence[0], "RangeShifterSettingsSequence" )
    
    # Default zero rangeshifter
    rs = Rangeshifter()
    
    if has_RS:
        rsss =  field.IonControlPointSequence[0].RangeShifterSettingsSequence[0]    
        thick = RS_THICKNESS[ rsss.RangeShifterWaterEquivalentThickness ]
        gantryangle = field.IonControlPointSequence[0].GantryAngle       
        iso_to_rs = rsss.IsocenterToRangeShifterDistance
        trans = get_translation(iso_to_rs, thick, gantryangle) 
        ##print("RS props: {},{},{}".format(gantryangle, trans, thick)   )
        rs = Rangeshifter(rotation=gantryangle, translation=trans, thickness=thick)
        
    return rs

        