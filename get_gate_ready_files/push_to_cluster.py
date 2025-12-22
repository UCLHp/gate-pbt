import paramiko
from pathlib import Path
import os
import sys
import shutil
import re



# Configuration
SOURCE_PATH = r"\\10.140.79.216\pbtmcdcm\get_gate_ready_files\data\simulationfiles"
ARCHIVE_PATH = r"\\10.140.79.216\pbtmcdcm\get_gate_ready_files\data\simulationfiles\copied_to_cluster"
OUTPUT_PATH = r"\\10.140.79.216\pbtmcdcm\pull_simulated_jobs_and_analyse\submitted_jobs"
REMOTE_USER = "uclh"
REMOTE_HOST = "10.140.79.159"
REMOTE_PATH = "/mnt/clustshare/"
PASSWORD = "vir7ual"



def push_to_cluster(patient_folder_name):
    """Transfer file or folder using paramiko (cross-platform)"""
    
    local_path = os.path.join(SOURCE_PATH, patient_folder_name)
    remote_path = os.path.join(REMOTE_PATH, patient_folder_name)
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Connect
        ssh.connect(
            hostname=REMOTE_HOST,
            username=REMOTE_USER,
            password=PASSWORD,
            look_for_keys=False,
            allow_agent=False
        )
        
        # Create SFTP session
        sftp = ssh.open_sftp()
        
        # Check if it's a file or directory
        if os.path.isfile(local_path):
            # Transfer single file
            sftp.put(local_path, remote_path)
            print(f"File transferred successfully!")
        else:
            # Transfer directory recursively
            _transfer_directory(sftp, local_path, remote_path)
            print(f"Folder transferred successfully!")
        
        sftp.close()
        ssh.close()

        # After successful transfer, move to archive
        archive_path = os.path.join(ARCHIVE_PATH, patient_folder_name)
        os.makedirs(ARCHIVE_PATH, exist_ok=True)
        shutil.move(local_path, archive_path)
        print(f"Original moved to: {archive_path}")
        
        return True
        
    except Exception as e:
        print(f"Transfer failed: {e}")
        return False


def _transfer_directory(sftp, local_dir, remote_dir):
    """Recursively transfer a directory via SFTP"""
    
    # Create remote directory
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass  # Directory might already exist
    
    # Walk through local directory
    for item in os.listdir(local_dir):
        local_item = os.path.join(local_dir, item)
        remote_item = os.path.join(remote_dir, item).replace('\\', '/')  # Linux uses forward slashes
        
        if os.path.isfile(local_item):
            # Transfer file
            sftp.put(local_item, remote_item)
            print(f"  Transferred: {item}")
        elif os.path.isdir(local_item):
            # Recursively transfer subdirectory
            _transfer_directory(sftp, local_item, remote_item)


import paramiko
import re
import os


def ssh_to_cluster_and_submit_jobs(patient_folder_name):
    """SSH to cluster and run wrapper script to submit jobs"""
    
    remote_folder = os.path.join(REMOTE_PATH, patient_folder_name).replace('\\', '/')
    
    # Force login shell with -l flag to ensure environment is loaded
    command = f"~/submit_gate_jobs.sh {remote_folder}"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(REMOTE_HOST, username=REMOTE_USER, password=PASSWORD)
        
        # CRITICAL: Use 'bash -l -c' to force a login shell
        print(f"Executing: bash -l -c '{command}'")
        stdin, stdout, stderr = ssh.exec_command(f"bash -l -c '{command}'", get_pty=True)
        
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        error = stderr.read().decode()
        
        print(f"\n=== Wrapper Script Output ===")
        print(output)
        
        if error:
            print(f"\n=== Errors/Warnings ===")
            print(error)
        
        print(f"\nExit status: {exit_status}")
        
        job_ids = re.findall(r'Submitted batch job (\d+)', output)
        
        if not job_ids:
            print("Warning: No job IDs found in output")
            return []
        
        # Create the directory if it doesn't exist
        os.makedirs(OUTPUT_PATH, exist_ok=True)

        log_file = os.path.join(OUTPUT_PATH, f"{patient_folder_name}_job_ids.txt")
        with open(log_file, 'w') as f:
            f.write(f"Folder: {patient_folder_name}\n")
            f.write(f"Remote path: {remote_folder}\n")
            f.write("=" * 40 + "\n")
            for job_id in job_ids:
                f.write(f"Job ID: {job_id}\n")
                print(f" Submitted job: {job_id}")

        print(f"\n Submitted {len(job_ids)} jobs total")
        print(f" Job IDs saved to {log_file}")
        
        ssh.close()
        return job_ids
        
    except Exception as e:
        print(f" SSH/Submit failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def push_to_cluster_and_submit(patient_folder_name = ""):
    # Check if source file exists
    if not Path(SOURCE_PATH).exists():
        print(f" Error: Source file not found: {SOURCE_PATH}")
        sys.exit(1)

    
    print(f"Transferring: {SOURCE_PATH} -> {patient_folder_name}")
    print(f"To: {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}")
    
    
    success = push_to_cluster(patient_folder_name)
    
    if success:
        print("Moved file to Cluster")
    else:
        print("failed")
    
    # NOW WE NEED TO SSH INTO THE LINUX MACHINE

    job_ids = ssh_to_cluster_and_submit_jobs(patient_folder_name)





if __name__ == "__main__":
    push_to_cluster_and_submit(patient_folder_name = "zzzProtonPlanningBrain--test_brain_mc")
