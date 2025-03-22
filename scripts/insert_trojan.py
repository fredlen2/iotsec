import argparse
import random
import subprocess
import os

def parse_bench_file(file_path):
    """Parses a .bench file and extracts inputs, outputs, and gate definitions."""
    inputs, outputs, gates = [], [], []
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("INPUT"):
                inputs.append(line)
            elif line.startswith("OUTPUT"):
                outputs.append(line)
            elif "=" in line:
                gates.append(line)
    return inputs, outputs, gates

def insert_trojan_logic(gates, trigger_size):
    """Inserts a hardware Trojan with a fixed trigger size."""
    rare_nodes = random.sample(gates, min(trigger_size, len(gates)))  # Select rare nodes
    trigger_label = "Trojan_Trigger"
    
    # Create trigger logic using AND of rare nodes
    trigger_expr = f"{trigger_label} = AND({', '.join([g.split('=')[0].strip() for g in rare_nodes])})"
    
    # Modify an output gate to be affected by the Trojan payload
    target_gate = random.choice(gates)
    target_gate_name = target_gate.split("=")[0].strip()
    payload_expr = f"{target_gate_name} = XOR({trigger_label}, {target_gate_name})"
    
    # Add Trojan logic
    gates.append(trigger_expr)
    gates.append(payload_expr)
    return gates

def write_trojan_bench(file_path, inputs, outputs, gates):
    """Writes the modified benchmark file with a Trojan."""
    with open(file_path, "w") as file:
        for inp in inputs:
            file.write(inp + "\n")
        for out in outputs:
            file.write(out + "\n")
        for gate in gates:
            file.write(gate + "\n")

def run_atalanta(test_file):
    """Runs Atalanta to check if the Trojan is detected."""
    try:
        command = f"./atalanta -t {test_file}"
        subprocess.run(command, shell=True, check=True)
        print(f"Atalanta test pattern generated for {test_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error running Atalanta: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_path", type=str, help="Path to the original benchmark file")
    parser.add_argument("--trigger_size", type=int, required=True, help="Number of rare nodes for the trigger")
    parser.add_argument("--num_trojans", type=int, default=50, help="Number of Trojan-infected files to generate")
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench_file(args.bench_path)

    base_name = args.bench_path.replace(".bench", "")

    for i in range(args.num_trojans):
        modified_gates = insert_trojan_logic(gates[:], args.trigger_size)  # Copy list before modification
        trojan_file = f"{base_name}_Trojan_{i}.bench"
        write_trojan_bench(trojan_file, inputs, outputs, modified_gates)
        print(f"Generated {trojan_file}")

        # Run Atalanta to check for Trojan detection
        run_atalanta(trojan_file)

if __name__ == "__main__":
    main()
