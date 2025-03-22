
Ensure all directories and files exist
mkdir -p config data locked_circuits results tools
touch config/circuits.json  # If not already present
touch results/sat_attack.log  # If not already present

create a .venv directory in your project folder and activate it with the second line code.
# Sudo issues run these to create the .venv
python3 -m pip install --user virtualenv
python3 -m virtualenv .venv

# No sudo issues
python3 -m venv .venv

source .venv/bin/activate


python3 scripts/gen_circuits_json.py

python3 scripts/automate_sat_attack.py



python3 tools/sarlock.py c432.bench --keysize 16
python3 tools/antisat.py c432.bench --keysize 16
python3 tools/corrupt_and_correct.py c432.bench --keysize 16




python3 insert_trojan.py c432.bench --trigger_size 3 --num_trojans 50

Hardware Trojan Design
A minimal Trojan consists of:

Trigger logic – A set of rare nodes (inputs) that activate the Trojan.
Payload logic – The actual malicious modification in the circuit.
Integration – The Trojan must affect the circuit output when activated.
Python Script: insert_trojan.py
This script:

Selects random rare nodes as a trigger.
Adds an AND-based trigger condition.
Introduces an XOR-based payload to modify outputs.
Generates 50 Trojan-infected files for each circuit.
Runs Atalanta to check if the Trojan can be detected.