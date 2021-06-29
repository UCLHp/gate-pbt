# -*- coding: utf-8 -*-
"""
@author: Steven Court
Method to calculate number of primaries required for each field to yield the
absolute dose.

Plan DICOM contains scan spot meterset weights, NOT MUs.
Varian IMS converts via: MU = scanspotweight * (beam meterset / finalcummetersetweight)

See N/MU calibration for details on how this was produced
"""


#TODO: Connect this with source desc file
def particles_per_MU( energy ):
    """Return number of particles per MU
    i.e the N/MU curve in the source desc file 
    """
    E = energy 
    # First draft DemoSTPC
    # n_mu = (3.063861502761413e-05)*E**4 + (0.048007375737805)*E**3 - (50.926377749348596)*E**2 + (2.727779564382193e+04)*E + 2.931906878221635e+05    
    # First draft UCLH_G1 June2021
    n_mu = (-3.804470812246635e-04)*E**4 + (0.297255551220351)*E**3 - (1.074619993259754e+02)*E**2 + (3.370102617771467e+04)*E + (1.176374880535324e+05)
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
    """Return number of protons required for absolute TPS dosimetry"""    

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
        if i%2 == 0:   # Skip empty control points
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
    """Return dictionary of field names and numbers of primaries required"""
    
    fields = dcmplan.IonBeamSequence
    
    req_prims = {}
    for field in fields:
        prims = calc_field_primaries( dcmplan, field )
        req_prims[field.BeamName] = prims
        
    return req_prims

