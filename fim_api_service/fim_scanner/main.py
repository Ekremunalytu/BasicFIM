import hashlib
import json
import os
import sys
from typing import List, Dict, Union
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION
# Only file names or relative paths are kept here, not full paths.
# ==============================================================================
CONFIG = {
    "baseline_path_name": "baseline.json",
    "files_to_monitor": [
        "test.txt"
    ]
}

# ==============================================================================
# FIM ENGINE CLASS
# ==============================================================================
class FIM_Engine:
    def __init__(self, baseline_path: str):
        self.baseline_path = baseline_path
        self.baseline_data = self._load_baseline()
        print(f"FIM Engine started. Baseline file: '{self.baseline_path}'")

    def _load_baseline(self) -> Dict[str, str]:
        if not os.path.exists(self.baseline_path):
            print("Warning: Baseline file not found. Starting with an empty baseline.")
            return {}
        try:
            with open(self.baseline_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"CRITICAL ERROR: Could not read baseline file: {e}")
            sys.exit(1)

    def _save_baseline(self):
        try:
            with open(self.baseline_path, "w") as f:
                json.dump(self.baseline_data, f, indent=4)
            print(f"Baseline successfully saved to '{self.baseline_path}'.")
        except IOError as e:
            print(f"ERROR: Could not write baseline file: {e}")

    @staticmethod
    def calculate_file_hash(file_path: str) -> Union[str, None]:
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            return None
        except IOError as e:
            print(f"Error: Problem reading file '{file_path}': {e}")
            return None

    def create_or_update_baseline(self, files_to_baseline: List[Path], project_root: Path):
        print("\n--- Baseline Creation/Update Started ---")
        update_count = 0
        for file_path in files_to_baseline:
            file_path_str = str(file_path)
            rel_path = os.path.relpath(file_path_str, start=str(project_root))
            new_hash = self.calculate_file_hash(file_path_str)
            if new_hash:
                existing_hash = self.baseline_data.get(rel_path)
                if existing_hash is None:
                    # File is new to baseline
                    print(f"  -> New file added to baseline: '{rel_path}'.")
                    self.baseline_data[rel_path] = new_hash
                    update_count += 1
                elif existing_hash != new_hash:
                    # File exists but hash changed
                    print(f"  -> Baseline updated for '{rel_path}'.")
                    self.baseline_data[rel_path] = new_hash
                    update_count += 1
                else:
                    # File exists and hash is same
                    print(f"  -> '{rel_path}' already up to date.")
            else:
                print(f"  -> WARNING: '{rel_path}' not found, cannot add to baseline.")

        if update_count > 0:
            self._save_baseline()
        else:
            print("All files are already up to date. No changes made.")

    def check_integrity(self, files_to_check: List[Path], project_root: Path):
        print("\n--- Integrity Check Started ---")
        if not self.baseline_data:
            print("ERROR: Baseline data is empty or could not be loaded. Cannot check integrity.")
            return

        for file_path in files_to_check:
            file_path_str = str(file_path)
            rel_path = os.path.relpath(file_path_str, start=str(project_root))
            print(f"-> Checking: '{rel_path}'")

            original_hash = self.baseline_data.get(rel_path)
            if not original_hash:
                print("     Status: WARNING - This file is not in the baseline, not monitored.")
                continue

            current_hash = self.calculate_file_hash(file_path_str)
            if not current_hash:
                print("     Status: ALERT! - File DELETED!")
                continue

            if original_hash == current_hash:
                print("     Status: SAFE - No changes.")
            else:
                print("     Status: ALERT! - FILE MODIFIED!")
                print(f"        Original Hash: {original_hash[:12]}...")
                print(f"        Current Hash : {current_hash[:12]}...")

# ==============================================================================
# MAIN EXECUTION BLOCK
# ==============================================================================
if __name__ == "__main__":
    # 1. Find the directory where this script is located.
    SCRIPT_DIR = Path(__file__).resolve().parent

    # 2. Use script directory as the base for file monitoring (not project root)
    BASE_DIR = SCRIPT_DIR

    # 3. Build absolute paths for files to monitor using config.
    files_to_monitor_full_paths = [BASE_DIR / filename for filename in CONFIG["files_to_monitor"]]
    baseline_full_path = BASE_DIR / CONFIG["baseline_path_name"]

    print(f"Script Directory: {BASE_DIR}")
    print(f"Files to Monitor: {CONFIG['files_to_monitor']}")
    print("-" * 20)

    # Command line argument check
    if len(sys.argv) < 2:
        print("Auto mode: Checking integrity...")
        command = 'auto'
    elif sys.argv[1] not in ['baseline', 'check']:
        print("Usage Error!")
        print("  To create/update baseline: python main.py baseline")
        print("  To check integrity:        python main.py check")
        print("  For auto mode (no args):   python main.py")
        sys.exit(1)
    else:
        command = sys.argv[1]

    fim_engine = FIM_Engine(baseline_path=str(baseline_full_path))

    if command == 'baseline':
        fim_engine.create_or_update_baseline(files_to_baseline=files_to_monitor_full_paths, project_root=BASE_DIR)
    elif command == 'check':
        fim_engine.check_integrity(files_to_check=files_to_monitor_full_paths, project_root=BASE_DIR)
    elif command == 'auto':
        # Auto mode: sadece integrity check yap
        if fim_engine.baseline_data:
            fim_engine.check_integrity(files_to_check=files_to_monitor_full_paths, project_root=BASE_DIR)
        else:
            # İlk kez çalışıyorsa baseline oluştur
            print("No baseline found. Creating initial baseline...")
            fim_engine.create_or_update_baseline(files_to_baseline=files_to_monitor_full_paths, project_root=BASE_DIR)