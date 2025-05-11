# IoT and Embedded System Security assignment solution

First, clone the repository then you can proceed with the below steps which ever may be applicable.
You can skip the ones that do not apply:
```
https://github.com/fredlen2/iotsec.git
```

## SETUP INSTRUCTIONS
Ensure all directories and files exist. I have added some extra steps in most of the scripts to ensure it creates the required directories automatically. But if the script fails, run these then try again:

``` \bin\bash
mkdir -p config data locked_circuits results tools
touch config/circuits.json  # If not already present
touch results/sat_attack.log  # If not already present
```

Create a .venv directory in your project folder and activate it with the second line code.

``` \bin\bash
# Sudo issues run these to create the .venv
python3 -m pip install --user virtualenv
python3 -m virtualenv .venv


# No sudo issues
python3 -m venv .venv
```

Activate virtual environment from project folder:
``` \bin\bash
source .venv/bin/activate
```

### install python requirements
``` \bin\bash
    pip install -r requirements.txt
```

### SLD, LCMP and Atalanta
The tools directory in the project folder contains the Atalanta, SLD, and LCMP. You'll need to grant execute permission for the sld and lcmp if you're running the task A script.
Atalanta can be run from wherever you have yours and is even easier if you have added to your bash profile.


## ABOVE STEPS ARE NECESSARY ESPECIALLY THE .venv FOR ASSIGNMENT 1

# ASSIGNMENT 1
## Assignment Task A Scripts Usage:
This script scans the original bench directory (data) and creates a json file of the iterations and keysizes for each design
``` python3
    python3 scripts/gen_circuits_json.py
```

The script proceeds to run python3 scripts/gen_pdf_report.py to convert the output csv to pdf.
Increase max_workers if the tasks are mostly waiting on external processes 
(scripts/autoparallel_sat_attack.py line 111). 
example:
    max_workers = 8
The tools/RLL.py script is not fully optimized making this script slow.

Task A deliverable:
``` python3
    python3 scripts/autoparallel_sat_attack.py
```

This is an alternative script (Not tested because server was throwing some errors)
```
    python3 scripts/auto_sat_attack.py
```


## Assignment Task B Scripts - provably secure logic locking Usage:
Task B deliverable:
``` python3
python3 scripts/sarlock.py data/c432.bench --keysize 16
python3 scripts/antisat.py data/c432.bench --keysize 16
python3 scripts/corrupt_and_correct.py data/c432.bench --keysize 16
```

## Assignment Task C Scripts - Hardware Trojan Design Usage:

A minimal Trojan consists of:

Trigger logic – A set of rare nodes (inputs) that activate the Trojan.
Payload logic – The actual malicious modification in the circuit.
Integration – The Trojan must affect the circuit output when activated.

Task C deliverable:
### Trojan scripts output folder is `locked_circuits`
### Generate 50 trojan-infected files from one design
``` python3
    python3 scripts/insert_trojan.py --bench_path data/c432.bench
```

### Generate 50 trojan files with 4-input triggers from one design
``` python3
    python3 scripts/insert_trojan.py --bench_path data/c432.bench --trigger_size 4 --num_trojans 50
```

### Batch-infect all .bench files in a directory
``` python3
    python3 scripts/insert_trojan.py --bench_path data/
```



# ASSIGNMENT 2
## Stealthy Trojans
Assignment 2 deliverable:
``` \bin\bash
    python3 scripts/antisat_trojan.py  --bench_path data/c432.bench --keysize 16
    python3 scripts/cac_trojan.py --bench_path data/c432.bench --keysize 16
    python3 scripts/sarlock_trojan.py --bench_path data/c432.bench --keysize 16

```


### Sample helper Scripts to monitor the files or file contents creation:
script to watch bench files being created in the locked_circuits directory:
``` \bin\bash
    watch -n 1 ls -l locked_circuits/
```

script to watch log files and CSV file being written to
``` \bin\bash
    tail -f results/sat_attack_parallel_results.csv
```
``` \bin\bash
    tail -f results/sat_attack_parallel.log
```

### The pdf script can be run manually too
```python3
    python3 scripts/gen_pdf_report.py \
    --input-csv results/sat_attack_parallel_results.csv \
    --output-pdf results/sat_attack_summary.pdf \
    --rows-per-page 25
```