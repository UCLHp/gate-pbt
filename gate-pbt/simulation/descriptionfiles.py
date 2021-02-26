# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods to generate the plan description file for each field and
the source description file"
"""

from math import isclose


def get_plan_description(plan, field):
    """The initial plan description modified to 
    correspond to a single field"""
    pln=[]
    pln.append("#TREATMENT-PLAN-DESCRIPTION")
    pln.append("#PlanName")
    pln.append(plan.RTPlanLabel)
    pln.append("#NumberOfFractions")
    pln.append(len(plan.FractionGroupSequence))
    for frc in plan.FractionGroupSequence:
        pln.append("##FractionID")
        pln.append(frc.FractionGroupNumber)
        pln.append("##NumberOfFields")
        pln.append( "1" )  # ONLY PRINT SINGLE FIELDS
        pln.append("###FieldsID")
        pln.append(field.BeamNumber)
    pln.append("#TotalMetersetWeightOfAllFields")        
    pln.append( field.FinalCumulativeMetersetWeight )  
    return pln



def get_field_description(field):
    fd = []
    fd.append("#FIELD-DESCRIPTION")
    fd.append("###FieldID")
    fd.append(field.BeamNumber)  ## OR DO WE WANT BEAM NAME?
    fd.append("###FinalCumulativeMetersetWeight")
    fd.append(field.FinalCumulativeMetersetWeight)
    fd.append("###GantryAngle")
    fd.append(field.IonControlPointSequence[0].GantryAngle) ## always only in [0]?
    fd.append("###PatientSupportAngle")
    fd.append(field.IonControlPointSequence[0].PatientSupportAngle)
    fd.append("###IsocentrePosition")
    isocentre=""
    for coord in field.IonControlPointSequence[0].IsocenterPosition:
        isocentre += str(coord)
        isocentre += " "
    fd.append( isocentre.strip() )
    fd.append("###NumberOfControlPoints")
    fd.append(len(field.IonControlPointSequence)//2)  ##HALF OF THESE WILL BE THE ZERO WEIGHT SPOTS
    
    #Get the control point descriptions for this beam
    spot_desc = get_spot_descriptions(field)
    # Add them to the field_descritpion
    fd = fd + spot_desc
       
    return fd



def get_spot_descriptions(field):
    sd = []
    sd.append("#SPOTS-DESCRIPTION")
    
    #Only consider CPs with non-zero spots
    nonzero_CPs = []
    for cp in field.IonControlPointSequence:
        if isinstance( cp.ScanSpotMetersetWeights, float ):
            if not isclose(cp.ScanSpotMetersetWeights,0):
                nonzero_CPs.append( cp )
        elif isinstance( cp.ScanSpotMetersetWeights, list ):
            if not all( isclose(w,0) for w in cp.ScanSpotMetersetWeights ):
                nonzero_CPs.append( cp )
    
    for cp in nonzero_CPs:
        sd.append("####ControlPointIndex")
        sd.append( cp.ControlPointIndex//2 )  #Since we are removing CPs with empty spots
        sd.append("####SpotTunnedID")
        sd.append(cp.ScanSpotTuneID)   ## WHAT IS THIS?
        sd.append("####CumulativeMetersetWeight")
        sd.append(cp.CumulativeMetersetWeight)
        sd.append("####Energy (MeV)")
        sd.append(cp.NominalBeamEnergy)
        sd.append("####NbOfScannedSpots")
        sd.append(cp.NumberOfScanSpotPositions)

        sd.append("####X Y Weight")       
        # Want "X Y Weight" for all spots
        weights=[]
        xy=[]
        if isinstance( cp.ScanSpotMetersetWeights, float ):
            # Then have only a single spot
            weights.append( cp.ScanSpotMetersetWeights )
            xy.append( (cp.ScanSpotPositionMap[0], cp.ScanSpotPositionMap[1])  )
        elif isinstance( cp.ScanSpotMetersetWeights, list ):
            for i,w in enumerate(cp.ScanSpotMetersetWeights):
                weights.append(w)
                xy.append( (cp.ScanSpotPositionMap[i*2],cp.ScanSpotPositionMap[i*2+1])  )
        else:
            print("Issue with ScanSpotMetersetWeights" )                  

        for (x,y),w in zip(xy,weights):
            sd.append( str(x)+" "+str(y)+" "+str(w) )

    return sd
                  




def make_field_description(filename, plan_description, field_descriptions):
    """Method to write the PlanDescriptionFile""" 
    with open(filename,"w") as out:
        for l in plan_description:
            out.write( str(l)+"\n" )
        for l in field_descriptions:
            out.write( str(l)+"\n" ) 
    out.close()




'''
def main():

    DICOM_INPUT = "plan.dcm"

    plan = pydicom.read_file(DICOM_INPUT)
   
    for field in plan.IonBeamSequence:
        fld_dsc = get_field_description(field)
        plan_dsc = get_plan_description(plan, field)

        fname = "PlanDescFile_"+str(field.BeamName)+".txt"
        make_field_description( fname, plan_dsc, fld_dsc  )

    
if __name__=="__main__":
    main()
'''    
