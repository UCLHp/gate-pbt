#!/bin/bash
#
#SBATCH --job-name=NMUcal_SquareField
#SBATCH --output=/mnt/clustshare/NMUcal/SquareField_%A_%a.out
#SBATCH --error=/mnt/clustshare/NMUcal/SquareField_%A_%a.err
#SBATCH --array=0-1680
#SBATCH --requeue


# Specify energy in the alias below


# Submit job array for a single energy layer in which spots are to be split into individual 
# simulations so as to obtain equal numbers of primaries in each spot.
#   (20x20cm field with 5mm spacing -> 1681 spots)
#   (10x10cm field with 2.5mm spacing -> 1681 spots)


srun Gate -a [path,/mnt/clustshare/NMUcal][energy,150][spotID,$SLURM_ARRAY_TASK_ID] /mnt/clustshare/NMUcal/mac/spot_from_square_field.mac
