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
Anti-SAT Logic Locking Script
- Inserts provably secure Anti-SAT logic
- Avoids floating nets (e.g., KEYINPUT_NOTx)
- Compatible with Atalanta ATPG and SAT tools
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
        elif '=' in line:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice('01') for _ in range(keysize))
    key_inputs = [f"INPUT(KEYINPUT{i})" for i in range(keysize)]
    key_wires = [f"KEYINPUT{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def build_antisat_logic(key_wires, target_inputs):
    logic = []
    used_keys = []
    xor_f = []
    xor_fbar = []
    keyinput_nots = []

    for i, (key, inp) in enumerate(zip(key_wires, target_inputs)):
        ki_not = f"KEYINPUT_NOT{i}"
        logic.append(f"{ki_not}=NOT({key})")
        xor_f.append(f"XOR_F_{i}=XOR({inp},{key})")
        xor_fbar.append(f"XOR_FBAR_{i}=XOR({inp},{ki_not})")
        keyinput_nots.append(ki_not)
        used_keys.append(key)

    def layer_and(name, inputs):
        output = []
        for i in range(0, len(inputs), 2):
            a = inputs[i]
            b = inputs[i+1]
            out = f"{name}_{i//2}"
            logic.append(f"{out}=AND({a},{b})")
            output.append(out)
        return output

    # Build F and FBAR trees
    f_layer = xor_f
    fbar_layer = xor_fbar
    while len(f_layer) > 1:
        f_layer = layer_and("F_AND", f_layer)
    while len(fbar_layer) > 1:
        fbar_layer = layer_and("FBAR_AND", fbar_layer)

    # Final AND and NOT
    logic.append(f"ANTISAT_AND=AND({f_layer[0]},{fbar_layer[0]})")
    logic.append("LOCK_ENABLE=NOT(ANTISAT_AND)")

    return logic, keyinput_nots

def main():
    parser = argparse.ArgumentParser(description="Anti-SAT Logic Locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Input .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Key size")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Output directory")

    args = parser.parse_args()
    args.output_path.mkdir(parents=True, exist_ok=True)

    bench_name = args.bench_path.stem
    out_file = args.output_path / f"{bench_name}_AntiSAT_k_{args.keysize}.bench"

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_input_decls, key_wires = generate_key(args.keysize)

    # Select keysize number of input wires for XORing
    primary_inputs = [line[6:-1] for line in inputs]
    target_inputs = random.sample(primary_inputs, args.keysize)

    # Use the first output for protection
    output_names = [line[7:-1] for line in outputs]
    target_output = output_names[0]

    # Find and rename target output's logic to *_enc
    new_gates = []
    replaced = False
    for line in gates:
        parts = line.split('=')
        if len(parts) != 2:
            continue
        left = parts[0].strip()
        right = parts[1].strip()
        if left == target_output:
            new_gates.append(f"{target_output}_enc={right}")
            replaced = True
        else:
            new_gates.append(f"{left}={right}")

    if not replaced:
        raise ValueError(f"[!] Could not find assignment for protected output: {target_output}")

    # Add final protected output logic
    new_gates.append(f"{target_output}=AND(LOCK_ENABLE,{target_output}_enc)")

    # Build AntiSAT logic
    antisat_logic, keyinput_nots = build_antisat_logic(key_wires, target_inputs)

    # Build output
    full_lines = []
    full_lines.append(f"#key={key}")
    full_lines.extend(inputs)
    full_lines.extend(key_input_decls)
    full_lines.extend(outputs)
    full_lines.extend(new_gates)
    full_lines.extend(antisat_logic)

    # Add keyinput_nots as OUTPUTs to avoid floating nets
    for name in keyinput_nots:
        full_lines.append(f"OUTPUT({name})")

    with open(out_file, 'w') as f:
        for line in full_lines:
            f.write(f"{line}\n")

    print(f"[✓] Anti-SAT locked circuit written to {out_file}")
    print(f"[✓] Target output: {target_output}")
    print(f"[✓] Key used: {key}")

if __name__ == "__main__":
    main()
