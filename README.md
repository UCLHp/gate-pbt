# gate-pbt
![Current Version](https://img.shields.io/badge/version-0.1.0-green.svg)

Monte Carlo simulations of proton therapy treatments using [Gate](https://gate.uca.fr/#/admin)/[GateTools](https://github.com/OpenGATE/GateTools)/[Geant4](https://geant4.web.cern.ch/).

## Prerequisites
Python dependencies are listed in requirements.txt.  

To run the simulations you'll need Gate and Geant4 installed. 
See the Gate documentation [here](https://gate.uca.fr/documentation#/admin) for more info
and examples. This work has been performed using 
the virtual machines, version 8.1 and 8.2, available [here](https://gate.uca.fr/download/vgate#/admin). 
These are Linux VMs that include a Geant4 install along with various other useful software.
If you wish to align with the Gate-RTion recommendations, a VM with Gate 8.1 and Geant4 10.3.3
will be available soon.  

Development and testing has so far been done using pencil beam scanning proton plans created in the Eclipse treatment planning system (versions 13.7, 15.5 and 16.1). If you run into issues using another TPS let me know.

The physics list and simulation parameters used in the simulation can be set in the mac 
template file and will be aligned to the [Gate-RTion recommendations](https://aapm.onlinelibrary.wiley.com/doi/10.1002/mp.14481) as default. More information about the Gate-RTion collaboration can be found [here](https://gate.uca.fr/download/gate-rtion#/admin).


## Usage

### File preparation
First export the relevant dicom files from the TPS to an empty folder.
You will need the plan file, the structure set, the _field_ dose files and all CT images.  

In the simulation directory, ```python run.py``` will prompt for the directory containing
the exported dicom files and generate a folder containing all files required for 
a Gate simulation (in data/simulationfiles).  

The script will automatically split the fields into separate simulations and generate a Slurm job 
submission script for each field. This process can be optimized depending on your cluster and how you
want to split the simulations. 


### Simulation
On our cluster, submitting the array of jobs corresponding to a field can be done via the command
```sbatch path/to/script.sh``` from the control node.


### Analysis
The simulations will generate, for each mac file submitted, mhd files for dose and dose-squared by default. Options for dose-to-water, LET and uncertainty can be set manually in the mac template file.

A full analysis of the data generated can be performed from the analysis directory, ```python analysis.py```.
It will prompt for the directory containing the simulation output and:

1. Separate the data for individual fields and merge all data present (dose, dose-squared, LET)
2. Override the TransformMatrix to "1 0 0 0 1 0 0 0 1" in all of the merged mhd files. This is required since Gate preserves any patient rotations performed in the simulation in its output's TransformMatrix. In the file preparation stage we reorientated all images to this directionality so as to avoid some bugs in both Gate and GateTools
3. Calculate the dose uncertainty following [Chetty2006](https://pubmed.ncbi.nlm.nih.gov/16798417/)
4. Scale the simulation to absolute dose using the N/MU curve provided
5. Convert Gate's dose-to-material to dose-to-water following [Paganetti2009](https://iopscience.iop.org/article/10.1088/0031-9155/54/14/004/pdf), using the HU-density and HU-RSP curves provided. Gate has the option of calculating dose-to-water on the fly but this slows down the simulations by a factor of about 3
6. Convert each field's dicom dose into an mhd image and perform a 3D gamma analysis between this and the dose calculated in the simulation
7. Convert the dose and gamma mhd images into dicom format for easy import and visualization in the treatment planning system


## Limitations / known bugs
Likely many - feel free to get in touch if you have any questions.


## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss 
what you would like to change.


## License
```
Copyright (C) 2020 Steven Court

gate-pbt: proton therapy simulations using GATE/Geant4.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```
