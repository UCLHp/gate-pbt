import os
import sys
import subprocess
import time
import shutil
from pathlib import Path
from collections import deque
import re
from pathlib import Path
from typing import List, Tuple
import paramiko
from datetime import datetime
import openpyxl




# Configuration (matching the push script)
REMOTE_USER = "uclh"
REMOTE_HOST = "10.140.79.159"
REMOTE_PATH = "/mnt/clustshare/"
PASSWORD = "vir7ual"

# Monitoring configuration
CHECK_INTERVAL_MINUTES = 20  # Check every 5 minutes (adjust as needed)


def extract_job_ids_from_directory(directory_containing_text_file_with_submitted_plans: str) -> Tuple[List[Tuple[int, ...]], List[str]]:
    """
    Extract job IDs from all .txt files in the specified directory.
    
    Args:
        directory_containing_text_file_with_submitted_plans: Path to directory containing .txt files
        
    Returns:
        Tuple containing:
        - List of tuples, where each tuple contains job IDs from one .txt file
        - List of strings, where each string is the filename (without _job_ids suffix and .txt extension)
        
        Example: ([(18276, 18301, 18302), (18303, 18304)], 
                  ['plan_name_1', 'plan_name_2'])
    """
    job_ids_list = []
    filenames_list = []
    directory = Path(directory_containing_text_file_with_submitted_plans)
    
    # Check if directory exists
    if not directory.exists() or not directory.is_dir():
        return job_ids_list, filenames_list
    
    # Find all .txt files in directory
    txt_files = sorted(directory.glob("*.txt"))
    
    # Pattern to match "Job ID: <number>"
    job_id_pattern = re.compile(r'Job ID:\s*(\d+)')
    
    for txt_file in txt_files:
        try:
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Extract all job IDs from the file
            job_ids = tuple(int(match.group(1)) for match in job_id_pattern.finditer(content))
            
            # Only append non-empty tuples
            if job_ids:
                job_ids_list.append(job_ids)
                
                # Extract filename without extension and remove _job_ids suffix
                filename = txt_file.stem  # Gets filename without .txt extension
                if filename.endswith('_job_ids'):
                    filename = filename[:-8]  # Remove '_job_ids' (8 characters)
                
                filenames_list.append(filename)
                
        except (IOError, UnicodeDecodeError, ValueError) as e:
            # Log error and continue processing other files
            print(f"Warning: Could not process {txt_file}: {e}")
            continue
    
    return job_ids_list, filenames_list


def check_if_simulations_complete(job_ids_list, filenames_list):
    '''
    ssh into the cluster, run squeue and list all still running job ids
    collect these job ids into a useful list of still running ids, note the job ids get additional aspects e.g. <job_id>_1 if slurm has split a job id over multiple nodes.
    just take the <job_id> bit. you now have a list of pure running ids. 
    loop over the list of job_ids (recall each element is a tuple (job_id1, job_id2, ...)) and if there are no job ids in the list of running, then this job is completed, return the filename associated from filenames_list

    iterate over entire job_ids_list and (filenames_list) and return the list of completed filenames_list
    '''
    
    completed_filenames = []
    
    try:
        # Create SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=REMOTE_HOST,
            username=REMOTE_USER,
            password=PASSWORD,
            look_for_keys=False,
            allow_agent=False
        )
        
        # Run squeue to get all running jobs for this user
        command = "squeue -u $USER -h -o '%i'"  # -h removes header, -o '%i' shows only job IDs
        stdin, stdout, stderr = ssh.exec_command(command)
        
        squeue_output = stdout.read().decode()
        
        # Extract pure job IDs from squeue output
        # Job IDs might appear as "12345" or "12345_1" (array jobs), we only want the base number
        running_job_ids = set()
        for line in squeue_output.strip().split('\n'):
            if line.strip():
                # Extract the base job ID (before any underscore)
                match = re.match(r'(\d+)', line.strip())
                if match:
                    running_job_ids.add(int(match.group(1)))
        
        print(f"Currently running job IDs: {running_job_ids}")
        
        # Check each set of job IDs against running jobs
        for filename, job_tuple in zip(filenames_list, job_ids_list):
            # Check if any job in this tuple is still running
            any_running = any(job_id in running_job_ids for job_id in job_tuple)
            
            if not any_running:
                print(f" All jobs completed for: {filename}")
                completed_filenames.append(filename)
            else:
                still_running = [job_id for job_id in job_tuple if job_id in running_job_ids]
                print(f" Jobs still running for {filename}: {still_running}")
        
        ssh.close()
        
    except Exception as e:
        print(f" Failed to check job status: {e}")
        import traceback
        traceback.print_exc()
    
    return completed_filenames


