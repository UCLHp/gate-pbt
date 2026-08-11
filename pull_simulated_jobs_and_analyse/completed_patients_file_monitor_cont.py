import os
import stat
import subprocess
import time
import shutil
import re
import csv
from pathlib import Path
from typing import List, Tuple
from datetime import datetime

import paramiko


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REMOTE_USER = "uclh"
REMOTE_HOST = "10.140.79.159"
REMOTE_PATH = "/mnt/clustshare/"

# Credentials -- set in the .env file next to this script (loaded by
# `uv run --env-file .env`), or via setx:
#   CLUSTER_SSH_KEY  = path to private key (preferred), or
#   CLUSTER_PASSWORD = cluster password
SSH_KEY_FILE = os.environ.get("CLUSTER_SSH_KEY")
PASSWORD = os.environ.get("CLUSTER_PASSWORD")
print(PASSWORD, SSH_KEY_FILE)
# Network share root (analysis runs in place here; this build of the
# analysis exe writes to UNC paths fine -- proven over hundreds of plans).
SHARE_ROOT = Path(r"\\10.140.79.216\pbtmcdcm")

# Monitoring configuration
CHECK_INTERVAL_MINUTES = 20  # Check every 20 minutes (adjust as needed)

# A transient share/network hiccup makes the analysis exe fail once and
# succeed on the retry next cycle -- that's fine and handled automatically.
# But a genuinely broken plan would otherwise retry forever. After this many
# failed analysis attempts the plan is quarantined instead.
ANALYSIS_MAX_ATTEMPTS = 5

# Slurm states that mean the job finished but did NOT succeed
BAD_JOB_STATES = {
    "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY",
    "NODE_FAIL", "BOOT_FAIL", "DEADLINE", "PREEMPTED", "REVOKED",
}

# In-memory count of failed analysis attempts per patient folder name.
# Resets if the watchdog restarts (a restart grants a fresh set of retries).
_analysis_attempts = {}


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------
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
# Job-ticket parsing
# ---------------------------------------------------------------------------
def extract_job_ids_from_directory(
    directory_containing_text_file_with_submitted_plans: str,
) -> Tuple[List[Tuple[int, ...]], List[str]]:
    """
    Extract job IDs from all .txt files in the specified directory.

    Returns:
        - List of tuples, where each tuple contains job IDs from one .txt file
        - List of strings: the filenames (without _job_ids suffix / .txt extension)
    """
    job_ids_list = []
    filenames_list = []
    directory = Path(directory_containing_text_file_with_submitted_plans)

    if not directory.exists() or not directory.is_dir():
        return job_ids_list, filenames_list

    txt_files = sorted(directory.glob("*.txt"))
    job_id_pattern = re.compile(r"Job ID:\s*(\d+)")

    for txt_file in txt_files:
        try:
            with open(txt_file, "r", encoding="utf-8") as f:
                content = f.read()

            job_ids = tuple(int(m.group(1)) for m in job_id_pattern.finditer(content))

            if job_ids:
                job_ids_list.append(job_ids)

                filename = txt_file.stem
                if filename.endswith("_job_ids"):
                    filename = filename[:-8]
                filenames_list.append(filename)

        except (IOError, UnicodeDecodeError, ValueError) as e:
            print(f"Warning: Could not process {txt_file}: {e}")
            continue

    return job_ids_list, filenames_list


# ---------------------------------------------------------------------------
# Job status checking (squeue + sacct verification)
# ---------------------------------------------------------------------------
def _get_job_final_states(ssh, job_ids) -> dict:
    """
    Query sacct for the final state of the given job IDs.
    Returns {job_id: state_string}. Empty dict if sacct is unavailable
    (accounting disabled), in which case the caller falls back to
    trusting squeue alone.
    """
    states = {}
    if not job_ids:
        return states

    id_csv = ",".join(str(j) for j in sorted(job_ids))
    command = f"sacct -j {id_csv} -o JobID,State -n -P"
    try:
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode()
    except Exception as e:
        print(f"  Note: sacct query failed ({e}); trusting squeue only.")
        return states

    for line in output.strip().split("\n"):
        if not line.strip() or "|" not in line:
            continue
        jobid_field, state_field = line.split("|", 1)
        m = re.match(r"(\d+)", jobid_field.strip())
        if not m:
            continue
        base_id = int(m.group(1))
        state = state_field.strip().split()[0]  # "CANCELLED by 1234" -> "CANCELLED"
        if base_id in states and states[base_id] in BAD_JOB_STATES:
            continue
        states[base_id] = state

    return states


