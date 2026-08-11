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
import traceback


# How long a newly detected UID folder must sit untouched before we process it
# (gives the exporting system time to finish writing files).
SETTLE_SECONDS = 360

# How many times we retry a UID folder whose processing crashed before giving
# up on it. Prevents the poller from re-queuing a broken folder forever.
MAX_ATTEMPTS = 3


class RandomFolderHandler(FileSystemEventHandler):
    def __init__(self, executable_path, dicom_folder_name="dicom_data"):
        self.executable_path = Path(executable_path)
        self.dicom_folder_name = dicom_folder_name
        self.base_path = Path.cwd()
        self.parent_path = self.base_path.parent
        self.folders_queue = deque()

        # Tracks how many times processing each UID folder has been ATTEMPTED,
        # keyed by absolute path string. Folders that hit MAX_ATTEMPTS are
        # abandoned (with a loud message) instead of looping forever.
        self.attempt_counts = {}
        self.abandoned = set()

        self.gate_ready_folder = self.base_path / "data" / "simulationfiles"

    # ------------------------------------------------------------------
    # Small helpers
    # ------------------------------------------------------------------
    def _get_clean_folder_name(self, folder_path):
        """Replace all full stops in the folder name with underscores."""
        folder_name = folder_path.name
        clean_name = folder_name.replace('.', '_')
        print(f"   Converting folder name: '{folder_name}' -> '{clean_name}'")
        return clean_name

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

        failed_simulations_dir = self.gate_ready_folder / "failed_simulations"
        failed_simulations_dir.mkdir(parents=True, exist_ok=True)

        for folder in stale_folders:
            timestamp = int(time.time())
            dest_name = f"{folder.name}_failed_{timestamp}"
            dest_path = failed_simulations_dir / dest_name

            try:
                shutil.move(str(folder), str(dest_path))
                print(f"   Moved stale/failed folder: {folder.name} -> {dest_path}")
            except Exception as e:
                print(f"   Error moving stale folder {folder.name}: {e}")

    # ------------------------------------------------------------------
    # Queueing (event-driven + polled)
    # ------------------------------------------------------------------
    def on_created(self, event):
        if event.is_directory:
            self._check_and_add_folder(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            self._check_and_add_folder(event.dest_path)

    def _queue_uid_folder(self, uid_folder: Path):
        """Add a UID folder to the queue unless it is already queued,
        already abandoned, or out of retry attempts."""
        key = str(uid_folder.resolve())

        if key in self.abandoned:
            return
        if any(uid_folder == f[1] for f in self.folders_queue):
            return
        if self.attempt_counts.get(key, 0) >= MAX_ATTEMPTS:
            self.abandoned.add(key)
            print(f"   GIVING UP on {uid_folder.name} after {MAX_ATTEMPTS} failed "
                  f"attempts. Investigate and remove/fix the folder manually:")
            print(f"     {uid_folder}")
            return

        print(f"   Queuing UID folder: {uid_folder}")
        self.folders_queue.append((time.time(), uid_folder))

    def _check_and_add_folder(self, path):
        folder_path = Path(path)
        if not folder_path.exists() or not folder_path.is_dir():
            return

        if folder_path.name.isdigit():
            print(f"New numeric folder detected: {folder_path}")
            for uid_folder in folder_path.iterdir():
                if uid_folder.is_dir():
                    self._queue_uid_folder(uid_folder)
        else:
            print(f"Ignored non-numeric folder: {folder_path.name}")

    def poll_for_new_folders(self):
        for folder_path in self.parent_path.iterdir():
            if folder_path.is_dir() and folder_path.name.isdigit():
                for uid_folder in folder_path.iterdir():
                    if uid_folder.is_dir():
                        self._queue_uid_folder(uid_folder)

    def update_and_process_ready_folders(self):
        """Process any queued folders that have been waiting > SETTLE_SECONDS."""
        now = time.time()
        while self.folders_queue and now - self.folders_queue[0][0] >= SETTLE_SECONDS:
            _, folder_path = self.folders_queue.popleft()
            key = str(folder_path.resolve())
            self.attempt_counts[key] = self.attempt_counts.get(key, 0) + 1
            try:
                self.handle_ready_folder(folder_path)
            except Exception as e:
                attempts = self.attempt_counts[key]
                print(f"Error processing folder {folder_path} "
                      f"(attempt {attempts}/{MAX_ATTEMPTS}): {e}")
                # If the folder still exists, the poller will re-queue it and
                # it gets another settle period before the next attempt.
                # Once attempts reach MAX_ATTEMPTS, _queue_uid_folder refuses
                # it and it is abandoned with a warning.

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    def handle_ready_folder(self, folder_path):
        """Move UID folder, then run executable."""
        print(f"Processing new upload: {folder_path}")

        clean_folder_name = self._get_clean_folder_name(folder_path)

        base_export_dir = self.base_path / "exported_patient_data"
        uid_dir = base_export_dir / clean_folder_name
        dicom_data_dir = uid_dir / self.dicom_folder_name

        dicom_data_dir.mkdir(parents=True, exist_ok=True)

        for root, dirs, files in os.walk(folder_path):
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

            # Clean up stale folders BEFORE running executable
            print("Checking for stale/failed folders from previous runs...")
            self._move_stale_folders_to_failed()

            dicom_data_dir = dicom_folder_path / self.dicom_folder_name

            print(f" Running {self.executable_path} with DICOM dir: {dicom_data_dir}")

            # cwd= runs the exe from its own directory without changing the
            # watchdog's working directory (os.chdir was fragile: an exception
            # mid-flight left the whole process stranded in the wrong cwd).
            result = subprocess.run(
                [str(self.executable_path), str(dicom_data_dir)],
                capture_output=True,
                text=True,
                cwd=self.executable_path.parent,
            )

            if result.returncode != 0:
                print(f"Executable failed with return code: {result.returncode}")
                if result.stderr.strip():
                    print(f"Error: {result.stderr}")
                # Archive under failed_patient_files with a _failed_ stamp so
                # failures are visually distinct from real successes.
                self.move_processed_folder(dicom_folder_path, failed=True)
                return

            print("Executable completed successfully!")
            if result.stdout.strip():
                print(f"Output: {result.stdout}")

            self.move_processed_folder(dicom_folder_path)

            patient_folders = self._get_patient_folders_in_gate_ready()

            if len(patient_folders) == 1:
                folder_name = patient_folders[0].name
                print(f"Found patient folder to push: {folder_name}")
                push_to_cluster_and_submit(folder_name)
            elif len(patient_folders) == 0:
                raise FileNotFoundError(f"No patient folder found in {self.gate_ready_folder}")
            else:
                # Shouldn't happen since stale folders are cleaned beforehand,
                # but kept as a safety check.
                raise ValueError(
                    f"Multiple patient folders found in {self.gate_ready_folder}: "
                    f"{[f.name for f in patient_folders]}. "
                    "This is unexpected - stale folders should have been moved."
                )

        except Exception as e:
            print(f"Error processing DICOM folder: {e}")

    def move_processed_folder(self, dicom_folder_path, failed=False):
        """Archive the processed folder.

        Successes  -> completed_patient_files/<name>_done_<ts>
        Failures   -> failed_patient_files/<name>_failed_<ts>
        so failed exports can never be mistaken for good ones.
        """
        try:
            timestamp = int(time.time())
            if failed:
                archive_dir = "failed_patient_files"
                suffix = "failed"
            else:
                archive_dir = "completed_patient_files"
                suffix = "done"

            dest_name = f"{dicom_folder_path.name}_{suffix}_{timestamp}"
            dest_path = dicom_folder_path.parent / archive_dir / dest_name
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dicom_folder_path), str(dest_path))
            print(f"Moved processed folder: {dicom_folder_path} -> {dest_path}")
        except Exception as e:
            print(f"Error moving processed folder: {e}")




