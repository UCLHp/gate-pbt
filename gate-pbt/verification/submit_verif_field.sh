#!/bin/bash
#SBATCH --job-name=verif_1
#SBATCH --output=/mnt/clustshare/verif_1/%A_%a.out
#SBATCH --error=/mnt/clustshare/verif_1/%A_%a.err
#SBATCH --array=1-10
#SBATCH --requeue

srun Gate -a [path,/mnt/clustshare/verif_1][run,$SLURM_ARRAY_TASK_ID] /mnt/clustshare/verif_1/mac/verif_1.mac