def _download_directory(sftp, remote_dir, local_dir):
    """Recursively download a directory via SFTP (reverse of _transfer_directory)"""
    
    # Create local directory if it doesn't exist
    os.makedirs(local_dir, exist_ok=True)
    
    try:
        # List all items in remote directory
        items = sftp.listdir_attr(remote_dir)
        
        for item in items:
            remote_item = os.path.join(remote_dir, item.filename).replace('\\', '/')
            local_item = os.path.join(local_dir, item.filename)
            
            # Check if item is a directory (using st_mode)
            import stat
            if stat.S_ISDIR(item.st_mode):
                # Recursively download subdirectory
                _download_directory(sftp, remote_item, local_item)
            else:
                # Download file
                sftp.get(remote_item, local_item)
                print(f"  Downloaded: {item.filename}")
                
    except Exception as e:
        print(f"Error downloading from {remote_dir}: {e}")


def pull_simulation_back(completed_simulations, directory_containing_completed_simulations):
    '''
    pull completed files from filenames_list back to server into directory_containing_completed_simulations

    use the same ssh format used in the pushing script provided for context
    '''
    
    if not completed_simulations:
        print("No completed simulations to pull back.")
        return
    
    # Ensure the local directory exists
    os.makedirs(directory_containing_completed_simulations, exist_ok=True)
    
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
        
        # Download each completed simulation
        for patient_folder_name in completed_simulations:
            remote_path = os.path.join(REMOTE_PATH, patient_folder_name).replace('\\', '/')
            local_path = os.path.join(directory_containing_completed_simulations, patient_folder_name)
            
            print(f"\nDownloading: {patient_folder_name}")
            print(f"From: {remote_path}")
            print(f"To: {local_path}")
            
            try:
                # Check if remote path exists and is a directory
                try:
                    sftp.stat(remote_path)
                    # Download directory recursively
                    _download_directory(sftp, remote_path, local_path)
                    print(f" Folder downloaded successfully: {patient_folder_name}")

                    try:
                        _delete_remote_directory(sftp, remote_path)
                        print(f" Deleted from remote: {patient_folder_name}")
                    except Exception as e:
                        print(f" Warning: Failed to delete remote folder {patient_folder_name}: {e}")
                    
                except FileNotFoundError:
                    print(f" Remote path not found: {remote_path}")
                    continue
                    
            except Exception as e:
                print(f" Failed to download {patient_folder_name}: {e}")
                continue
        
        sftp.close()
        ssh.close()
        
        print(f"\n Successfully pulled {len(completed_simulations)} completed simulation(s)")
        
    except Exception as e:
        print(f" SFTP connection failed: {e}")
        import traceback
        traceback.print_exc()


def _delete_remote_directory(sftp, remote_dir):
    """Recursively delete a directory on the remote server via SFTP"""
    import stat
    
    # Safety check: don't delete root-level paths
    if remote_dir.rstrip('/') in ['', '/mnt', '/mnt/clustshare']:
        raise ValueError(f"Refusing to delete protected path: {remote_dir}")
    
    try:
        items = sftp.listdir_attr(remote_dir)
        
        for item in items:
            remote_item = os.path.join(remote_dir, item.filename).replace('\\', '/')
            
            if stat.S_ISDIR(item.st_mode):
                # Recursively delete subdirectory
                _delete_remote_directory(sftp, remote_item)
            else:
                # Delete file
                sftp.remove(remote_item)
        
        # After all contents deleted, remove the now-empty directory
        sftp.rmdir(remote_dir)
        
    except Exception as e:
        print(f"Error deleting remote directory {remote_dir}: {e}")
        raise


