#!/bin/bash
#
#SBATCH --job-name=NMUcal
#SBATCH --output=NMUcal.txt
#SBATCH --error=NMUcal_errors.txt
#SBATCH --array=0-1680
#SBATCH --requeue


# Submit job array for a single energy layer in which spots are to be split into individual 
# simulations so as to obtain equal numbers of primaries in each spot.
# (Above: 20x20cm field with 5mm spacing -> 1681 spots).
#
# Specify energy in the alias below


srun Gate -a [path,/mnt/clustshare/NMUcal][energy,150][spotID,$SLURM_ARRAY_TASK_ID] /mnt/clustshare/NMUcal/mac/NMU_spot_from_square_field.mac
