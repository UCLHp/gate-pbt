# gate-pbt
![Current Version](https://img.shields.io/badge/version-0.1.0-green.svg)

Simulating proton therapy treatments using Gate/GateTools/Geant4

## Prerequisites
Python dependencies are listed in requirements.txt. To run the simulations you'll need
Gate and Geant4 installed. All of my work has been performed using the virtual machine
version 8.2, available [here](http://www.opengatecollaboration.org/node/91). 
This includes the Geant4 10.03.p03 install along with various other useful software.


## Usage

### File preparation
First export the relevant dicom files from the TPS to an empty folder.
You will need the plan file, the structure set, the plan dose and all CT images. 
All CT files must be placed in a subdirectory called "ct".

In the simulation directory, ```python run.py``` will prompt for the directory containing
your exported dicom files and generate a new directory containing all files required for 
a Gate simulation (found in data/simulationfiles). Individual mac files will be generated separately for each field in
the plan.

If running on a cluster you can split a simulation: ```jobsplitter.split_by_primaries(field.mac, N)``` 
will split a mac file into N separate files based purely on the number of primaries. E.g. providing
a simulation field.mac that has 100E6 primaries and specifying N=10, 10 mac files will be generated
each with 10E6 primaries. It will also rename the output appropriately.


### Simulation
To run the simulations you will need Gate installed: ```Gate filename.mac```.
See the Gate documentation [here](http://www.opengatecollaboration.org/UsersGuide) for more info
and examples. 


### Analysis
The simulations will generate, for each mac file, mhd and raw files for dose, LET, and uncertainty.

```python mergeresults.py``` prompts for the directory with these files and combines them. 
Use this to combine results for indiviudal fields, or for the full plan.

```dose_mhd2dcm(dose.mhd, dose.dcm)``` takes the mhd output from Gate and the corresponding
plan/field dicom dose file and converts the mhd format to a dcm format so that it can be imported
into the TPS for comparison.



## Limitations / known bugs
Many. I only recommend that you use the code to generate the Gate simulation files.

All testing has been done using pencil beam scanning proton plans created in the Eclipse treatment planning system (versions 13.7 and 15.5).

The header information in the mhd output from Gate will not match that of the CT image (due to
any rotations applied in Gate when setting up the patient). You must manually correct this by changing
the TransformMatrix field to match that of the CT.

When simulating certain patient positions (HFP for example) Gate will also produce the wrong Origin in the
mhd file. If this is the case, a file will have been generated when creating the gate files with the
correct Origin to be used.


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