def monitor_for_random_folders(executable_path, dicom_folder_name="dicom_data"):
    executable = Path(executable_path)
    current_dir = Path.cwd()
    parent_dir = current_dir.parent

    if not executable.exists():
        print(f"FATAL: Executable does not exist: {executable}", flush=True)
        sys.exit(1)

    print(f"Monitoring directory: {parent_dir}", flush=True)
    print(f"Executable path: {executable.resolve()}", flush=True)

    event_handler = RandomFolderHandler(executable_path, dicom_folder_name)

    consecutive_errors = 0
    MAX_CONSECUTIVE_ERRORS = 60   # ~1 minute of solid failure

    print("Polling for numeric folders...", flush=True)
    try:
        while True:
            try:
                event_handler.poll_for_new_folders()
                event_handler.update_and_process_ready_folders()
                consecutive_errors = 0
            except OSError as e:
                # Share unavailable / disconnected. Expected occasionally.
                consecutive_errors += 1
                if consecutive_errors == 1 or consecutive_errors % 30 == 0:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                          f"Filesystem error (x{consecutive_errors}): {e}", flush=True)
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print("FATAL: share unreachable too long, exiting for restart.",
                          flush=True)
                    sys.exit(1)
            except Exception as e:
                consecutive_errors += 1
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                      f"Unexpected error in poll loop: {e}", flush=True)
                traceback.print_exc()
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print("FATAL: repeated errors, exiting for restart.", flush=True)
                    sys.exit(1)

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping monitor...", flush=True)


if __name__ == "__main__":
    EXECUTABLE_PATH = "./run.exe"
    DICOM_FOLDER_NAME = "dicom_data"

    expected = "get_gate_ready_files"
    if Path.cwd().name != expected:
        sys.exit(f"FATAL: cwd is {Path.cwd()}, expected to be inside {expected}")

    if len(sys.argv) >= 2:
        EXECUTABLE_PATH = sys.argv[1]
    if len(sys.argv) >= 3:
        DICOM_FOLDER_NAME = sys.argv[2]

    print("=== DICOM Folder Monitor ===", flush=True)
    print(f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"CWD: {Path.cwd()}", flush=True)
    print(f"Watching: {Path.cwd().parent}", flush=True)
    print(f"Python: {sys.executable}", flush=True)
    print()

    try:
        monitor_for_random_folders(EXECUTABLE_PATH, DICOM_FOLDER_NAME)
    except SystemExit:
        raise                      # let sys.exit() through untouched
    except BaseException:
        print("FATAL: unhandled exception, full traceback follows:", flush=True)
        traceback.print_exc()
        sys.exit(1)