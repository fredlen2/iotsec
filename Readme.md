# IoT and Embedded System Security assignment solution

First, clone the repository then you can proceed with the below steps which ever may be applicable.
You can skip the ones that do not apply:
```
https://github.com/fredlen2/iotsec.git
```

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

## Assignment Task A Scripts Usage:

``` python3
python3 scripts/gen_circuits_json.py
```

``` python3
python3 scripts/automate_sat_attack.py

# OR

python3 scripts/autoparallel_sat_attack.py

# The second script proceeds to run python3 scripts/gen_pdf_report.py to convert the output csv to pdf.
# Increase max_workers if the tasks are mostly waiting on external processes 
(scripts/autoparallel_sat_attack.py line 111). The tools/RLL.py script is not fully optimized.
    max_workers = 8
```

## Assignment Task B Scripts - provably secure logic locking Usage:

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

### Trojan insertion - process all .bench files in `data/` with default settings - output folder is `trojan_injected`
``` python3
python3 scripts/insert_trojan.py
```

### Trojan insertion for a single file - output folder is `trojan_injected`
``` python3
python3 scripts/insert_trojan.py --bench_path data/c432.bench --trigger_size 3 --num_trojans 50
```

The two trojan scripts (have their outputs in trojan_injected directory):

Selects random rare nodes as a trigger.
Adds an AND-based trigger condition.
Introduces an XOR-based payload to modify outputs.
Generates 50 Trojan-infected files for each circuit.
Runs Atalanta to check if the Trojan can be detected.



# Assignment 2 - Stealthy Trojans
Run with single command
``` \bin\bash
    python3 scripts/all_trojan_locking.py -b data/c432.bench -k=16
```
OR

Run them separately

``` \bin\bash
    python3 scripts/antisat_trojan.py  -b data/c432.bench -k 16
    python3 scripts/corrupt_and_correct_trojan.py -b data/c432.bench -k 16
    python3 scripts/sarlock_trojan.py -b data/c432.bench -k 16

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