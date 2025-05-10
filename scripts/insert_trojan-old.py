import os
import random
import argparse

# Default directories
DATA_DIR = "data"
TROJAN_DIR = "trojan_injected"

# Ensure output directory exists
os.makedirs(TROJAN_DIR, exist_ok=True)

def parse_bench_file(file_path):
    """Parse the .bench file into sections."""
    with open(file_path, "r") as f:
        lines = f.read().splitlines()
    inputs = [line for line in lines if line.startswith("INPUT(")]
    outputs = [line for line in lines if line.startswith("OUTPUT(")]
    gates = [line for line in lines if "=" in line and not (line.startswith("INPUT(") or line.startswith("OUTPUT("))]
    return inputs, outputs, gates

def find_rare_nets(gates):
    """Extract the LHS net name from each gate."""
    return [gate.split("=")[0].strip() for gate in gates]

def insert_trojan(inputs, outputs, gates, rare_nets, trigger_size, trojan_id):
    """
    Insert a Trojan with given trigger size and trojan_id into the circuit.
    Assumes that `rare_nets` has been computed once per file.
    """
    new_gates = gates.copy()
    # Randomly select trigger nets from the precomputed list
    trigger_nets = random.sample(rare_nets, trigger_size)
    trigger_name = f"trojan_trigger_{trojan_id}"
    trigger_expr = ", ".join(trigger_nets)
    new_gates.append(f"{trigger_name} = {'BUF' if trigger_size == 1 else 'AND'}({trigger_expr})")
    
    # Trojan payload: flip a random net
    payload_target = random.choice(rare_nets)
    payload_name = f"trojan_payload_{trojan_id}"
    payload_gate = f"{payload_name} = XOR({trigger_name}, {payload_target})"
    override_gate = f"{payload_target} = BUF({payload_name})"
    
    # Remove the original definition for payload_target and append payload logic
    new_gates = [g for g in new_gates if not g.startswith(f"{payload_target} =")]
    new_gates.extend([payload_gate, override_gate])
    return new_gates

def write_bench_file(file_path, inputs, outputs, gates):
    """Write the circuit sections to a bench file in one shot."""
    content = "\n".join(inputs + outputs + gates) + "\n"
    with open(file_path, "w") as f:
        f.write(content)

def insert_trojans_in_file(file_name, trigger_size, num_trojans):
    circuit_name = file_name.replace(".bench", "")
    path = os.path.join(DATA_DIR, file_name)
    inputs, outputs, gates = parse_bench_file(path)
    rare_nets = find_rare_nets(gates)
    
    for i in range(num_trojans):
        new_gates = insert_trojan(inputs, outputs, gates, rare_nets, trigger_size, i)
        save_path = os.path.join(TROJAN_DIR, f"{circuit_name}_trojan_{i}.bench")
        write_bench_file(save_path, inputs, outputs, new_gates)
    
    print(f"Inserted {num_trojans} trojans into {file_name}")

def parse_args():
    parser = argparse.ArgumentParser(description="Insert hardware Trojans into .bench files.")
    parser.add_argument("--bench_path", type=str, help="Specific .bench file to process (in data/)")
    parser.add_argument("--trigger_size", type=int, default=3, help="Number of trigger nets (default: 3)")
    parser.add_argument("--num_trojans", type=int, default=50, help="Number of trojan-injected files to create (default: 50)")
    return parser.parse_args()

def main():
    args = parse_args()
    if args.bench_path:
        bench_file = os.path.basename(args.bench_path)
        insert_trojans_in_file(bench_file, args.trigger_size, args.num_trojans)
    else:
        for file in os.listdir(DATA_DIR):
            if file.endswith(".bench"):
                insert_trojans_in_file(file, args.trigger_size, args.num_trojans)
    print("All trojans inserted.")

if __name__ == "__main__":
    main()
