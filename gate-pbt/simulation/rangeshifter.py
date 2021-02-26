# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods related to positioning of rangeshifter.
So as to only have 1 mac template file, any field without a rangeshifter
will technically contain a 0.001 mm thick rangeshitfer positioned so as 
to be out of the beam.
"""

from math import sin, cos, radians

######### TODO
# 1. Need exact RS dimensions / chemical composition
# 2. Add all rangeshifters to RS_THICKNESS
#########

# dictionary of rangeshifter WET to physical thicknesses in use (since
# dicom file will only contain WET)
RS_THICKNESS = { 57.0:50 }



class Rangeshifter:
    
    # Default Rangeshifter is 0mm thick and translated 1.45 m to edge of
    # the MergedVolume, out of beam path.
    
    def __init__(self, rotation=0, translation=None, thickness=0.001 ):
        self.rotation = rotation
        self.thickness = thickness 
        if translation is None: 
            # Must ensure this remains within the MergedVolume
            translation = [0,950,0]         
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

        