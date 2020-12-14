# -*- coding: utf-8 -*-
"""
Created on Fri Jun 19 11:33:23 2020

@author: SCOURT01
"""

import matplotlib.pyplot as plt
from numpy.polynomial import Polynomial


def plot_energy_pps(filename):
    """Plot E vs PPS data from gate simulations"""
    
    x,y = [], []
    for line in open(filename, "r"):
        values = [float(s) for s in line.strip().split()]
        x.append(values[0])
        y.append(values[1])
    
    plt.figure(figsize=(10,6))
    plt.plot(x, y, linewidth=3)
    plt.xlabel("Energy (Mev)", fontsize=16)
    plt.ylabel("Primaries per second (PPS)", fontsize=17)
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.xlim((60,265))
    #plt.savefig("e_pps.png")
    plt.show()



def plot_energy_nmu():
    """Plot N/MU vs energy; i.e. polynomial in source desc file"""
    # Calibration taken from skandion
    # https://github.com/OpenGATE/GateContrib/blob/master/dosimetry/dosimetry/protontherapy/data/Source-Properties.txt

    energies = list(range(70,251,5))
    n_mu = []
    for E in energies:
        nmu = 38305849.80777806 - 757267.7950206206*E + 39470.879309031465*E**2 -\
            692.4982726864837*E**3 + 7.991201233899195*E**4 + \
            7.991201233899195*E**5 - 0.059977540330568506*E**6 + \
            0.00027937202589281356*E**7 - 0.0000007598937570035222*E**8 + \
            0.0000000010784400314569827*E**9 - 0.0000000000005984490922947305*E**10
        n_mu.append( nmu )
        
    print("N/MU @ {} MeV: {}, {} MeV: {}".format(energies[0],n_mu[0],energies[-1],n_mu[-1]) )    
    print("   --> ratio = {}".format(n_mu[-1]/n_mu[0]) )
        
    plt.figure(figsize=(10,6))
    plt.plot(energies, n_mu, linewidth=3)
    plt.xlabel("Energy (Mev)", fontsize=16)
    plt.ylabel("N/MU calibration (Skandion)", fontsize=17)
    plt.yscale("log")
    plt.xticks(fontsize=14)
    plt.yticks(fontsize=14)
    plt.xlim((60,265))
    #plt.savefig("n_mu_skandion.png")
    plt.show() 
    
    
    
def get_time_per_particle( e_vs_pps_file ):
    """Estimate the simulation time per primary particle, in water
    at different energies. Return polynomial fit"""
    # Takes E_vs_PPS data
    
    energies, time_per_prim = [], []
    for line in open(e_vs_pps_file, "r"):
        values = [float(s) for s in line.strip().split()]
        energies.append(values[0])
        time_per_prim.append( 1.0/values[1] )

    plt.scatter(energies, time_per_prim)

    p = Polynomial.fit(energies, time_per_prim, 2)
    plt.plot(*p.linspace())
    
    ################# checking polynomial fit ##################
    time = []
    for en in energies:
        t = -6.2931E-4 + 1.3926E-5*en + 1.5251E-8*en**2
        time.append(t)

    plt.scatter(energies,time, s=15)
    ############################################################
            
    plt.ylabel("Simulation time per primary")
    plt.xlabel("Energy")
    plt.ylim((0,0.005))
    
    ###print(p)
    # correct coefficients
    pnormal = p.convert(domain=(-1, 1))
    print("time per particle polynomial params = {}".format(pnormal))
    
    
    
    
def get_n_per_mu( e_vs_nmu_file ):
    """Return polynomial fit of E vs N/MU curve"""
    
    energies, nmu = [], []
    for line in open(e_vs_nmu_file, "r"):
        values = [float(s) for s in line.strip().split()]
        energies.append( values[0] )
        nmu.append( values[1] )

    plt.scatter(energies, nmu)

    p = Polynomial.fit(energies, nmu, 5)
    plt.plot(*p.linspace())
    
    ################# checking polynomial fit ##################
    nmu_fit = []
    for en in energies:
    #    n = 3.528489E+7 + (2.975837E+6)*en - (5.143418E+3)*en**2 + 5.362886*en**3
    #    n = 2.35643E+7 + (3.3294727E+6)*en - (8.8892359E+3)*en**2 + (2.199734E+1)*en**3 - (2.634455E-2)*en**4       
        n = 7.96835276E+7 + (1.19619046E+6)*en + (2.19278161E+4)*en**2 - (1.9025047E+2)*en**3 + (6.73796045E-1)*en**4 - (8.89071546E-4)*en**5
    
        nmu_fit.append(n)
    
    plt.scatter(energies,nmu_fit, s=15)
    ############################################################
            
    plt.ylabel("N/MU Christie")
    plt.xlabel("Energy")
    #plt.ylim((0,0.005))
    
    ###print(p)
    # correct coefficients
    pnormal = p.convert(domain=(-1, 1))
    print("N/MU vs E polynomial params = {}".format(pnormal))
    
    

get_n_per_mu("Christie__NominalEnergy_ProtonsPerMU.dat")


#plot_energy_pps("E_vs_PPS.dat")
#get_time_per_particle("E_vs_PPS.dat")
#plot_energy_nmu()



