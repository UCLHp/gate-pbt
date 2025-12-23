=================================================================
# Automated Monte Carlo Simulation Pipeline Documentation
=================================================================

## 1. High-Level Overview

This document describes an automated pipeline for running Geant4-based Monte Carlo (MC) simulations for proton therapy treatment plans. The system is designed to be robust and requires minimal user interaction once initiated.

The pipeline is split into two primary, concurrent processes:

1.  **Pre-processing and Job Submission (`get_gate_ready_files`):** This part of the pipeline watches for new patient data exported from the Treatment Planning System (TPS). It processes this data into a format ready for simulation, pushes the necessary files to a high-performance computing (HPC) cluster, and submits the simulation jobs using Slurm.

2.  **Post-processing and Analysis (`pull_simulated_jobs_and_analyse`):** This part continuously monitors the HPC cluster for completed simulation jobs. Once a job is finished, it pulls the results back, performs a detailed analysis (including dose scaling, dose-to-water conversion, and gamma index comparison), and archives the results.

The entire workflow is designed to be a closed loop, as illustrated below:

```
+-----------------------+      +------------------------+      +---------------------+
|                       |      |                        |      |                     |
|   Treatment Planning  |----->|   DICOM Export Folder  |----->|  Pipeline Watches   |
|       System (TPS)    |      | (Monitored Directory)  |      | (get_gate_ready_files)|
|                       |      |                        |      |                     |
+-----------------------+      +------------------------+      +----------+----------+
                                                                          |
                                                                          | 1. Pre-process & Submit
                                                                          v
+-----------------------+      +------------------------+      +----------+----------+
|                       |      |                        |      |                     |
|      HPC Cluster      |<---->|   Submitted Job IDs    |<---->|  Pipeline Monitors  |
| (Runs GATE Simulation)|      |      (Shared File)     |      | (pull_sim_and_analyse)|
|                       |      |                        |      |                     |
+----------+------------+      +------------------------+      +----------+----------+
           |                                                              |
           | 2. Results Pulled                                            | 3. Analysis Run
           v                                                              v
+----------+------------+      +------------------------+      +----------+----------+
|                       |      |                        |      |                     |
| Completed Simulations |----->|   Analysis Results     |----->|  Import back to TPS |
| (Pulled from Cluster) |      | (Dose, Gamma, etc.)    |      |    (for review)     |
|                       |      |                        |      |                     |
+-----------------------+      +------------------------+      +---------------------+

```

---

## 2. Running the Pipeline

The pipeline is started by running two Python scripts concurrently in separate terminals. The `uv` runner is used to manage the environment.

**MAIN POWER SHELL**
```powershell
python .\main.py
```

This command runs the main.py script in the main directory (pbtmcdcm) and automatically runs the two main scripts (defined below)


**Terminal 1: Start the DICOM File Monitor**
```powershell
cd get_gate_analysis_files
$env:PYTHONUNBUFFERED=1
& uv run dicom_file_monitor.py 2>&1 | Tee-Object -FilePath '.\dcmfile.log'
```

**Terminal 2: Start the Completed Job Monitor**
```powershell
cd pull_simulated_jobs_and_analyse
$env:PYTHONUNBUFFERED=1
& uv run completed_patients_file_monitor_cont.py 2>&1 | Tee-Object -FilePath '.\completed_job_monitor.log'
```

These commands ensure that all output is printed to the console and simultaneously saved to log files for debugging.

---



## 3. Core Components & Workflow

### 3.1. Part 1: Pre-processing and Job Submission (`get_gate_ready_files`)

This process handles everything required to get from a raw DICOM export to a running simulation on the cluster.

**Key Script:** `dicom_file_monitor.py`

**Workflow:**

1.  **Monitoring:** The script watches a specific network directory for new folders. When a folder containing DICOM files is created (exported from the TPS), the script waits for 180 seconds to ensure the file transfer is complete.

2.  **File Organization:** The DICOM files are moved into a structured directory:
    `get_gate_ready_files/exported_patient_data/<PatientID_PlanName>/dicom_data/`

    ```
    (From Claude - I didn't do this) File Movement
    +-------------------------+                                +---------------------------------------------+
    | \\network\path\to\export|                                | ...\exported_patient_data\                  |
    |                         |                                |  +-- <PatientID_PlanName>\                  |
    |  +-- 1234567\           | --(moves)-->                   |  |    +-- dicom_data\                       |
    |  |   +-- CT.dcm         |                                |  |    |    +-- CT.dcm                       |
    |  |   +-- RTPLAN.dcm     |                                |  |    |    +-- RTPLAN.dcm                   |
    |  |   +-- ...            |                                |  |    |    +-- ...                          |
    +-------------------------+                                +---------------------------------------------+
    ```

