# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 16:18:58 2020
@author: SCOURT01

Investigating field statistics, such as energy levels used,
total number of CPs, spots and MUs binned by energy.

"""



def particles_per_MU( energy ):
    """Return number of particles per MU
    i.e the N/MU curve in the source desc file
    """
    # Daniela's curve; FIRST DRAFT
    E = energy 
    n_mu = (3.063861502761413e-05)*E**4 + (0.048007375737805)*E**3 - (50.926377749348596)*E**2 + (2.727779564382193e+04)*E + 2.931906878221635e+05    
    return n_mu

    

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



def calc_field_primaries(plan, field):
    """Plot MUs, #spots and estimated simulation time for each CP"""    

    ##############################
    # Plan DICOM contains scan spot meterset weights, NOT MUs.
    # Varian IMS converts via:
    # MU = scanspotweight * (beam meterset / finalcummetersetweight)
    ##############################

    beamnumber = field.BeamNumber
    
    finalcummeterset = field.FinalCumulativeMetersetWeight
    beammeterset = get_beam_meterset( plan, beamnumber )
    
    cps = field.IonControlPointSequence
    
    energies = []
    tot_mus = []
    
    for i,cp in enumerate(cps):
        if i%2 == 0:   # Skip empty CPs
            energies.append( cp.NominalBeamEnergy )
            # Count spots and MUs
            if isinstance(cp.ScanSpotMetersetWeights, float):
                spotweights = cp.ScanSpotMetersetWeights
                mus = spotweights * (beammeterset/finalcummeterset)
                tot_mus.append( mus )
            else:
                spotweights = sum(cp.ScanSpotMetersetWeights)
                mus = spotweights * (beammeterset/finalcummeterset)
                tot_mus.append( mus )

    tot_prims = 0
    for cpe,mu in zip(energies,tot_mus):
        primaries = particles_per_MU(cpe) * mu
        tot_prims += primaries
    
    return tot_prims
    
    
    


def get_required_primaries( dcmplan ):
    """Return absolute number of primaries required per field"""
    
    fields = dcmplan.IonBeamSequence
    
    req_prims = {}
    for field in fields:
        prims = calc_field_primaries( dcmplan, field )
        req_prims[field.BeamName] = prims
        
    return req_prims

