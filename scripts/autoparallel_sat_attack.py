import os
import json
import subprocess
import time
import csv
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

# Setup Logging
os.makedirs("results", exist_ok=True)
log_file = "results/sat_attack_parallel.log"
logging.basicConfig(filename=log_file, level=logging.INFO, 
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Define Folders
CONFIG_FILE = "config/circuits.json"
DATA_FOLDER = "data"
LOCKED_FOLDER = "locked_circuits"
RESULTS_FOLDER = "results"
TOOLS_FOLDER = "tools"

os.makedirs(LOCKED_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

results_file = os.path.join(RESULTS_FOLDER, "sat_attack_parallel_results.csv")

# Auto-update config
if not os.path.exists(CONFIG_FILE):
    circuits = []
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith(".bench"):
            name = filename.split(".")[0]
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

# Create CSV with header
if not os.path.exists(results_file):
    with open(results_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Circuit", "Locked File", "Key Size", "SAT Attack Runtime (s)", "Iterations", "Key Correct"])

def run_command(command):
    start_time = time.time()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = e.stdout + e.stderr
        logging.error(f"Command failed: {command}\nError: {output}")
    return output, round(time.time() - start_time, 3)

def process_lock_and_attack(name, bench_file, key_size, iteration):
    key = "".join(["1" if i % 2 == 0 else "0" for i in range(key_size)])
    locked_file = os.path.join(LOCKED_FOLDER, f"{name}_RLL_K{key_size}_{iteration}.bench")

    rll_command = f"python3 {TOOLS_FOLDER}/RLL.py --bench_path {bench_file} --key {key} --save_path {locked_file} --iter 1"
    logging.info(f"Generating locked: {locked_file}")
    run_command(rll_command)

    sat_command = f"{TOOLS_FOLDER}/sld {locked_file} {bench_file}"
    sat_output, sat_time = run_command(sat_command)

    recovered_key = None
    iterations_found = None
    for line in sat_output.splitlines():
        if line.startswith("key="):
            recovered_key = line.replace("key=", "").strip()
        elif line.startswith("iteration="):
            try:
                iterations_found = int(line.split(";")[0].split("=")[1].strip())
            except:
                iterations_found = None

    key_correct = "N/A"
    if recovered_key:
        lcmp_command = f"{TOOLS_FOLDER}/lcmp {bench_file} {locked_file} key={recovered_key}"
        lcmp_output, _ = run_command(lcmp_command)
        key_correct = "YES" if "equivalent" in lcmp_output else "NO"

    return [name + ".bench", locked_file, key_size, sat_time, iterations_found, key_correct]

# Parallel Processing
tasks = []
with ProcessPoolExecutor() as executor:
    futures = []
    for circuit in circuits:
        bench_file = os.path.join(DATA_FOLDER, circuit["file"])
        name = circuit["name"]
        for key_size in circuit["key_sizes"]:
            for i in range(iterations):
                futures.append(executor.submit(process_lock_and_attack, name, bench_file, key_size, i))

    for future in as_completed(futures):
        result_row = future.result()
        with open(results_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(result_row)

# Call PDF generator
try:
    subprocess.run("python3 scripts/generate_pdf_report.py", shell=True, check=True)
except Exception as e:
    logging.error(f"PDF generation failed: {e}")

logging.info("All done. See CSV and PDF in results/")
print("Task A completed with parallel execution. Report saved in 'results/'")
