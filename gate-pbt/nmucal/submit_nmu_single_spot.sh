#!/bin/bash
#
#SBATCH --job-name=NMUcal
#SBATCH --output=NMUcal.txt
#SBATCH --error=NMUcal_errors.txt
#SBATCH --array=70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,244
#SBATCH --requeue


# Simulate single spots per energy layer measuring in large detector volume (as an alternative
# to small detector in a homogenous field).
#
# Specify energies to be simulated in the --array field above.


srun Gate -a [path,/mnt/clustshare/NMUcal][energy,$SLURM_ARRAY_TASK_ID] /mnt/clustshare/NMUcal/mac/NMU_single_spot.mac
