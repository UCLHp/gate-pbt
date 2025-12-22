#!/bin/bash
#
#SBATCH --job-name=NMUcal_singleCentralSpot
#SBATCH --output=/mnt/clustshare/NMUcal/singleCentral_%A_%a.out
#SBATCH --error=/mnt/clustshare/NMUcal/singleCentral_%A_%a.err
#SBATCH --array=70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,244
#SBATCH --requeue


# Simulate a single central axis spot for each energy in --array.
# Measure dose in a large detector volume (as a quicker alternative
# to using a small detector in a homogenous field).
#
# Specify energies to be simulated in the --array field above.


srun Gate -a [path,/mnt/clustshare/NMUcal][energy,$SLURM_ARRAY_TASK_ID] /mnt/clustshare/NMUcal/mac/single_central_spot.mac
