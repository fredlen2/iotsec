import os
import json
import subprocess
import time
import csv
import logging
import shlex
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# Setup Logging (set to WARNING to reduce logging overhead)
os.makedirs("results", exist_ok=True)
log_file = os.path.join("results", "sat_attack_parallel.log")
logging.basicConfig(filename=log_file, level=logging.WARNING, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Define Folders
CONFIG_FILE = os.path.join("config", "circuits.json")
DATA_FOLDER = "data"
LOCKED_FOLDER = "locked_circuits"
RESULTS_FOLDER = "results"
TOOLS_FOLDER = "tools"

os.makedirs(LOCKED_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

results_file = os.path.join(RESULTS_FOLDER, "sat_attack_parallel_results.csv")

# Auto-update config if not present
if not os.path.exists(CONFIG_FILE):
    circuits = []
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith(".bench"):
            name = os.path.splitext(filename)[0]
            key_sizes = [16, 32] if name.startswith("c") else [128, 256]
            circuits.append({"name": name, "file": filename, "key_sizes": key_sizes})
    with open(CONFIG_FILE, "w") as f:
        json.dump({"circuits": circuits, "iterations": 10}, f, indent=4)
    logging.info("Generated config file.")

# Load config
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

circuits = config["circuits"]
iterations = config["iterations"]

# Create CSV with header if it does not exist
if not os.path.exists(results_file):
    with open(results_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Circuit", "Locked File", "Key Size", "SAT Attack Runtime (s)", "Iterations", "Key Correct"])

def run_command(command, use_shell=False):
    """
    Run an external command and return (output, runtime).
    If use_shell is False, command is split using shlex.split.
    """
    start_time = time.time()
    try:
        if use_shell:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        else:
            args = shlex.split(command)
            result = subprocess.run(args, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = e.stdout + e.stderr
        logging.error(f"Command failed: {command}\nError: {output}")
    return output, round(time.time() - start_time, 3)

def generate_key(key_size):
    """Generate a key string like '1010...' based on key_size."""
    return "10" * (key_size // 2) + ("1" if key_size % 2 else "")

def process_lock_and_attack(name, bench_file, key_size, iteration):
    key = generate_key(key_size)
    locked_file = os.path.join(LOCKED_FOLDER, f"{name}_RLL_K{key_size}_{iteration}.bench")

    # Generate locked file using RLL.py
    rll_command = f"python3 {TOOLS_FOLDER}/RLL.py --bench_path {bench_file} --key {key} --save_path {locked_file} --iter 1"
    run_command(rll_command, use_shell=False)

    # Run SAT attack
    sat_command = f"{TOOLS_FOLDER}/sld {locked_file} {bench_file}"
    sat_output, sat_time = run_command(sat_command, use_shell=False)

    recovered_key = None
    iterations_found = None
    for line in sat_output.splitlines():
        if line.startswith("key="):
            recovered_key = line.replace("key=", "").strip()
        elif line.startswith("iteration="):
            try:
                iterations_found = int(line.split(";")[0].split("=")[1].strip())
            except Exception:
                iterations_found = None

    key_correct = "N/A"
    if recovered_key:
        lcmp_command = f"{TOOLS_FOLDER}/lcmp {bench_file} {locked_file} key={recovered_key}"
        lcmp_output, _ = run_command(lcmp_command, use_shell=False)
        key_correct = "YES" if "equivalent" in lcmp_output else "NO"

    return [name + ".bench", locked_file, key_size, sat_time, iterations_found, key_correct]

def main():
    results = []
    total_tasks = sum(len(circuit["key_sizes"]) * iterations for circuit in circuits)
    # Increase max_workers if the tasks are mostly waiting on external processes
    max_workers = 8
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for circuit in circuits:
            bench_file = os.path.join(DATA_FOLDER, circuit["file"])
            name = circuit["name"]
            for key_size in circuit["key_sizes"]:
                for i in range(iterations):
                    futures.append(executor.submit(process_lock_and_attack, name, bench_file, key_size, i))

        # Wrap the as_completed iterator with tqdm to show progress
        for future in tqdm(as_completed(futures), total=total_tasks, desc="Processing tasks"):
            try:
                result_row = future.result()
                results.append(result_row)
            except Exception as e:
                logging.error(f"Task failed: {e}")

    # Write all results to CSV at once
    with open(results_file, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(results)

    # Call PDF generator
    try:
        subprocess.run(["python3", "scripts/gen_pdf_report.py"], check=True)
    except Exception as e:
        logging.error(f"PDF generation failed: {e}")

    logging.info("All done. See CSV and PDF in results/")
    print("Task A completed with parallel execution. Report saved in 'results/'")

if __name__ == "__main__":
    main()
