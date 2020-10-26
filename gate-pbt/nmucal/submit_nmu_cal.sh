#!/bin/bash
#
#SBATCH --job-name=NMUcal
#SBATCH --output=NMUcal.txt
#SBATCH --error=NMUcal_errors.txt
#SBATCH --array=70,80,90,100,110,120,130,140,150,160,170,180,190,200,210,220,230,240,244
#SBATCH --requeue


srun Gate -a [path,/mnt/clustshare/NMUcal][energy,$SLURM_ARRAY_TASK_ID] /mnt/clustshare/NMUcal/mac/NMU_single_E.mac
