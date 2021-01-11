# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 16:18:58 2020
@author: SCOURT01

Investigating field statistics, such as energy levels used,
total number of CPs, spots and MUs binned by energy.

"""
import pydicom
import matplotlib.pyplot as plt



def particles_per_MU( energy ):
    """Return number of particles per MU
    i.e the N/MU curve in the source desc file
    """
    E = energy
    
    # Calibration taken from IBA @ Skandion
    # https://github.com/OpenGATE/GateContrib/blob/master/dosimetry/dosimetry/protontherapy/data/Source-Properties.txt
    #n_mu = 38305849.80777806 - 757267.7950206206*E + 39470.879309031465*E**2 -\
    #    692.4982726864837*E**3 + 7.991201233899195*E**4 + \
    #    7.991201233899195*E**5 - 0.059977540330568506*E**6 + \
    #    0.00027937202589281356*E**7 - 0.0000007598937570035222*E**8 + \
    #    0.0000000010784400314569827*E**9 - 0.0000000000005984490922947305*E**10
        
    # From Christie
    #n_mu = 7.96835276E+7 + (1.19619046E+6)*E + (2.19278161E+4)*E**2 - \
    #    (1.9025047E+2)*E**3 + (6.73796045E-1)*E**4 - (8.89071546E-4)*E**5   
        
        
   
    #From Daniela
    #n_mu = (4.29113258740004e-05)*E**4 + (0.0672373781511538)*E**3 - (71.3256258226481)*E**2 + (38204.2849176103)*E + 410632.1756716
    ##   
    n_mu = (3.063861502761413e-05)*E**4 + (0.048007375737805)*E**3 - (50.926377749348596)*E**2 + (2.727779564382193e+04)*E + 2.931906878221635e+05
    
    
    return n_mu


    

def time_per_primary( energy ):
    """Return time per primary as simulated in water

    (arbitrary settings; just want relative values)
    See timings.py for fit    
    """
    en = energy
    t = -6.2931E-4 + 1.3926E-5*en + 1.5251E-8*en**2
    return t



def plot_relative_cp_sim_time( fieldname, energies, tot_mus ):
    """Plot relative simulation time for each CP"""

    
    times = []
    tot_prims = 0
    for cpe,mu in zip(energies,tot_mus):
        primaries = particles_per_MU(cpe) * mu
        tpp = time_per_primary( cpe )
        times.append(tpp*primaries)
        #
        tot_prims += primaries
    
    times_rel = [ t/sum(times)*100 for t in times ]    
    print("Relative CP simulation times (%) for field '{}':".format(fieldname))
    print(times_rel)
    
    
    #times_norm = [ t/max(times) for t in times ]    
    #print("Relative control point simulation times, field: {}:".format(fieldname))
    #print(times_norm)       
        
    plt.figure()
    plt.scatter(energies,times_rel)
    #plt.scatter(energies,times_norm)
    plt.xlabel("ControlPoint Energy (MeV)")
    plt.ylabel("Relative simulation time (%)")
    plt.title(fieldname)
    plt.show()      
    
    #####
    print("Particles for field {} = {}".format(fieldname,tot_prims))
    



def plot_mus(fieldname, energies, tot_mus):
    plt.figure()
    plt.scatter(energies, tot_mus)
    plt.xlabel("ControlPoint Energy (MeV)")
    plt.ylabel("Total MU")
    plt.title(fieldname)
    plt.show()
    
    
def plot_spots(fieldname, energies, tot_spots):
    plt.figure()
    plt.scatter(energies, tot_spots)
    plt.xlabel("ControlPoint Energy (MeV)")
    plt.ylabel("Number spots")
    plt.title(fieldname)
    plt.show()
    
    

def get_beam_meterset(plan, beamnum):
    """Return dcm BeamMeterset value for given beam number"""
    
    beam_meterset = -1
    
    for rbs in plan.FractionGroupSequence[0].ReferencedBeamSequence:
        if rbs.ReferencedBeamNumber == beamnum:
            beam_meterset = rbs.BeamMeterset

    if beam_meterset < 0:
        print("ERROR: no beam meterset weight found")
        exit(2)
    
    return beam_meterset



def plot_field_stats(plan, field):
    """Plot MUs, #spots and estimated simulation time for each CP"""    

    fieldname = field.BeamName
    beamnumber = field.BeamNumber
    
    ##############################
    # Plan DICOM contains scan spot meterset weights, NOT MUs.
    # Varian IMS converts via:
    # MU = scanspotweight * (beam meterset / finalcummetersetweight)
    ##############################
    
    finalcummeterset = field.FinalCumulativeMetersetWeight
    beammeterset = get_beam_meterset( plan, beamnumber )
    
    cps = field.IonControlPointSequence
    
    energies = []
    tot_mus = []
    tot_spots = []
    
    for i,cp in enumerate(cps):
        if i%2 == 0:   # Skip empty CPs
            energies.append( cp.NominalBeamEnergy )
            # Count spots and MUs
            if isinstance(cp.ScanSpotMetersetWeights, float):
                spotweights = cp.ScanSpotMetersetWeights    ## THESE ARE NOT MU VALUES?!
                mus = spotweights * (beammeterset/finalcummeterset)
                tot_mus.append( mus )
                tot_spots.append( 1 )
            else:
                spotweights = sum(cp.ScanSpotMetersetWeights)
                mus = spotweights * (beammeterset/finalcummeterset)
                tot_mus.append( mus )
                tot_spots.append( len(cp.ScanSpotMetersetWeights) )

            
    print()        
    print("----- Field {} -----".format(fieldname))
    print("FINAL CUM = ", finalcummeterset)
    print("BEAM METERSET = ", beammeterset)
    print("RATIO = ", beammeterset/finalcummeterset)
    print("  Energy layers: {}, {}->{} MeV".format(len(energies),energies[-1],energies[0]))
    print("  Total spots: {}".format(sum(tot_spots)))
    print("  Total field ScanSpotMetersetWeight {}".format(sum(tot_mus)))


    plot_mus(fieldname, energies, tot_mus)
    plot_spots(fieldname,energies, tot_spots)
    plot_relative_cp_sim_time(fieldname, energies, tot_mus)






def main():
    
    #DICOM_PLAN = "dcmplan_BaseSkull01.dcm"
    #DICOM_PLAN = "zzzProtonPlanning17.dcm"
    #DICOM_PLAN = "sarcoma.dcm"
    #DICOM_PLAN = "sarcoma_huge_target.dcm"
    #DICOM_PLAN = r"M:/vGATE-GEANT4/DoseToWater/MC_chest_wall/RN.1.2.246.352.221.461617125122614828210562692546382058883.dcm"
    
    #DICOM_PLAN = "RN.ZZ_Proton_COP.SingleSpot.dcm"
    #DICOM_PLAN = "RN.ZZ_Proton_COP.Layer.dcm"
    
    
    DICOM_PLAN = r"M:\vGATE-GEANT4\_dcm_data\DCM_zzzBaseSkull05\RN.1.2.246.352.71.5.179454110911.38673.20201217164318.dcm"



    plan = pydicom.dcmread(DICOM_PLAN)    
    fields = plan.IonBeamSequence
    
    for field in fields:
        plot_field_stats( plan, field )


if __name__=="__main__":
    main()