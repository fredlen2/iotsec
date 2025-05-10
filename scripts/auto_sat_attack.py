#!/usr/bin/env python3
import json
import logging
import subprocess
import time
import csv
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

# —— CONFIGURATION —— #
ROOT         = Path.cwd()
DATA_DIR     = ROOT / "data"
LOCKED_DIR   = ROOT / "locked_circuits"
RESULTS_DIR  = ROOT / "results"
TOOLS_DIR    = ROOT / "tools"
CONFIG_PATH  = ROOT / "config" / "circuits.json"
RESULTS_CSV  = RESULTS_DIR / "sat_attack_parallel_results.csv"

# —— SET UP LOGGING & FOLDERS —— #
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOCKED_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    filename=RESULTS_DIR / "sat_attack_parallel.log",
    level=logging.WARNING,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# —— GENERATE DEFAULT CONFIG IF MISSING —— #
if not CONFIG_PATH.exists():
    circuits = [
        {
            "name": f.stem,
            "file": f.name,
            "key_sizes": [16, 32] if f.stem.startswith("c") else [128, 256]
        }
        for f in DATA_DIR.glob("*.bench")
    ]
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"circuits": circuits, "iterations": 10}, indent=4)
    )
    logging.info("Generated config file at %s", CONFIG_PATH)

# —— LOAD CONFIG —— #
config = json.loads(CONFIG_PATH.read_text())
circuits, iterations = config["circuits"], config["iterations"]

# —— INITIALIZE RESULTS CSV —— #
if not RESULTS_CSV.exists():
    with RESULTS_CSV.open("w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Circuit", "Locked File", "Key Size",
            "SAT Attack Runtime (s)", "Iterations", "Key Correct"
        ])

# —— HELPERS —— #
def run(cmd: list) -> tuple[str, float]:
    start = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = proc.stdout
    except subprocess.CalledProcessError as e:
        out = (e.stdout or "") + (e.stderr or "")
        logging.error("Failed %s → %s", cmd, out)
    return out, round(time.time() - start, 3)

def generate_key(size: int) -> str:
    # repeat "10" pairs (or add an extra "1" for odd sizes)
    return "10" * (size // 2) + ("1" if size % 2 else "")

def process(c: dict, key_size: int, iteration: int) -> list:
    name      = c["name"]
    bench     = DATA_DIR / c["file"]
    key       = generate_key(key_size)
    locked    = LOCKED_DIR / f"{name}_RLL_K{key_size}_{iteration}.bench"

    # 1) Lock the circuit
    run([
        "python3", str(TOOLS_DIR / "RLL.py"),
        "--bench_path", str(bench),
        "--key",        key,
        "--save_path",  str(locked),
        "--iter",       "1"
    ])

    # 2) Run SAT attack
    sat_out, sat_time = run([
        str(TOOLS_DIR / "sld"),
        str(locked),
        str(bench)
    ])

    # 3) Parse solver output
    recovered, iters_found = None, None
    for line in sat_out.splitlines():
        if line.startswith("key="):
            recovered = line.split("=", 1)[1].strip()
        elif line.startswith("iteration="):
            try:
                iters_found = int(line.split("=", 1)[1].split(";", 1)[0])
            except ValueError:
                pass

    # 4) Validate key if recovered
    key_correct = "N/A"
    if recovered:
        lcmp_out, _ = run([
            str(TOOLS_DIR / "lcmp"),
            str(bench),
            str(locked),
            f"key={recovered}"
        ])
        key_correct = "YES" if "equivalent" in lcmp_out else "NO"

    return [
        f"{name}.bench",
        str(locked),
        key_size,
        sat_time,
        iters_found,
        key_correct
    ]

# —— MAIN EXECUTION —— #
def main():
    # build task list
    tasks = [
        (circuit, ks, i)
        for circuit in circuits
        for ks in circuit["key_sizes"]
        for i  in range(iterations)
    ]

    results = []
    max_workers = min(32, (os.cpu_count() or 1) * 2, len(tasks))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(process, c, ks, i): (c["name"], ks, i)
            for c, ks, i in tasks
        }
        for future in tqdm(as_completed(futures),
                           total=len(futures),
                           desc="Running tasks"):
            try:
                results.append(future.result())
            except Exception as e:
                logging.exception("Task %s failed", futures[future])

    # batch‐write CSV
    with RESULTS_CSV.open("a", newline="") as csvfile:
        csv.writer(csvfile).writerows(results)

    # generate PDF report
    try:
        subprocess.run(["python3", "scripts/gen_pdf_report.py"], check=True)
    except Exception as e:
        logging.error("PDF generation failed: %s", e)

    print("All tasks completed—results and report in", RESULTS_DIR)

if __name__ == "__main__":
    main()
