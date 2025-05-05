#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import os
import random

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

"""
Anti-SAT Logic Locking (Atalanta-compatible)
Securely inserts Anti-SAT block into the target output path
Avoids 3-input gates and floating nets
"""

def parse_bench(path):
    with open(path, 'r') as f:
        lines = f.readlines()

    inputs, outputs, gates = [], [], []
    for line in lines:
        line = line.strip()
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
        elif "=" in line:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice('01') for _ in range(keysize))
    key_inputs = [f"INPUT(KEYINPUT{i})" for i in range(keysize)]
    key_wires = [f"KEYINPUT{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def get_target_output(outputs):
    return outputs[0][7:-1]

def find_gate_assignment(gates, target_signal):
    for line in gates:
        if line.startswith(f"{target_signal} "):
            return line
    return None

def inject_antisat(gates, target_output, key_wires, primary_inputs):
    # 1. Extract original output logic
    orig_gate = find_gate_assignment(gates, target_output)
    if orig_gate is None:
        raise ValueError(f"[!] Could not find assignment for protected output: {target_output}")
    
    # Rename original logic to _enc to preserve it
    orig_output_enc = f"{target_output}_enc"
    _, logic_expr = orig_gate.split("=", 1)
    new_logic = [f"{orig_output_enc} = {logic_expr.strip()}"]
    
    # Replace original assignment with protected version
    gates = [g for g in gates if not g.startswith(f"{target_output} ")]
    
    # 2. Build F and Fbar using XOR and NOT logic
    xor_f = [f"XOR_F_{i} = XOR({inp}, {key})" for i, (inp, key) in enumerate(zip(primary_inputs, key_wires))]
    xor_fbar = [f"KEYINPUT_NOT{i} = NOT({key_wires[i]})" for i in range(len(key_wires))]
    xor_fbar += [f"XOR_FBAR_{i} = XOR({inp}, KEYINPUT_NOT{i})" for i, inp in enumerate(primary_inputs)]

    # 3. Build balanced AND trees (F and Fbar)
    def build_tree(nodes, prefix):
        current = nodes[:]
        tree = []
        level = 0
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    a, b = current[i], current[i+1]
                    node = f"{prefix}_L{level}_{i//2}"
                    tree.append(f"{node} = AND({a}, {b})")
                    next_level.append(node)
                else:
                    next_level.append(current[i])
            current = next_level
            level += 1
        return current[0], tree

    f_out, f_tree = build_tree([f"XOR_F_{i}" for i in range(len(key_wires))], "F_AND")
    fbar_out, fbar_tree = build_tree([f"XOR_FBAR_{i}" for i in range(len(key_wires))], "FBAR_AND")

    # 4. Combine to generate LOCK_ENABLE = NOT(AND(F, Fbar))
    logic = xor_f + xor_fbar + f_tree + fbar_tree
    logic += [f"ANTISAT_AND = AND({f_out}, {fbar_out})"]
    logic += [f"LOCK_ENABLE = NOT(ANTISAT_AND)"]

    # 5. Protect the output
    logic += [f"{target_output} = AND(LOCK_ENABLE, {orig_output_enc})"]

    return gates + new_logic + logic

def write_bench(out_path, key, inputs, outputs, key_inputs, logic):
    with open(out_path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Anti-SAT Logic Locking")
    parser.add_argument("--bench_path", required=True, type=Path, help="Path to .bench circuit")
    parser.add_argument("--keysize", required=True, type=int, help="Key size (must be <= number of inputs)")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"), help="Output folder")
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    primary_inputs = [line[6:-1] for line in inputs]
    if args.keysize > len(primary_inputs):
        raise ValueError("Key size cannot exceed number of primary inputs")

    key, key_input_lines, key_wires = generate_key(args.keysize)
    target_output = get_target_output(outputs)
    locked_logic = inject_antisat(gates, target_output, key_wires, primary_inputs)

    # Prepare output path and filename
    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_AntiSATLock_k_{args.keysize}.bench"

    write_bench(out_file, key, inputs, outputs, key_input_lines, locked_logic)

    print(f"Anti-SAT locked circuit with Key={key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
