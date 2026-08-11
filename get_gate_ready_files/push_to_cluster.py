import os
import re
import shutil
import shlex
from pathlib import Path

import paramiko


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SOURCE_PATH = r"\\10.140.79.216\pbtmcdcm\get_gate_ready_files\data\simulationfiles"
ARCHIVE_PATH = r"\\10.140.79.216\pbtmcdcm\get_gate_ready_files\data\simulationfiles\copied_to_cluster"
OUTPUT_PATH = r"\\10.140.79.216\pbtmcdcm\pull_simulated_jobs_and_analyse\submitted_jobs"
REMOTE_USER = "uclh"
REMOTE_HOST = "10.140.79.159"
REMOTE_PATH = "/mnt/clustshare/"

# Credentials -- no longer hardcoded. Same variables as the pull watchdog:
# Preferred: SSH key. Set CLUSTER_SSH_KEY to the path of your private key,
#            e.g.  setx CLUSTER_SSH_KEY "C:\Users\you\.ssh\id_ed25519"
# Fallback:  password via environment variable,
#            e.g.  setx CLUSTER_PASSWORD "yourpassword"
# (Run setx once in a terminal, then open a NEW terminal for it to take effect.)
SSH_KEY_FILE = os.environ.get("CLUSTER_SSH_KEY")
PASSWORD = os.environ.get("CLUSTER_PASSWORD")


def _ssh_connect() -> paramiko.SSHClient:
    """Create and return a connected SSH client using key or password auth."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if SSH_KEY_FILE:
        ssh.connect(
            hostname=REMOTE_HOST,
            username=REMOTE_USER,
            key_filename=SSH_KEY_FILE,
            look_for_keys=False,
            allow_agent=False,
        )
    elif PASSWORD:
        ssh.connect(
            hostname=REMOTE_HOST,
            username=REMOTE_USER,
            password=PASSWORD,
            look_for_keys=False,
            allow_agent=False,
        )
    else:
        raise RuntimeError(
            "No credentials configured. Set the CLUSTER_SSH_KEY or "
            "CLUSTER_PASSWORD environment variable (see comments at top of script)."
        )
    return ssh


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------
def _transfer_directory(sftp, local_dir, remote_dir):
    """Recursively transfer a directory via SFTP.
    Exceptions propagate so the caller knows the transfer was incomplete."""
    try:
        sftp.mkdir(remote_dir)
    except IOError:
        pass  # Directory might already exist

    for item in os.listdir(local_dir):
        local_item = os.path.join(local_dir, item)
        remote_item = f"{remote_dir.rstrip('/')}/{item}"

        if os.path.isfile(local_item):
            sftp.put(local_item, remote_item)
            print(f"  Transferred: {item}")
        elif os.path.isdir(local_item):
            _transfer_directory(sftp, local_item, remote_item)


def push_to_cluster(patient_folder_name) -> bool:
    """Transfer the patient folder to the cluster; archive the local copy
    only after a fully successful transfer. Returns True on success."""
    local_path = os.path.join(SOURCE_PATH, patient_folder_name)
    remote_path = f"{REMOTE_PATH.rstrip('/')}/{patient_folder_name}"

    try:
        ssh = _ssh_connect()
        sftp = ssh.open_sftp()

        if os.path.isfile(local_path):
            sftp.put(local_path, remote_path)
            print("File transferred successfully!")
        else:
            _transfer_directory(sftp, local_path, remote_path)
            print("Folder transferred successfully!")

        sftp.close()
        ssh.close()

        # After successful transfer, move local copy to archive
        os.makedirs(ARCHIVE_PATH, exist_ok=True)
        archive_path = os.path.join(ARCHIVE_PATH, patient_folder_name)
        shutil.move(local_path, archive_path)
        print(f"Original moved to: {archive_path}")

        return True

    except Exception as e:
        print(f"Transfer failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Job submission
# ---------------------------------------------------------------------------
def ssh_to_cluster_and_submit_jobs(patient_folder_name):
    """SSH to cluster and run wrapper script to submit jobs.
    Returns the list of submitted Slurm job IDs ([] on failure)."""
    remote_folder = f"{REMOTE_PATH.rstrip('/')}/{patient_folder_name}"

    # shlex.quote guards against spaces/special chars in the folder name
    command = f"~/submit_gate_jobs.sh {shlex.quote(remote_folder)}"

    try:
        ssh = _ssh_connect()

        # Use 'bash -l -c' to force a login shell so the environment is loaded
        print(f"Executing: bash -l -c '{command}'")
        stdin, stdout, stderr = ssh.exec_command(f"bash -l -c '{command}'", get_pty=True)

        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode()
        error = stderr.read().decode()

        print("\n=== Wrapper Script Output ===")
        print(output)

        if error:
            print("\n=== Errors/Warnings ===")
            print(error)

        print(f"\nExit status: {exit_status}")

        ssh.close()

        job_ids = re.findall(r'Submitted batch job (\d+)', output)

        if not job_ids:
            print("Warning: No job IDs found in output")
            return []

        # Write the job-ID ticket that the pull watchdog monitors
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

        return job_ids

    except Exception as e:
        print(f" SSH/Submit failed: {e}")
        import traceback
        traceback.print_exc()
        return []


# ---------------------------------------------------------------------------
# Entry point used by the DICOM watchdog
# ---------------------------------------------------------------------------
def push_to_cluster_and_submit(patient_folder_name=""):
    """Push a patient folder to the cluster and submit its jobs.
    Returns the list of submitted job IDs, or [] if anything failed.

    NOTE: this deliberately never calls sys.exit() -- it is imported and
    called by the long-running DICOM watchdog, and sys.exit() there would
    kill the whole monitor process."""
    if not patient_folder_name:
        print(" Error: no patient folder name given.")
        return []

    local_folder = Path(SOURCE_PATH) / patient_folder_name
    if not local_folder.exists():
        print(f" Error: patient folder not found: {local_folder}")
        return []

    print(f"Transferring: {local_folder}")
    print(f"To: {REMOTE_USER}@{REMOTE_HOST}:{REMOTE_PATH}")

    success = push_to_cluster(patient_folder_name)

    if not success:
        print(" Push failed -- NOT submitting jobs. "
              "Local folder left in place; fix the problem and retry.")
        return []

    print("Moved folder to cluster.")

    job_ids = ssh_to_cluster_and_submit_jobs(patient_folder_name)

    if not job_ids:
        print(" WARNING: transfer succeeded but job submission produced no job IDs.")
        print(f"          The data is on the cluster at {REMOTE_PATH}{patient_folder_name}")
        print("          and the local copy is archived in copied_to_cluster/.")
        print("          Submit manually or investigate before re-pushing.")

    return job_ids


if __name__ == "__main__":
    push_to_cluster_and_submit(patient_folder_name="zzzProtonPlanningBrain--test_brain_mc")