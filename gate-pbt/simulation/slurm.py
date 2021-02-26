# -*- coding: utf-8 -*-
"""
@author: Steven Court
Methods to make SLURM job script. Split field submitted as a job array.
Our jobs are run on a virtualized linux cluster
"""
import os


# LINUX PATH
CLUSTER_LOCATION = "/mnt/clustshare"



def dos2unix( filein, fileout ):
    """Convert Windows line endings to unix"""   
    with open( filein, 'rb') as infile:    
      content = infile.read()
    with open( fileout, 'wb') as output:
      for line in content.splitlines():
        output.write(line + b'\n')



def make_script(sim_dir_path, fieldname, splits, outpath):
    """Slurm job submission script for field"""
    
    # Identifier is the name of the sim folder; get from local path:
    simdirname = os.path.basename( sim_dir_path )
    simdirclustpath = CLUSTER_LOCATION + "/" + simdirname
    
    with open(outpath, "w") as out:
        out.write("#!/bin/bash\n")
        job = simdirname + "_" + fieldname
        out.write("#SBATCH --job-name={}\n".format(job))
        out.write("#SBATCH --output={}/{}_%A_%a.out\n".format(simdirclustpath,job))
        out.write("#SBATCH --error={}/{}_%A_%a.err\n".format(simdirclustpath,job))
        out.write("#SBATCH --array=1-{}\n".format(splits))
        out.write("#SBATCH --requeue\n")
        out.write("\n")
        
        macfile = fieldname + "_$SLURM_ARRAY_TASK_ID.mac"
        macpath = simdirclustpath + "/mac/" + macfile
        cmd = "srun Gate -a [path,{}] {}".format(simdirclustpath, macpath) 
        
        out.write( cmd )
    out.close()
    
    #Convert from Windows line endings to unix
    dos2unix( outpath, outpath )