def run_analysis_exec(output_folder_string="", executable_path=""):
    """Run the executable on the UID folder."""
    try:
        result = subprocess.run(
            [str(executable_path), str(output_folder_string)],  # pass explicit path
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Executable completed successfully!")
            if result.stdout.strip():
                print(f"Output: {result.stdout}")
        else:
            print(f"Executable failed with return code: {result.returncode}")
            if result.stderr.strip():
                print(f"Error: {result.stderr}")
            return
    except Exception as e:
            print(f"Error processing DICOM folder: {e}")


def append_to_spreadsheet(patient_folder):
    """
    Reads gamma values from patient folder and appends them to Excel spreadsheet.
    Handles multiple fields per patient, creating one row per field.
    
    Args:
        patient_folder: Path object pointing to the patient folder
    """
    # Read gamma values from text file
    gamma_file = patient_folder / "output" / "gamma_values.txt"
    
    if not gamma_file.exists():
        print(f"  Warning: gamma_values.txt not found in {patient_folder}")
        return
    
    # Parse the gamma values - now handling multiple fields
    with open(gamma_file, 'r') as f:
        content = f.read()
    
    # Split content by field sections (--- FIELD_NAME ---)
    field_pattern = r'---\s*(\S+)\s*---'
    
    # Find all field sections
    field_matches = list(re.finditer(field_pattern, content))
    
    if not field_matches:
        print(f"  Warning: No field sections found in gamma_values.txt")
        return
    
    # Parse each field section
    fields_data = []
    for i, match in enumerate(field_matches):
        field_name = match.group(1)
        
        # Get the content between this field header and the next (or end of file)
        start_pos = match.end()
        end_pos = field_matches[i + 1].start() if i + 1 < len(field_matches) else len(content)
        section_content = content[start_pos:end_pos]
        
        # Extract gamma values from this section
        gamma_values = {}
        patterns = {
            'Gamma_33_GLOBAL': r'Gamma_33_GLOBAL\s*=\s*([\d.]+)',
            'Gamma_22_GLOBAL': r'Gamma_22_GLOBAL\s*=\s*([\d.]+)',
            'Gamma_33_LOCAL': r'Gamma_33_LOCAL\s*=\s*([\d.]+)',
            'Gamma_22_LOCAL': r'Gamma_22_LOCAL\s*=\s*([\d.]+)'
        }
        
        for key, pattern in patterns.items():
            match_val = re.search(pattern, section_content)
            if match_val:
                gamma_values[key] = float(match_val.group(1))
            else:
                print(f"  Warning: Could not find {key} for field {field_name}")
                gamma_values[key] = None
        
        fields_data.append({
            'field_name': field_name,
            'gamma_values': gamma_values
        })
    
    # Path to Excel spreadsheet on network
    excel_path = Path(r"\\10.140.79.216\pbtmcdcm\gamma_results.xlsx")
    excel_dir = excel_path.parent
    if not excel_dir.exists():
        print(f"  Error: Network directory not accessible: {excel_dir}")
        print(f"  Please ensure network share is mounted")
        return
    
    try:
        # Try to open existing workbook
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
    except FileNotFoundError:
        # Create new workbook if it doesn't exist
        wb = openpyxl.Workbook()
        ws = wb.active
        
        # Add headers - now including Field Name
        ws.append([
            "Patient Folder",
            "Field Name",
            "Gamma 3%3mm Global",
            "Gamma 2%2mm Global",
            "Gamma 3%3mm Local",
            "Gamma 2%2mm Local"
        ])
    
    # Append a row for each field
    patient_folder_name = patient_folder.name
    for field_data in fields_data:
        ws.append([
            patient_folder_name,
            field_data['field_name'],
            field_data['gamma_values'].get('Gamma_33_GLOBAL'),
            field_data['gamma_values'].get('Gamma_22_GLOBAL'),
            field_data['gamma_values'].get('Gamma_33_LOCAL'),
            field_data['gamma_values'].get('Gamma_22_LOCAL')
        ])
    
    # Save the workbook
    wb.save(excel_path)
    print(f"  Appended gamma values for {patient_folder_name} ({len(fields_data)} fields) to spreadsheet")

def monitor_for_completed_patient_folders(executable_path):
    """Single iteration of checking and processing completed jobs"""
    executable = Path(executable_path)
    current_dir = Path.cwd()
    parent_dir = current_dir.parent

    base_network_path = Path(r"\\10.140.79.216\pbtmcdcm\pull_simulated_jobs_and_analyse")
    
    directory_containing_text_file_with_submitted_plans = base_network_path / "submitted_jobs"
    directory_containing_completed_simulations = base_network_path / "completed_patients"

    # Call the function
    job_ids_list, filenames_list = extract_job_ids_from_directory(directory_containing_text_file_with_submitted_plans)

    if not job_ids_list:
        print("No pending jobs found in submitted_jobs directory.")
        return

    # Both lists have the same length
    assert len(job_ids_list) == len(filenames_list)

    # Access corresponding data
    print("\n=== Submitted Jobs ===")
    for filename, job_tuple in zip(filenames_list, job_ids_list):
        print(f"{filename}: {job_tuple}")

    print("\n=== Checking Job Status ===")
    completed_simulations = check_if_simulations_complete(job_ids_list, filenames_list)  # cross checking with squeue

    if not completed_simulations:
        print("No jobs completed in this check cycle.")
        return

    print("\n=== Pulling Completed Simulations ===")
    pull_simulation_back(completed_simulations, directory_containing_completed_simulations)  # list of completed filenames ['patient_folder_1', 'patient_folder_2', ...]

    print("\n=== Running Analysis ===")
    
    # Create destination directories if they don't exist
    completed_jobs_text_dir = directory_containing_text_file_with_submitted_plans / "completed_jobs_text"
    analysed_completed_patients_dir = directory_containing_completed_simulations / "analysed_completed_patients"
    os.makedirs(completed_jobs_text_dir, exist_ok=True)
    os.makedirs(analysed_completed_patients_dir, exist_ok=True)
    
    for i in completed_simulations:
        output_folder_string = directory_containing_completed_simulations / i / "output"
        if output_folder_string.exists():
            print(f"\nRunning analysis on: {i}")

            
            run_analysis_exec(output_folder_string, executable_path)
            
            # After successful analysis, move files to archive locations
            try:
                # 1. Move the text file from submitted_jobs to completed_jobs_text
                text_file_name = f"{i}_job_ids.txt"
                text_file_source = directory_containing_text_file_with_submitted_plans / text_file_name
                text_file_dest = completed_jobs_text_dir / text_file_name
                
                if text_file_source.exists():
                    shutil.move(str(text_file_source), str(text_file_dest))
                    print(f"  Moved text file: {text_file_name} > completed_jobs_text/")
                else:
                    print(f"  Text file not found: {text_file_name}")


                
                
                # 2. Move the patient folder from completed_patients to analysed_completed_patients
                patient_folder_source = directory_containing_completed_simulations / i
                patient_folder_dest = analysed_completed_patients_dir / i

                ### SOME FUNCTION TO APPEND TO AN EXCEL SPREADSHEET
                append_to_spreadsheet(patient_folder_source)
                
                if patient_folder_source.exists():
                    shutil.move(str(patient_folder_source), str(patient_folder_dest))
                    print(f"  Moved patient folder: {i} > analysed_completed_patients/")
                else:
                    print(f"  Patient folder not found: {i}")
                    
                

                


            except Exception as e:
                print(f"  Error moving files for {i}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f" Output folder not found for {i}: {output_folder_string}")

    return


def continuous_monitor(executable_path, check_interval_minutes=CHECK_INTERVAL_MINUTES):
    """
    Continuously monitor for completed jobs at regular intervals.
    
    Args:
        executable_path: Path to the analysis executable
        check_interval_minutes: How often to check (in minutes)
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
            
            # Wait for the specified interval
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
    
    # You can choose between single run or continuous monitoring:
    
    # Option 1: Run once (original behavior)
    # monitor_for_completed_patient_folders(EXECUTABLE_PATH)
    
    # Option 2: Run continuously every N minutes
    continuous_monitor(EXECUTABLE_PATH, check_interval_minutes=CHECK_INTERVAL_MINUTES)  # Check every N minutes