3.  **Execution of `run.exe`:** The script then calls `run.exe`, passing the path to the newly created `dicom_data` directory. `run.exe` is a compiled Python script (`run.py`) that performs the core pre-processing tasks:
    *   **Reads DICOM:** Parses CT, RTPLAN, RTSTRUCT, and RTDOSE files.
    *   **Creates Simulation Structure:** Builds the necessary directory structure (`data/`, `mac/`, `output/`) for the GATE simulation.
    *   **Image Conversion & Processing:**
        *   Converts the DICOM CT series into a single MetaImage file (`.mhd`).
        *   Re-orientates the image to a standard orientation.
        *   Crops the CT image to a smaller region of interest (e.g., around the `zSurface` contour) to reduce simulation time.
        *   Applies material overrides based on the RTSTRUCT file (e.g., setting regions outside the patient to air, applying specific HU values to defined structures).
    *   **Generates Simulation Files:** Calls `generatefiles.py` to create the GATE macro (`.mac`) files which contain the simulation instructions (beam positions, energies, etc.) derived from the RTPLAN.
    *   **Creates Slurm Script:** Calls `slurm.py` to generate the submission script for the Slurm job scheduler.

4.  **Push to Cluster:** After `run.exe` finishes, the `push_to_cluster_and_submit` function is called.
    *   It uses SFTP (via the `paramiko` library) to transfer the entire generated simulation folder to the HPC cluster's shared file system (`/mnt/clustshare/`).
    *   It then uses SSH to execute a script on the cluster (`~/submit_gate_jobs.sh`) which submits the job to Slurm.
    *   The script captures the Job IDs returned by Slurm.

5.  **Logging Job IDs:** The captured Job IDs are saved to a text file named `<PatientID_PlanName>_job_ids.txt` inside the `pull_simulated_jobs_and_analyse/submitted_jobs/` directory. This file acts as a handover point to the second part of the pipeline.

### 3.2. Part 2: Post-processing and Analysis (`pull_simulated_jobs_and_analyse`)

This process runs continuously, checking for finished jobs and analyzing them.

**Key Script:** `completed_patients_file_monitor_cont.py`

**Workflow:**

1.  **Monitoring Submitted Jobs:** The script runs in a loop (every 20 minutes). In each cycle, it:
    *   Reads all `_job_ids.txt` files in the `submitted_jobs` directory to get a list of all simulations that are pending or running.

2.  **Checking Job Status:**
    *   It connects to the HPC cluster via SSH and runs the `squeue` command to get a list of all currently running jobs for the user.
    *   By comparing the list of submitted jobs with the list of running jobs, it identifies which simulations have completed.

3.  **Pulling Results:** For each completed simulation, the script:
    *   Connects to the cluster via SFTP.
    *   Downloads the entire simulation folder (which now contains the output results) from the cluster into the `pull_simulated_jobs_and_analyse/completed_patients/` directory.

    ```
    Pulling Results
    +--------------------------------+                                +------------------------------------------+
    | HPC Cluster (/mnt/clustshare/) |                                | ...\pull_simulated_jobs_and_analyse\     |
    |                                |                                |  +-- completed_patients\                 |
    |  +-- <PatientID_PlanName>\     |                                |  |    +-- <PatientID_PlanName>\          |
    |  |   +-- data/                 |      --(downloads)-->          |  |    |    +-- data/                      |
    |  |   +-- mac/                  |                                |  |    |    +-- mac/                       |
    |  |   +-- output/ (with results)|                                |  |    |    +-- output/ (with results)     |
    +--------------------------------+                                +------------------------------------------+
    ```

4.  **Execution of `analysis.exe`:** The script then calls `analysis.exe` on the downloaded `output` directory. `analysis.exe` is a compiled Python script (`analysis.py`) that performs the core post-processing:
    *   **Merges Results:** Combines the scattered output files from the parallel simulation jobs into single merged files (e.g., `_merged-Dose.mhd`, `_merged-LET.mhd`).
    *   **Dose Scaling:** Scales the relative dose from the MC simulation to absolute dose (in Gy) based on the number of simulated particles versus the number required by the treatment plan.
    *   **Dose-to-Water Conversion:** Converts the simulated "dose-to-material" into "dose-to-water", which is the standard for clinical evaluation.
    *   **Gamma Analysis:** Performs a gamma index comparison between the final MC dose and the original dose calculated by the TPS. This is a critical quality assurance step. Pass rates for 3%/3mm and 2%/2mm criteria are calculated and saved.
    *   **Uncertainty Analysis:** Calculates and saves metrics related to the statistical uncertainty of the simulation.
    *   **MHD to DICOM Conversion:** Converts the final dose and gamma map `.mhd` files back into the DICOM format, using the original RTDOSE file as a template. This allows the results to be imported back into the TPS for visual review and comparison.