def check_if_simulations_complete(job_ids_list, filenames_list):
    """
    SSH into the cluster and determine, for each submitted plan, whether all
    of its Slurm jobs have finished.

    Returns:
        (completed_filenames, failed_filenames)
    """
    completed_filenames = []
    failed_filenames = []

    try:
        ssh = _ssh_connect()

        # --- 1) What is still running/pending? -----------------------------
        command = "squeue -u $USER -h -o '%i'"
        stdin, stdout, stderr = ssh.exec_command(command)
        squeue_output = stdout.read().decode()

        running_job_ids = set()
        for line in squeue_output.strip().split("\n"):
            if line.strip():
                m = re.match(r"(\d+)", line.strip())
                if m:
                    running_job_ids.add(int(m.group(1)))

        print(f"Currently running job IDs: {running_job_ids}")

        # --- 2) For jobs no longer in squeue, verify final state via sacct -
        finished_ids = set()
        for job_tuple in job_ids_list:
            for job_id in job_tuple:
                if job_id not in running_job_ids:
                    finished_ids.add(job_id)

        final_states = _get_job_final_states(ssh, finished_ids)
        if not final_states and finished_ids:
            print(
                "  Note: no sacct data available; assuming jobs absent from "
                "squeue completed successfully."
            )

        # --- 3) Classify each plan ------------------------------------------
        for filename, job_tuple in zip(filenames_list, job_ids_list):
            still_running = [j for j in job_tuple if j in running_job_ids]

            if still_running:
                print(f" Jobs still running for {filename}: {still_running}")
                continue

            bad_jobs = {
                j: final_states[j]
                for j in job_tuple
                if j in final_states and final_states[j] in BAD_JOB_STATES
            }

            if bad_jobs:
                print(f" Jobs FAILED for {filename}: {bad_jobs}")
                failed_filenames.append(filename)
            else:
                print(f" All jobs completed for: {filename}")
                completed_filenames.append(filename)

        ssh.close()

    except Exception as e:
        print(f" Failed to check job status: {e}")
        import traceback
        traceback.print_exc()

    return completed_filenames, failed_filenames


# ---------------------------------------------------------------------------
# SFTP transfer helpers
# ---------------------------------------------------------------------------
def _download_directory(sftp, remote_dir, local_dir):
    """
    Recursively download a directory via SFTP.

    Exceptions are deliberately allowed to PROPAGATE: if any file fails to
    transfer, the caller must know, because the remote copy is deleted only
    after a fully successful download.
    """
    os.makedirs(local_dir, exist_ok=True)

    for item in sftp.listdir_attr(remote_dir):
        remote_item = f"{remote_dir.rstrip('/')}/{item.filename}"
        local_item = os.path.join(local_dir, item.filename)

        if stat.S_ISDIR(item.st_mode):
            _download_directory(sftp, remote_item, local_item)
        else:
            sftp.get(remote_item, local_item)
            print(f"  Downloaded: {item.filename}")


def _delete_remote_directory(sftp, remote_dir):
    """Recursively delete a directory on the remote server via SFTP."""
    # Safety check: don't delete root-level paths
    if remote_dir.rstrip("/") in ["", "/mnt", "/mnt/clustshare"]:
        raise ValueError(f"Refusing to delete protected path: {remote_dir}")

    for item in sftp.listdir_attr(remote_dir):
        remote_item = f"{remote_dir.rstrip('/')}/{item.filename}"

        if stat.S_ISDIR(item.st_mode):
            _delete_remote_directory(sftp, remote_item)
        else:
            sftp.remove(remote_item)

    sftp.rmdir(remote_dir)


