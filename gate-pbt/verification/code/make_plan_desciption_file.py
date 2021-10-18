# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods to generate the plan description file for each field and
the source description file"
"""

from math import isclose

import pydicom

import fieldstats





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





def main():

    #DICOM_INPUT = r"M:\vGATE-GEANT4\gate-pbt\gate-pbt\verification\_Plan Data\NPL boxes\NPL plans I simulated\d10\RN.1.2.246.352.71.5.179454110911.40613.20210617163548.dcm"
    #DICOM_INPUT = r"M:/vGATE-GEANT4/gate-pbt/gate-pbt/verification/_Plan Data/NPL plans/d25/RN.1.2.246.352.71.5.179454110911.40659.20210623145028.dcm"
    #DICOM_INPUT = r"M:/vGATE-GEANT4/gate-pbt/gate-pbt/verification/_Plan Data/Single spots/174.857MeV_iso20cm/RN.1.2.246.352.71.5.957952195770.1307421.20210708111937.dcm"
 
    # DDNCF fields
    #DICOM_INPUT = r"M:\vGATE-GEANT4\gate-pbt\gate-pbt\verification\_Plan Data\DDNCF_Plans\RN.9.35x20_x5.dcm"
    # AxB plan
    #A,B=35,20
    #iso_depth = A-0.5*B 
    #trans = 20 - iso_depth
    #print("\n\nSet iso depth to = "+str(iso_depth)+"cm")
    #print("  -> Water translation = "+str(trans)+" cm in Y") 
    #print("  -> Roos translation = "+str(-1*trans)+" cm in Y\n")
    
    #DICOM_INPUT = r"M:\vGATE-GEANT4\gate-pbt\gate-pbt\verification\_Plan Data\5x5x5_SOBP\RN.9.5x5x5_5cm_RS5_x9.dcm"
    DICOM_INPUT = r"M:\vGATE-GEANT4\gate-pbt\gate-pbt\verification\_Plan Data\NPL boxes\NPL plans I simulated\d15\RN.1.2.246.352.71.5.179454110911.40658.20210623142506.dcm"

    

    
    plan = pydicom.read_file(DICOM_INPUT)
    
    required_primaries = fieldstats.get_required_primaries( plan )
    
    print(required_primaries)
   
    for field in plan.IonBeamSequence:
        fld_dsc = get_field_description(field)
        plan_dsc = get_plan_description(plan, field)

        fname = "PlanDescriptionFile_"+str(field.BeamName)+".txt"
        make_field_description( fname, plan_dsc, fld_dsc  )




    
if __name__=="__main__":
    main()
   
