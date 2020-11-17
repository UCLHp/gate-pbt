# -*- coding: utf-8 -*-
"""

Script to generate plan description files at multiple energies for:
(1) homogenous square fields 
(2) single spots
to be used in calibrating simulation N and TPS MU.

"""

def get_plan_description(final_cum_meterset_weight):
    pln=[]
    pln.append("#TREATMENT-PLAN-DESCRIPTION")
    pln.append("#PlanName")
    pln.append("QAfield")
    pln.append("#NumberOfFractions")
    pln.append("1")
    pln.append("##FractionID")
    pln.append("1")
    pln.append("##NumberOfFields")
    pln.append( "1" )
    pln.append("###FieldsID")
    pln.append("1")
    pln.append("#TotalMetersetWeightOfAllFields")        
    #pln.append( field.FinalCumulativeMetersetWeight )  
    pln.append( final_cum_meterset_weight )  
    return pln



def get_field_description(final_cum_meterset_weight):
    fd = []
    fd.append("#FIELD-DESCRIPTION")
    fd.append("###FieldID")
    fd.append("1") 
    fd.append("###FinalCumulativeMetersetWeight")
    fd.append(final_cum_meterset_weight)
    fd.append("###GantryAngle")
    fd.append("0")
    fd.append("###PatientSupportAngle")
    fd.append("0")
    fd.append("###IsocentrePosition")
    fd.append( "0 0 0 " )
    fd.append("###NumberOfControlPoints")
    fd.append("1")  
    return fd



def get_spot_descriptions_squarefield(energy, nspots, spacing, mu):
    sd = []
    sd.append("#SPOTS-DESCRIPTION")
   
    sd.append("####ControlPointIndex")
    sd.append( "0" )  
    sd.append("####SpotTunnedID")
    sd.append("4.0")   ## WHAT IS THIS?
    sd.append("####CumulativeMetersetWeight")
    sd.append("0")
    sd.append("####Energy (MeV)")
    sd.append(energy)
    sd.append("####NbOfScannedSpots")
    sd.append(nspots)
    sd.append("####X Y Weight")       
           
    spots_per_row = int(nspots**0.5)
    min_coord = (0 - (spots_per_row-1)//2) * spacing
              
    for i in range( int(nspots**0.5) ):
        for j in range( int(nspots**0.5) ):                   
            x = min_coord + i*spacing
            y = min_coord + j*spacing
            sd.append( str(x)+" "+str(y)+" "+str(mu) )

    return sd



def get_spot_description_single(energy):
    sd = []
    sd.append("#SPOTS-DESCRIPTION")
   
    sd.append("####ControlPointIndex")
    sd.append( "0" )  
    sd.append("####SpotTunnedID")
    sd.append("4.0")   ## WHAT IS THIS?
    sd.append("####CumulativeMetersetWeight")
    sd.append("0")
    sd.append("####Energy (MeV)")
    sd.append(energy)
    sd.append("####NbOfScannedSpots")
    sd.append("1")
    sd.append("####X Y Weight")       
    sd.append("0 0 1")

    return sd
                  




def make_plan_description_file(filename, plan_dsc, field_dsc, spot_dsc):
    with open(filename,"w") as out:
        for l in plan_dsc:
            out.write( str(l)+"\n" )
        for l in field_dsc:    
            out.write( str(l)+"\n" ) 
        for l in spot_dsc:
            out.write( str(l)+"\n" ) 
    out.close()







def main():
    
    FIELD_SIZE = 200       ## Square field, mm
    SPOT_SPACING = 5    ## Spot centre to centre distance, mm
    SPOT_MU = 10          ## Equally weighted spots
    ENERGIES = list( range(70,241,10) ) + [244]
    
    nspots_per_row = FIELD_SIZE/SPOT_SPACING + 1
    nspots = int(nspots_per_row**2)
    finalcummetersetweight = nspots * SPOT_MU
    
    # Square field
    plan_dsc_sq = get_plan_description(finalcummetersetweight)   
    fld_dsc_sq = get_field_description(finalcummetersetweight)
    # Single spot
    plan_dsc_sing = get_plan_description(1)   
    fld_dsc_sing = get_field_description(1)
    
    
    
    for energy in ENERGIES:
        
        # Make square field plan description file
        spot_dsc = get_spot_descriptions_squarefield(energy, nspots, SPOT_SPACING, SPOT_MU)
        filename = "Sq{}mm_Spacing{}mm_{}MeV.txt".format(FIELD_SIZE,SPOT_SPACING,energy)
        make_plan_description_file( filename, plan_dsc_sq, fld_dsc_sq, spot_dsc  )
        
        # Make single spot plan description file
        spot_dsc_sing = get_spot_description_single(energy)
        filename_sing = "SingleSpot_{}MeV.txt".format(energy)
        make_plan_description_file( filename_sing, plan_dsc_sing, fld_dsc_sing, spot_dsc_sing)
        

  
    
if __name__=="__main__":
    main()
  