5.  **Archiving:** Once the analysis is complete, the script moves the `_job_ids.txt` file and the patient's simulation folder to archive directories (`completed_jobs_text/` and `analysed_completed_patients/`) to signify that the process for this patient is complete.


## 5. Executable Generation

The `run.exe` and `analysis.exe` files are crucial components. They are generated from their respective Python scripts (`run.py`, `analysis.py`) using **PyInstaller**.

These are run from within the gate-pbt-executable-code directory, which contains all the code that produces the executables:

`\gate-pbt-executable-code\gate-pbt-executable\gate-pbt`

The project is set up with `.spec` files (`run.spec`, `analysis.spec`) that contain the correct configuration for PyInstaller to bundle all necessary dependencies, assets (like the `templates` folder), and paths correctly.

To re-compile an executable, you would run:


```bash
# Example for run.exe
\gate-pbt-executable-code> uv run pyinstaller .\gate-pbt-executable\gate-pbt\run.spec

# Example for analysis.exe
\gate-pbt-executable-code> uv run pyinstaller .\gate-pbt-executable\gate-pbt\analysis.spec
```
This ensures that the executables are self-contained and can be run without issues related to Python paths or missing packages. It's important you run from within gate-pbt-executable-code so that the correct uv .venv is used.

The executables are then located in `\gate-pbt-executable-code\gate-pbt-executable\gate-pbt\dist`. Both the _internal folder and the executable files are needed. They should be copied and placed directly into the `get_gate_ready_files` (run) and `pull_simulated_jobs_and_analyse` (analysis) directories.

If you wanted to run the run.py or analysis.py scripts directly you could do so with 
```bash
uv run .\gate-pbt-executable\gate-pbt\analysis\analysis.py

```

These scripts take the directory of the folders to run on as an argument, but if no arg is given, a GUI is opened for the user to select.





================================================================================
                    PIP + VENV vs UV CHEAT SHEET
            Python Package Management: Traditional vs Modern
================================================================================
================================================================================
OVERVIEW & PHILOSOPHY
================================================================================

PIP + VENV (Traditional Approach)
----------------------------------
• Separate tools for separate tasks:
  - pip: Package installer (written in Python)
  - venv: Virtual environment creator (Python standard library)
  - pip-tools: Dependency locking (separate install)
  - pyenv: Python version management (separate tool)

• Fragmented workflow requiring multiple tools
• Each virtual environment duplicates all dependencies
• Sequential operations (slow)
• Requires Python to be installed first
• Industry standard since 2008 (pip) and 2012 (venv)

UV (Modern All-in-One Approach)
--------------------------------
• Single unified tool written in Rust
• Replaces: pip, venv, pip-tools, virtualenv, pipx, pyenv, poetry, and more
• 10-100x faster than pip in benchmarks
• Global cache with symlinks/hardlinks (no duplication)
• Parallel operations throughout
• Can be installed without Python
• Drop-in replacement for pip commands
• Created by Astral (makers of Ruff linter)

================================================================================
ARCHITECTURE & HOW THEY WORK
================================================================================

PIP + VENV ARCHITECTURE
-----------------------

How venv works:
• Creates isolated Python environment by copying Python binary
• Creates lib/site-packages directory for packages
• Modifies PATH to use environment's Python/pip
• Each environment is completely independent
• Every project gets full copies of all dependencies
• Typical size: Multiple GB for ML projects (duplicate numpy, pandas, etc.)

How pip works:
• Written in Python (slower, needs Python to run)
• Downloads packages from PyPI (Python Package Index)
• Resolves dependencies sequentially
• Downloads entire wheel files to read metadata
• Installs packages by copying files into site-packages
• No global cache (re-downloads for each environment)
• Dependency resolution can be slow and sometimes incorrect
• Uses greedy/backtracking algorithm

Installation process:
1. Download entire wheel file
2. Extract and parse metadata
3. Resolve dependencies (one at a time)
4. Download more wheels
5. Copy files into site-packages
6. Compile bytecode

UV ARCHITECTURE
---------------

How uv works:
• Written in Rust (compiled binary, extremely fast)
• Uses global cache: ~/.cache/uv/
• Packages downloaded once, linked to all projects
• Uses hardlinks/symlinks on filesystem (CoW on supported filesystems)
• No duplication of packages across projects
• Parallel downloads and dependency resolution

Key innovations:
1. Zero-copy deserialization (.rkyv files)
   - Metadata stored in binary format matching memory layout
   - No parsing needed - mapped directly into memory
   - O(1) complexity for metadata access vs O(n) for pip

2. HTTP Range Requests
   - Fetches only metadata from wheels (few KB instead of entire file)
   - Example: Reads 3KB from 100MB PyTorch wheel instead of downloading all

3. Lock-free concurrency
   - Uses atomic operations instead of thread locks
   - Each CPU core gets cache copy
   - Compare-and-swap for updates
   - Multiple threads work simultaneously without blocking

