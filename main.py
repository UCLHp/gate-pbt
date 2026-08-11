import subprocess
import os
from pathlib import Path
import sys

UV = r'C:\Users\MSOUTHER\.local\bin\uv.exe'



def main():
    # Define the two scripts
    scripts = [
        {
            'name': 'DICOM File Monitor',
            'script': 'dicom_file_monitor.py',
            'cwd': 'get_gate_ready_files',
            'log': 'dcmfile.log'
        },
        {
            'name': 'Completed Job Monitor',
            'script': 'completed_patients_file_monitor_cont.py',
            'cwd': 'pull_simulated_jobs_and_analyse',
            'log': 'completed_job_monitor.log'
        }
    ]
    
    processes = []
    
    try:
        print("Starting pipeline monitors...")
        
        # Start both processes
        for config in scripts:
            print(f"\nStarting {config['name']}...")
            process = subprocess.Popen(
                [UV, 'run', '--env-file', '.env', config['script']],
                cwd=config['cwd'],
                env={**os.environ, 'PYTHONUNBUFFERED': '1'},
                stdout=open(Path(config['cwd']) / config['log'], 'a', buffering=1),
                stderr=subprocess.STDOUT
            )
            processes.append((config['name'], process))
            print(f"{config['name']} started (PID: {process.pid})")
        
        print("\nBoth monitors are running. Press Ctrl+C to stop.")
        
        # Wait for processes and monitor them
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    print(f"\n {name} has stopped unexpectedly (exit code: {process.returncode})")
                    sys.exit(1)
            
            # Sleep briefly to avoid busy waiting
            import time
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nShutting down monitors...")
        for name, process in processes:
            process.terminate()
            print(f"Stopped {name}")
        print("All monitors stopped.")
    
    except Exception as e:
        print(f"\n Error: {e}")
        for name, process in processes:
            process.terminate()
        sys.exit(1)
        

if __name__ == '__main__':
    main()