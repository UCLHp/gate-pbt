# -*- coding: utf-8 -*-
"""

Script to generate plan description files for single energy square
fields to be used in calibrating simulation N and TPS MU.

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



def get_spot_descriptions(energy, nspots, spacing, mu):
    sd = []
    sd.append("#SPOTS-DESCRIPTION")
   
    sd.append("####ControlPointIndex")
    sd.append( "1" )  
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
                  




def make_field_description(filename, plan_dsc, field_dsc, spot_dsc):
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
    ###ENERGY = 150          ## Beam energy, MeV
    ENERGIES = list( range(70,241,10) ) + [244]
    
    nspots_per_row = FIELD_SIZE/SPOT_SPACING + 1
    nspots = nspots_per_row**2
    
    finalcummetersetweight = nspots * SPOT_MU
    
    
    plan_dsc = get_plan_description(finalcummetersetweight)   
    fld_dsc = get_field_description(finalcummetersetweight)
    
    for energy in ENERGIES:
        
        spot_dsc = get_spot_descriptions(energy, nspots, SPOT_SPACING, SPOT_MU)
        filename = "Sq{}mm_Spacing{}mm_{}MU_{}MeV.txt".format(FIELD_SIZE,SPOT_SPACING,SPOT_MU,energy)
        make_field_description( filename, plan_dsc, fld_dsc, spot_dsc  )
        

  
    
if __name__=="__main__":
    main()
  
