import os
import sys
import subprocess
import time
import shutil
from pathlib import Path
from collections import deque
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from push_to_cluster import push_to_cluster_and_submit

class RandomFolderHandler(FileSystemEventHandler):
    def __init__(self, executable_path, dicom_folder_name="dicom_data"):
        self.executable_path = Path(executable_path)
        self.dicom_folder_name = dicom_folder_name
        self.base_path = Path.cwd()
        self.parent_path = self.base_path.parent
        self.folders_queue = deque()
        
        # ========== Define gate_ready_folder as instance variable ==========
        self.gate_ready_folder = self.base_path / "data" / "simulationfiles"
        # ========================================================================

    def _get_clean_folder_name(self, folder_path):
        """Replace all full stops in the folder name with underscores."""
        folder_name = folder_path.name
        clean_name = folder_name.replace('.', '_')
        print(f"   Converting folder name: '{folder_name}' -> '{clean_name}'")
        return clean_name

    # ========== HELPER METHOD ==========
    def _get_patient_folders_in_gate_ready(self):
        """
        Get list of patient folders in gate_ready_folder, excluding 
        'copied_to_cluster' and 'failed_simulations' directories.
        """
        if not self.gate_ready_folder.exists():
            return []
        
        excluded_folders = {"copied_to_cluster", "failed_simulations"}
        patient_folders = [
            f for f in self.gate_ready_folder.iterdir() 
            if f.is_dir() and f.name not in excluded_folders
        ]
        return patient_folders
    # ========================================

    # ========== HELPER METHOD ==========
    def _move_stale_folders_to_failed(self):
        """
        Check for any leftover patient folders in gate_ready_folder before 
        running the executable. These are from previous failed runs.
        Move them to 'failed_simulations' folder.
        """
        stale_folders = self._get_patient_folders_in_gate_ready()
        
        if not stale_folders:
            print("   No stale folders found in gate_ready_folder. Proceeding.")
            return
        
        # Create failed_simulations directory if it doesn't exist
        failed_simulations_dir = self.gate_ready_folder / "failed_simulations"
        failed_simulations_dir.mkdir(parents=True, exist_ok=True)
        
        for folder in stale_folders:
            timestamp = int(time.time())
            # Add timestamp to avoid name collisions
            dest_name = f"{folder.name}_failed_{timestamp}"
            dest_path = failed_simulations_dir / dest_name
            
            try:
                shutil.move(str(folder), str(dest_path))
                print(f"   Moved stale/failed folder: {folder.name} -> {dest_path}")
            except Exception as e:
                print(f"   Error moving stale folder {folder.name}: {e}")
    # ========================================

    def on_created(self, event):
        if event.is_directory:
            self._check_and_add_folder(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            self._check_and_add_folder(event.dest_path)

    def _check_and_add_folder(self, path):
        folder_path = Path(path)
        if not folder_path.exists() or not folder_path.is_dir():
            return

        if folder_path.name.isdigit():
            print(f"New numeric folder detected: {folder_path}")
            for uid_folder in folder_path.iterdir():
                if uid_folder.is_dir():
                    print(f"   Queuing UID folder: {uid_folder}")
                    self.folders_queue.append((time.time(), uid_folder))
        else:
            print(f"Ignored non-numeric folder: {folder_path.name}")

    def update_and_process_ready_folders(self):
        """Check if any folders have been waiting > 180 seconds, then process them."""
        now = time.time()
        while self.folders_queue and now - self.folders_queue[0][0] >= 360:
            _, folder_path = self.folders_queue.popleft()
            try:
                self.handle_ready_folder(folder_path)
            except Exception as e:
                print(f"Error processing folder {folder_path}: {e}")

    def handle_ready_folder(self, folder_path):
        """Move UID folder, then run executable."""
        print(f"Processing new upload: {folder_path}")

        clean_folder_name = self._get_clean_folder_name(folder_path)
        
        base_export_dir = self.base_path / "exported_patient_data"
        uid_dir = base_export_dir / clean_folder_name
        dicom_data_dir = uid_dir / self.dicom_folder_name
        
        dicom_data_dir.mkdir(parents=True, exist_ok=True)
        
        def has_dcm_files(folder):
            """Check if a folder contains any .dcm files."""
            return any(f.suffix.lower() == '.dcm' for f in folder.iterdir() if f.is_file())

        source_uid_folder = folder_path
        for root, dirs, files in os.walk(source_uid_folder):
            for file in files:
                if file.lower().endswith('.dcm'):
                    source_path = os.path.join(root, file)
                    dest_path = os.path.join(dicom_data_dir, file)
                    shutil.move(source_path, dest_path)
        
        try:
            shutil.rmtree(folder_path)
            print(f"Deleted original folder and all remaining contents: {folder_path}")
        except Exception as e:
            print(f"Could not delete folder {folder_path}: {e}")

        self.process_dicom_folder(uid_dir)

    def process_dicom_folder(self, dicom_folder_path):
        """Run the executable on the UID folder."""
        try:
            print(f"Processing DICOM folder: {dicom_folder_path}")
            original_cwd = os.getcwd()
            print('original cwd', original_cwd)
            print('exec path parent ', self.executable_path.parent)

            # ========== Clean up stale folders BEFORE running executable ==========
            print("Checking for stale/failed folders from previous runs...")
            self._move_stale_folders_to_failed()
            # ===========================================================================

            os.chdir(self.executable_path.parent)            

            dicom_data_dir = dicom_folder_path / "dicom_data"

            print(f" Running {self.executable_path} with DICOM dir: {dicom_data_dir}")

            result = subprocess.run(
                [str(self.executable_path), str(dicom_data_dir)],
                capture_output=True,
                text=True
            )

            os.chdir(original_cwd)

            if result.returncode == 0:
                print("Executable completed successfully!")
                if result.stdout.strip():
                    print(f"Output: {result.stdout}")
            else:
                print(f"Executable failed with return code: {result.returncode}")
                if result.stderr.strip():
                    print(f"Error: {result.stderr}")
                # ========== Don't return yet - let the cleanup happen ==========
                # The folder will be picked up as "stale" on the next run
                # But we still want to move the processed folder
                self.move_processed_folder(dicom_folder_path)
                return
                # =====================================================================

            self.move_processed_folder(dicom_folder_path)

            # ========== MODIFIED: Use helper method and updated logic ==========
            patient_folders = self._get_patient_folders_in_gate_ready()

            if len(patient_folders) == 1:
                folder_name = patient_folders[0].name
                print(f"Found patient folder to push: {folder_name}")
                push_to_cluster_and_submit(folder_name)
            elif len(patient_folders) == 0:
                raise FileNotFoundError(f"No patient folder found in {self.gate_ready_folder}")
            else:
                # This shouldn't happen now since we clean up stale folders beforehand
                # But keeping as a safety check
                raise ValueError(
                    f"Multiple patient folders found in {self.gate_ready_folder}: "
                    f"{[f.name for f in patient_folders]}. "
                    "This is unexpected - stale folders should have been moved."
                )
            # ===================================================================

        except Exception as e:
            print(f"Error processing DICOM folder: {e}")

    def move_processed_folder(self, dicom_folder_path):
        """Rename/move the processed folder."""
        try:
            timestamp = int(time.time())
            done_folder_name = f"{dicom_folder_path.name}_done_{timestamp}"
            done_folder_path = dicom_folder_path.parent / "completed_patient_files" / done_folder_name
            done_folder_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent exists
            shutil.move(str(dicom_folder_path), str(done_folder_path))
            print(f"Moved processed folder: {dicom_folder_path} -> {done_folder_path}")
        except Exception as e:
            print(f"Error moving processed folder: {e}")

    def poll_for_new_folders(self):
        for folder_path in self.parent_path.iterdir():
            if folder_path.is_dir() and folder_path.name.isdigit():
                for uid_folder in folder_path.iterdir():
                    if uid_folder.is_dir() and not any(uid_folder == f[1] for f in self.folders_queue):
                        print(f" Poller detected new UID folder: {uid_folder}")
                        self.folders_queue.append((time.time(), uid_folder))

def monitor_for_random_folders(executable_path, dicom_folder_name="dicom_data"):
    executable = Path(executable_path)
    current_dir = Path.cwd()
    parent_dir = current_dir.parent

    if not executable.exists():
        print(f"Error: Executable does not exist: {executable}")
        return

    print(f"Monitoring directory: {parent_dir}")
    print(f"Executable path: {executable}")

    event_handler = RandomFolderHandler(executable_path, dicom_folder_name)

    observer = Observer()
    observer.schedule(event_handler, str(parent_dir), recursive=False)
    observer.start()

    print("Waiting for numeric folders to appear...")
    print("Press Ctrl+C to stop monitoring")

    try:
        while True:
            time.sleep(1)
            event_handler.poll_for_new_folders()
            event_handler.update_and_process_ready_folders()
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        observer.stop()

    observer.join()

if __name__ == "__main__":
    EXECUTABLE_PATH = "./run.exe"
    DICOM_FOLDER_NAME = "dicom_data"

    if len(sys.argv) >= 2:
        EXECUTABLE_PATH = sys.argv[1]
    if len(sys.argv) >= 3:
        DICOM_FOLDER_NAME = sys.argv[2]

    print("=== DICOM Folder Monitor ===")
    print("This script will:")
    print("1. Monitor the parent directory for numeric folders")
    print(f"2. Move them into 'get_gate_ready_files/exported_patient_data/<UID>/{DICOM_FOLDER_NAME}'")
    print("3. Run the executable on UID folder")
    print("4. Rename processed folders")
    print()

    monitor_for_random_folders(EXECUTABLE_PATH, DICOM_FOLDER_NAME)