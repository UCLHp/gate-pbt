# -*- coding: utf-8 -*-
"""
Created on Tue Jan 26 10:03:44 2021
@author: SCOURT01

Methods to make SLURM job script. Split field submitted as a job array.
Our jobs are run on a virtualized linux cluster

"""
import os


# LINUX PATH
CLUSTER_LOCATION = "/mnt/clustshare"


def make_script(sim_dir_path, fieldname, splits, outpath):
    """Slurm job submission script for field"""
    
    # Identifier is the name of the sim folder; get from local path:
    simdirname = os.path.basename( sim_dir_path )
    simdirclustpath = CLUSTER_LOCATION + "/" + simdirname
    
    with open(outpath, "w") as out:
        out.write("#!/bin/bash\n")
        job = simdirname + "_" + fieldname
        out.write("#SBATCH --job-name={}\n".format(job))
        out.write("#SBATCH --output=/mnt/clustshare/{}_%A_%a.out\n".format(job))
        out.write("#SBATCH --error=/mnt/clustshare/{}_%A_%a.err\n".format(job))
        #out.write("#SBATCH --output=/mnt/clustshare/{}\n".format(job+".txt"))
        #out.write("#SBATCH --error=/mnt/clustshare/{}\n".format(job+"_errors.txt"))
        out.write("#SBATCH --array=1-{}\n".format(splits))
        out.write("#SBATCH --requeue\n")
        out.write("\n")
        
        macfile = fieldname + "_$SLURM_ARRAY_TASK_ID.mac"
        macpath = simdirclustpath + "/mac/" + macfile
        cmd = "srun Gate -a [path,{}] {}".format(simdirclustpath, macpath) 
        
        out.write( cmd )
    out.close()