def pull_simulation_back(completed_simulations, directory_containing_completed_simulations):
    """
    Pull completed patient folders from the cluster back to the network share.
    The remote copy is deleted ONLY after the download completed without a
    single error, so a mid-transfer failure can never destroy the only copy.
    """
    if not completed_simulations:
        print("No completed simulations to pull back.")
        return

    os.makedirs(directory_containing_completed_simulations, exist_ok=True)

    try:
        ssh = _ssh_connect()
        sftp = ssh.open_sftp()

        for patient_folder_name in completed_simulations:
            remote_path = f"{REMOTE_PATH.rstrip('/')}/{patient_folder_name}"
            local_path = os.path.join(
                directory_containing_completed_simulations, patient_folder_name
            )

            print(f"\nDownloading: {patient_folder_name}")
            print(f"From: {remote_path}")
            print(f"To: {local_path}")

            try:
                sftp.stat(remote_path)
            except FileNotFoundError:
                print(f" Remote path not found: {remote_path}")
                continue

            try:
                _download_directory(sftp, remote_path, local_path)
                print(f" Folder downloaded successfully: {patient_folder_name}")
            except Exception as e:
                print(f" Download FAILED for {patient_folder_name}: {e}")
                print(f" Remote copy left intact; will retry next cycle.")
                continue

            try:
                _delete_remote_directory(sftp, remote_path)
                print(f" Deleted from remote: {patient_folder_name}")
            except Exception as e:
                print(f" Warning: Failed to delete remote folder {patient_folder_name}: {e}")

        sftp.close()
        ssh.close()

        print(f"\n Finished pulling {len(completed_simulations)} completed simulation(s)")

    except Exception as e:
        print(f" SFTP connection failed: {e}")
        import traceback
        traceback.print_exc()


# ---------------------------------------------------------------------------
# Analysis execution (in place on the share)
# ---------------------------------------------------------------------------
def run_analysis_exec(output_folder_string="", executable_path="") -> bool:
    """Run the analysis executable on the given output folder.
    Returns True on success, False on any failure."""
    try:
        result = subprocess.run(
            [str(executable_path), str(output_folder_string)],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("Executable completed successfully!")
            if result.stdout.strip():
                print(f"Output: {result.stdout}")
            return True
        else:
            print(f"Executable failed with return code: {result.returncode}")
            if result.stderr.strip():
                print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"Error running analysis executable: {e}")
        return False
        
        
        

