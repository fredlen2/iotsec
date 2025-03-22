import os
import json
import subprocess
import time
import csv
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initial Setup
JOBS = 8  # Adjust this depending on CPU cores

CONFIG_FILE = "config/circuits.json"
DATA_FOLDER = "data"
LOCKED_FOLDER = "locked_circuits"
RESULTS_FOLDER = "results"
TOOLS_FOLDER = "tools"
RLL_SCRIPT = f"{TOOLS_FOLDER}/RLL.py"
SAT_BINARY = f"{TOOLS_FOLDER}/sld"
LCMP_BINARY = f"{TOOLS_FOLDER}/lcmp"
RESULTS_CSV = os.path.join(RESULTS_FOLDER, "sat_attack_results_parallel.csv")
LOG_FILE = os.path.join(RESULTS_FOLDER, "sat_attack.log")

os.makedirs(LOCKED_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Load config 
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

circuits = config["circuits"]
iterations = config["iterations"]

# CSV Setup for output tracking
if not os.path.exists(RESULTS_CSV):
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Circuit", "Locked File", "Key Size", "SAT Attack Runtime (s)", "Iterations", "Key Correct"])

def run_task(name, bench_file, key_size, i):
    key = "".join(["1" if j % 2 == 0 else "0" for j in range(key_size)])
    locked_basename = f"{name}_RLL_K{key_size}_{i}"
    expected_output = os.path.join(LOCKED_FOLDER, f"{locked_basename}.bench")

    # Step 1: RLL Locking
    rll_cmd = f"python3 {RLL_SCRIPT} --bench_path {bench_file} --key {key} --save_path {os.path.join(LOCKED_FOLDER, locked_basename)} --iter 1"
    logging.info(f"[{name}] Generating locked file {expected_output}")
    subprocess.run(rll_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if not os.path.exists(expected_output):
        logging.error(f"[{name}] Failed to generate {expected_output}")
        return [name, expected_output, key_size, "ERROR", "", "GEN_FAIL"]

    # Step 2: SAT Attack
    sat_cmd = f"{SAT_BINARY} {expected_output} {bench_file}"
    sat_start = time.time()
    sat_proc = subprocess.run(sat_cmd, shell=True, capture_output=True, text=True)
    sat_time = round(time.time() - sat_start, 3)

    sat_output = sat_proc.stdout + sat_proc.stderr
    recovered_key = None
    iteration_count = None

    for line in sat_output.splitlines():
        if line.strip().startswith("iteration="):
            try:
                iteration_count = int(line.strip().split("=")[1].split(";")[0])
            except:
                iteration_count = None
        if "key=" in line and len(line.strip().split("=")[1].strip()) == key_size:
            recovered_key = line.strip().split("=")[1].strip()

    # Step 3: Key Verification
    key_status = "N/A"
    if recovered_key:
        lcmp_cmd = f"{LCMP_BINARY} {bench_file} {expected_output} key={recovered_key}"
        lcmp_proc = subprocess.run(lcmp_cmd, shell=True, capture_output=True, text=True)
        key_status = "YES" if "equivalent" in lcmp_proc.stdout else "NO"

    return [name, expected_output, key_size, sat_time, iteration_count, key_status]

# Parallel Execution
tasks = []
for circuit in circuits:
    bench_path = os.path.join(DATA_FOLDER, circuit["file"])
    for key_size in circuit["key_sizes"]:
        for i in range(iterations):
            tasks.append((circuit["name"], bench_path, key_size, i))

print(f"Running {len(tasks)} SAT attack tasks in parallel with {JOBS} workers...")

with ThreadPoolExecutor(max_workers=JOBS) as executor:
    futures = {executor.submit(run_task, *task): task for task in tasks}

    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        for future in as_completed(futures):
            result = future.result()
            writer.writerow(result)

print(f"Task A (Parallelized) complete! Check: {RESULTS_CSV}")
logging.info("Parallelized SAT attacks complete.")