4. Advanced dependency resolver
   - Parallel resolution of dependency tree
   - Pubgrub algorithm (same as Cargo, Dart)
   - Considers all constraints simultaneously
   - Proves solutions exist or conclusively shows impossibility

5. Global cache with content addressing
   - Stores packages by hash in ~/.cache/uv/
   - Creates hardlinks in project .venv pointing to cache
   - One copy of numpy==1.24.0 serves all projects
   - Saves gigabytes of disk space

Installation process:
1. Fetch only metadata via HTTP range request (parallel)
2. Resolve all dependencies simultaneously
3. Download packages in parallel (only if not cached)
4. Create hardlinks from cache to venv
5. Complete in milliseconds instead of minutes

Virtual environments:
• 80x faster than python -m venv
• 7x faster than virtualenv
• Standards-compliant (work with other tools)
• Uses same .venv structure
• Automatically detects and uses nearest .venv in tree

INSTALLING UV
-------------
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pip (ironically)
pip install uv

# With pipx
pipx install uv

# With Homebrew
brew install uv

# No Python required! UV is a standalone binary.

================================================================================
PERFORMANCE DIFFERENCES
================================================================================

Why UV is faster:
1. Written in Rust (compiled, not interpreted)
2. Parallel operations everywhere
3. Global cache (no re-downloads)
4. Zero-copy deserialization
5. HTTP range requests (partial downloads)
6. Lock-free concurrency
7. Advanced dependency resolver
8. No Python interpreter overhead

================================================================================
KEY ADVANTAGES & LIMITATIONS
================================================================================

PIP + VENV ADVANTAGES
---------------------
✓ Industry standard (universal compatibility)
✓ Built into Python (no separate install)
✓ Mature and battle-tested
✓ Extensive documentation and community support
✓ Guaranteed compatibility with all packages
✓ Works in all environments
✓ Well-understood by all Python developers
✓ Reliable for production environments

PIP + VENV LIMITATIONS
----------------------
✗ Slow (especially with large dependencies)
✗ No built-in dependency locking
✗ Requires multiple tools (pip, venv, pip-tools, pyenv)
✗ Duplicates packages across projects (wastes disk space)
✗ No global cache
✗ Cryptic error messages
✗ Poor dependency conflict resolution
✗ Leaves orphaned dependencies after uninstall
✗ Sequential operations
✗ Re-downloads packages for each environment


UV ADVANTAGES
-------------
✓ Extremely fast (10-100x speedup)
✓ All-in-one tool (replaces 7+ tools)
✓ Global cache (saves disk space)
✓ Built-in dependency locking
✓ Better error messages
✓ Python version management included
✓ Parallel operations
✓ Drop-in pip replacement
✓ Standards-compliant environments
✓ Removes transitive dependencies on uninstall
✓ Cross-platform consistency
✓ No Python required for installation
✓ Modern project management (like Cargo/Poetry)
✓ Reproducible builds
✓ Great for CI/CD pipelines

UV LIMITATIONS
--------------
✗ Relatively new (2024 release)
✗ Less battle-tested than pip
✗ Smaller community (growing rapidly)
✗ Python-only (can't install system dependencies like Conda)
✗ Doesn't read pip.conf or PIP_* environment variables
✗ May have compatibility issues with very old packages (.egg format)
✗ Learning curve for project-based workflow
✗ Not included with Python by default (yet)

================================================================================
MIGRATION GUIDE
================================================================================

FROM PIP + VENV TO UV
---------------------

STEP 1: Install UV
------------------
curl -LsSf https://astral.sh/uv/install.sh | sh

STEP 2: Modern Project Workflow
------------------------------------------------
# For new or migrating projects:

1. Initialize UV project:
   uv init  # Or convert existing project

2. Generate pyproject.toml from requirements.txt:
   # Manually create pyproject.toml or:
   uv add $(cat requirements.txt | grep -v '^#' | grep -v '^$')
   # personally. I put the requirements.txt file in the context window of a LLM and get it to make my the pyproject.toml file
   # then just run uv sync

3. Sync environment:
   uv sync # checks what is in the .venv is consistent with pyproject.toml

5. Run your code:
   uv run python script.py
 

COMMON MIGRATION TASKS
----------------------

Existing project with requirements.txt:
---------------------------------------
# Old way
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# New way 
uv init
# Move dependencies to pyproject.toml
uv sync



UNIQUE UV COMMANDS
------------------
uv init                             # Initialize new project
uv add requests                     # Add dependency to project
uv remove requests                  # Remove dependency from project
uv sync                             # Sync project dependencies
uv lock                             # Lock dependencies
uv tool install ruff                # Install tool globally
uv python list                      # List available Python versions
uv python pin 3.11                  # Pin project to Python version