def run_analysis_with_script(output_folder_string="") -> bool:
    """Run analysis.py directly."""
    import sys
    from pathlib import Path
    import subprocess
    
    """
    for this crap we have to add the gate-pbt env into the pull_simulated_jobs_and_analyse/ venv which is uv package managed
    after we fix the issues go back to run_analysis_exec and we can recreate the uv venv without itk etc. its in the pyproject.toml so read that
    """
    

    ANALYSIS_SCRIPT = Path(
        r"\\10.140.79.216\pbtmcdcm\gate-pbt-executable-code\gate-pbt-executable\gate-pbt\analysis\analysis.py"
    )
    try:
        
        proc = subprocess.Popen(
            [
                sys.executable,
                str(ANALYSIS_SCRIPT),
                str(output_folder_string),
            ],
            cwd=ANALYSIS_SCRIPT.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        for line in proc.stdout:
            print(line, end="")

        proc.wait()
        return proc.returncode == 0

                
        

    except Exception as e:
        print(f"Error running analysis: {e}")
        return False


def _quarantine_failed_analysis(patient_folder_source, text_file_source,
                                failed_analysis_dir, failed_jobs_text_dir, name):
    """A plan has exhausted its analysis retries. Move it out of the working
    directory so it stops being reprocessed, and retire its ticket."""
    os.makedirs(failed_analysis_dir, exist_ok=True)
    os.makedirs(failed_jobs_text_dir, exist_ok=True)

    print(f"  QUARANTINE: analysis for {name} failed {ANALYSIS_MAX_ATTEMPTS} times.")
    print(f"              Moving to {failed_analysis_dir} for manual investigation.")

    try:
        if patient_folder_source.exists():
            shutil.move(str(patient_folder_source), str(failed_analysis_dir / name))
    except Exception as e:
        print(f"  Could not quarantine patient folder {name}: {e}")

    try:
        if text_file_source.exists():
            shutil.move(str(text_file_source),
                        str(failed_jobs_text_dir / text_file_source.name))
    except Exception as e:
        print(f"  Could not retire ticket for {name}: {e}")


# ---------------------------------------------------------------------------
# CSV recording (with lock/failure fallbacks)
# ---------------------------------------------------------------------------
def _csv_append(path, headers, rows):
    """Append rows to a CSV, writing headers first if the file is new or empty.
    Raises OSError/PermissionError on failure so the caller can react."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not (path.exists() and path.stat().st_size > 0)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(headers)
        writer.writerows(rows)


def _write_gamma_rows(primary_path, headers, rows, label, max_retries=3, retry_delay=2):
    """Write rows to the primary CSV; on lock/error fall back so data is never lost.
    Returns the Path actually written to, or None if everything failed."""
    for attempt in range(1, max_retries + 1):
        try:
            _csv_append(primary_path, headers, rows)
            return primary_path
        except PermissionError:
            if attempt < max_retries:
                print(f"  CSV locked (open in Excel?). Retry {attempt}/{max_retries - 1} in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"  CSV still locked after {max_retries} attempts; using fallback.")
        except OSError as e:
            print(f"  Could not write to {primary_path}: {e}")
            break  # network/dir problem -> skip straight to fallback

    stamp = datetime.now().strftime("%Y%m%d")
    fallback = primary_path.with_name(f"{primary_path.stem}_fallback_{stamp}.csv")
    try:
        _csv_append(fallback, headers, rows)
        print(f"  WARNING: wrote {label} to FALLBACK file: {fallback.name}")
        print(f"           Merge it back into {primary_path.name} once that file is free.")
        return fallback
    except OSError:
        local = Path.cwd() / fallback.name
        try:
            _csv_append(local, headers, rows)
            print(f"  WARNING: network unreachable. Wrote {label} to LOCAL fallback: {local}")
            return local
        except OSError as e2:
            print(f"  ERROR: failed to record {label} anywhere: {e2}")
            return None


def append_to_spreadsheet(patient_folder):
    """
    Reads gamma values from a patient folder and appends them to the results CSV.
    One row per field. Recreates the CSV with headers if it doesn't exist,
    and falls back to a sidecar file if the CSV is locked or the share is down.
    Returns the Path written to, or None on total failure.
    """
    gamma_file = patient_folder / "output" / "gamma_values.txt"
    if not gamma_file.exists():
        print(f"  Warning: gamma_values.txt not found in {patient_folder}")
        return None

    with open(gamma_file, "r") as f:
        content = f.read()

    field_pattern = r"---\s*(\S+)\s*---"
    field_matches = list(re.finditer(field_pattern, content))
    if not field_matches:
        print(f"  Warning: No field sections found in gamma_values.txt")
        return None

    patterns = {
        "Gamma_33_GLOBAL": r"Gamma_33_GLOBAL\s*=\s*([\d.]+)",
        "Gamma_22_GLOBAL": r"Gamma_22_GLOBAL\s*=\s*([\d.]+)",
        "Gamma_33_LOCAL": r"Gamma_33_LOCAL\s*=\s*([\d.]+)",
        "Gamma_22_LOCAL": r"Gamma_22_LOCAL\s*=\s*([\d.]+)",
    }

    fields_data = []
    for i, match in enumerate(field_matches):
        field_name = match.group(1)
        start_pos = match.end()
        end_pos = field_matches[i + 1].start() if i + 1 < len(field_matches) else len(content)
        section = content[start_pos:end_pos]

        gamma_values = {}
        for key, pat in patterns.items():
            m = re.search(pat, section)
            if m:
                gamma_values[key] = float(m.group(1))
            else:
                print(f"  Warning: Could not find {key} for field {field_name}")
                gamma_values[key] = None

        fields_data.append({"field_name": field_name, "gamma_values": gamma_values})

    csv_path = SHARE_ROOT / "gamma_analysis_results.csv"
    headers = [
        "Patient Folder", "Field Name",
        "Gamma 3%3mm Global", "Gamma 2%2mm Global",
        "Gamma 3%3mm Local", "Gamma 2%2mm Local",
    ]

    patient_name = patient_folder.name
    rows = [
        [
            patient_name,
            fd["field_name"],
            fd["gamma_values"].get("Gamma_33_GLOBAL"),
            fd["gamma_values"].get("Gamma_22_GLOBAL"),
            fd["gamma_values"].get("Gamma_33_LOCAL"),
            fd["gamma_values"].get("Gamma_22_LOCAL"),
        ]
        for fd in fields_data
    ]

    written_to = _write_gamma_rows(csv_path, headers, rows, label=patient_name)
    if written_to:
        print(f"  Appended {len(rows)} field row(s) for {patient_name} to {written_to.name}")
    return written_to


# ---------------------------------------------------------------------------
# Main monitoring cycle
# ---------------------------------------------------------------------------
def monitor_for_completed_patient_folders(executable_path):
    """Single iteration of checking and processing completed jobs."""
    base_network_path = SHARE_ROOT / "pull_simulated_jobs_and_analyse"

    directory_containing_text_file_with_submitted_plans = base_network_path / "submitted_jobs"
    directory_containing_completed_simulations = base_network_path / "completed_patients"

    job_ids_list, filenames_list = extract_job_ids_from_directory(
        directory_containing_text_file_with_submitted_plans
    )

    if not job_ids_list:
        print("No pending jobs found in submitted_jobs directory.")
        return

    assert len(job_ids_list) == len(filenames_list)

    print("\n=== Submitted Jobs ===")
    for filename, job_tuple in zip(filenames_list, job_ids_list):
        print(f"{filename}: {job_tuple}")

    print("\n=== Checking Job Status ===")
    completed_simulations, failed_simulations = check_if_simulations_complete(
        job_ids_list, filenames_list
    )

    # Archive destinations
    completed_jobs_text_dir = directory_containing_text_file_with_submitted_plans / "completed_jobs_text"
    failed_jobs_text_dir = directory_containing_text_file_with_submitted_plans / "failed_jobs_text"
    analysed_completed_patients_dir = directory_containing_completed_simulations / "analysed_completed_patients"
    failed_analysis_dir = directory_containing_completed_simulations / "failed_analysis"
    os.makedirs(completed_jobs_text_dir, exist_ok=True)
    os.makedirs(analysed_completed_patients_dir, exist_ok=True)

    # ----------------------------------------------------------------------
    # Handle FAILED simulations: archive their tickets so they stop looping,
    # but leave the data on the cluster for manual inspection.
    # ----------------------------------------------------------------------
    if failed_simulations:
        os.makedirs(failed_jobs_text_dir, exist_ok=True)
        print("\n=== Failed Simulations ===")
        for name in failed_simulations:
            print(f" {name}: one or more Slurm jobs FAILED / TIMED OUT / were CANCELLED.")
            print(f"   Data left on the cluster at {REMOTE_PATH}{name} for inspection.")
            ticket = directory_containing_text_file_with_submitted_plans / f"{name}_job_ids.txt"
            try:
                if ticket.exists():
                    shutil.move(str(ticket), str(failed_jobs_text_dir / ticket.name))
                    print(f"   Ticket moved to failed_jobs_text/ -- resubmit when ready.")
            except Exception as e:
                print(f"   Could not archive failed ticket {ticket.name}: {e}")

    if not completed_simulations:
        print("No jobs completed successfully in this check cycle.")
        return

    print("\n=== Pulling Completed Simulations ===")
    pull_simulation_back(completed_simulations, directory_containing_completed_simulations)

    print("\n=== Running Analysis ===")

    for i in completed_simulations:
        patient_folder_source = directory_containing_completed_simulations / i
        output_folder = patient_folder_source / "output"

        text_file_name = f"{i}_job_ids.txt"
        text_file_source = directory_containing_text_file_with_submitted_plans / text_file_name
        text_file_dest = completed_jobs_text_dir / text_file_name

        if not output_folder.exists():
            print(f" Output folder not found for {i}: {output_folder}")
            # If the whole patient folder is gone, it was archived on an earlier
            # cycle but its text ticket lingered (e.g. a failed ticket move).
            # Archive the orphaned ticket so it stops being reconsidered forever.
            if not patient_folder_source.exists() and text_file_source.exists():
                try:
                    shutil.move(str(text_file_source), str(text_file_dest))
                    print(f"  Archived orphaned text ticket: {text_file_name}")
                except Exception as e:
                    print(f"  Could not archive orphaned ticket {text_file_name}: {e}")
            continue

        print(f"\nRunning analysis on: {i}")

        # ------------------------------------------------------------------
        # STEP 0 -- run the analysis in place on the share.
        # a plan that keeps failing is quarantined after ANALYSIS_MAX_ATTEMPTS
        # so it can't loop forever.
        # ------------------------------------------------------------------
        #analysis_ok = run_analysis_exec(output_folder, executable_path)
        
        analysis_ok = run_analysis_with_script(output_folder)
        
        
        if not analysis_ok:
            _analysis_attempts[i] = _analysis_attempts.get(i, 0) + 1
            attempts = _analysis_attempts[i]
            if attempts >= ANALYSIS_MAX_ATTEMPTS:
                _quarantine_failed_analysis(
                    patient_folder_source, text_file_source,
                    failed_analysis_dir, failed_jobs_text_dir, i,
                )
            else:
                print(f"  Analysis failed for {i} (attempt {attempts}/"
                      f"{ANALYSIS_MAX_ATTEMPTS}); leaving folder and text "
                      f"ticket in place to retry next cycle.")
            continue

        _analysis_attempts.pop(i, None)  # success -> clear any failure count

        # ------------------------------------------------------------------
        # STEP 1 -- record the gamma values FIRST.
        # Nothing is moved until this succeeds. So a locked/corrupt sheet
        # or a downed share simply leaves BOTH the patient folder and the text
        # ticket untouched: the next cycle retries cleanly, with no data loss
        # and (because nothing was written) no risk of a duplicate row.
        # ------------------------------------------------------------------
        recorded_to = append_to_spreadsheet(patient_folder_source)
        if recorded_to is None:
            print(f"  Could not record gamma values for {i}; "
                  f"leaving folder and text ticket in place to retry next cycle.")
            continue

        # ------------------------------------------------------------------
        # STEP 2 -- data is safely recorded. Move the patient FOLDER next.
        # With its output/ subfolder gone, the patient can't be re-analysed and
        # re-appended on a later cycle even if archiving the ticket below fails.
        # This is the main guard against duplicate rows.
        # ------------------------------------------------------------------
        folder_moved = False
        try:
            if patient_folder_source.exists():
                shutil.move(str(patient_folder_source), str(analysed_completed_patients_dir / i))
                print(f"  Moved patient folder: {i} > analysed_completed_patients/")
            folder_moved = True  # treat "already gone" as moved
        except Exception as e:
            print(f"  WARNING: gamma values for {i} recorded in {recorded_to.name}, "
                  f"but the patient folder could not be moved: {e}")
            print(f"           Move {patient_folder_source} manually when convenient.")

        # ------------------------------------------------------------------
        # STEP 3 -- retire the text ticket. If the folder move FAILED above,
        # retiring the ticket is what stops the patient being reprocessed (and
        # re-appended) next cycle, so it matters most in exactly that case.
        # ------------------------------------------------------------------
        try:
            if text_file_source.exists():
                shutil.move(str(text_file_source), str(text_file_dest))
                print(f"  Moved text file: {text_file_name} > completed_jobs_text/")
            else:
                print(f"  Text file not found (already archived?): {text_file_name}")
        except Exception as e:
            print(f"  WARNING: could not archive text ticket {text_file_name}: {e}")
            if not folder_moved:
                print(f"           Both moves failed for {i}; the next cycle may "
                      f"re-record it (one duplicate row at worst). Resolve manually.")

    return


def continuous_monitor(executable_path, check_interval_minutes=CHECK_INTERVAL_MINUTES):
    """
    Continuously monitor for completed jobs at regular intervals.
    """
    print("=" * 60)
    print(f"Starting continuous monitoring")
    print(f"Check interval: {check_interval_minutes} minutes")
    print(f"Press Ctrl+C to stop")
    print("=" * 60)

    try:
        while True:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'=' * 60}")
            print(f"Check cycle started at: {timestamp}")
            print(f"{'=' * 60}")

            try:
                monitor_for_completed_patient_folders(executable_path)
            except Exception as e:
                print(f" Error during monitoring cycle: {e}")
                import traceback
                traceback.print_exc()

            next_check = datetime.now().timestamp() + (check_interval_minutes * 60)
            next_check_time = datetime.fromtimestamp(next_check).strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n{'=' * 60}")
            print(f"Waiting {check_interval_minutes} minutes...")
            print(f"Next check at: {next_check_time}")
            print(f"{'=' * 60}")

            time.sleep(check_interval_minutes * 60)

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("Monitoring stopped by user")
        print("=" * 60)


if __name__ == "__main__":
    EXECUTABLE_PATH = "./analysis.exe"
    
    expected = "pull_simulated_jobs_and_analyse"
    if Path.cwd().name != expected:
        sys.exit(f"FATAL: cwd is {Path.cwd()}, expected to be inside {expected}")

    # Option 1: Run once
    # monitor_for_completed_patient_folders(EXECUTABLE_PATH)

    # Option 2: Run continuously every N minutes
    continuous_monitor(EXECUTABLE_PATH, check_interval_minutes=CHECK_INTERVAL_MINUTES)