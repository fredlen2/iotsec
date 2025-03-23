import os
import json
import re
import subprocess
import time
import csv
import logging

# Setup Logging
log_file = "results/sat_attack.log"
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

# Results File
results_file = os.path.join(RESULTS_FOLDER, "sat_attack_results.csv")

# Function to Update Config File Dynamically
def update_config():
    """Scans the data folder and updates circuits.json dynamically."""
    circuits = []
    
    for filename in os.listdir(DATA_FOLDER):
        if filename.endswith(".bench"):
            name = filename.split(".")[0]  # Extract circuit name
            key_sizes = [16, 32] if name.startswith("c") else [128, 256]  # Infer key sizes
            circuits.append({"name": name, "file": filename, "key_sizes": key_sizes})

    config = {"circuits": circuits, "iterations": 10}

    # Save updated config to file
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

    logging.info("Updated circuits.json dynamically.")

# Load or Update Config
if not os.path.exists(CONFIG_FILE):
    logging.info("Config file not found. Generating a new one...")
    update_config()

# Load configuration file
with open(CONFIG_FILE, "r") as f:
    config = json.load(f)

circuits = config["circuits"]
iterations = config["iterations"]

def run_command(command):
    """Executes a shell command and returns output & execution time."""
    start_time = time.time()
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = e.output
        logging.error(f"Command failed: {command}\nError: {output}")
    end_time = time.time()
    return output, round(end_time - start_time, 3)

# Create CSV File with Headers if not exists
if not os.path.exists(results_file):
    with open(results_file, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Circuit", "Locked File", "Key Size", "SAT Attack Runtime (s)", "Iterations", "Key Correct"])

for circuit in circuits:
    bench_file = os.path.join(DATA_FOLDER, circuit["file"])
    name = circuit["name"]

    for key_size in circuit["key_sizes"]:
        key = "".join(["1" if i % 2 == 0 else "0" for i in range(key_size)])  # Generate key pattern
        
        for i in range(iterations):
            locked_file = os.path.join(LOCKED_FOLDER, f"{name}_RLL_K{key_size}_{i}.bench")
            
            # Step 1: Generate RLL-Locked Design
            rll_command = f"python3 {TOOLS_FOLDER}/RLL.py --bench_path {bench_file} --key {key} --save_path {locked_file} --iter 1"
            logging.info(f"Generating locked design: {locked_file}")
            print(f"Generating locked design: {locked_file}")
            run_command(rll_command)

            # Step 2: Run SAT Attack
            sat_command = f"{TOOLS_FOLDER}/sld {locked_file} {bench_file}"
            logging.info(f"Running SAT attack on: {locked_file}")
            print(f"Running SAT attack on: {locked_file}")

            sat_output, _ = run_command(sat_command)
            logging.info(f"SAT attack results: {sat_output}")

            # Extract SAT Attack Iterations and Time
            iterations_found, sat_time = None, None
            match = re.search(r"iteration=(\d+);.*?cpu_time=([\d.]+);", sat_output)
            if match:
                iterations_found = int(match.group(1))
                sat_time = float(match.group(2))

            # Step 3: Extract recovered key
            recovered_key = None
            for line in sat_output.split("\n"):
                if "Recovered Key:" in line:
                    recovered_key = line.split(":")[1].strip()
                    break

            # Step 4: Verify key correctness
            key_correct = "N/A"
            if os.path.exists(locked_file):  # Ensure file exists before running lcmp
                lcmp_command = f"{TOOLS_FOLDER}/lcmp {bench_file} {locked_file} key={key}"
                logging.info(f"Verifying key for: {locked_file}")
                print(f"Verifying key for: {locked_file}")
                lcmp_output, _ = run_command(lcmp_command)

                key_correct = "YES" if "equivalent" in lcmp_output else "NO"

            # Step 5: Save Results
            with open(results_file, "a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([f"{name}.bench", locked_file, key_size, sat_time, iterations_found, key_correct])

logging.info("Process completed. Check 'results/sat_attack_results.csv' for results.\n'locked bench files are also in locked_circuits/ folder")
print("Task A completed. Check results in 'results/sat_attack_results.csv'.\n'locked bench files are also in locked_circuits/ folder'")
