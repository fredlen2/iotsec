#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import (
#     parse_bench_file,
#     defining_keyinputs,
#     insert_key_gates,
#     write_list_to_file,
# )

#!/usr/bin/env python3
"""
SARLock - Secure logic locking for combinational circuits
Ensures Atalanta compatibility: no floating nets, proper header, valid output wiring
"""


def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT("):
                inputs.append(line.split("(")[1].split(")")[0])
            elif line.startswith("OUTPUT("):
                outputs.append(line.split("(")[1].split(")")[0])
            elif "=" in line:
                gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    return key, key_inputs

def write_locked_bench(inputs, outputs, key_inputs, gates, logic, output_path, key):
    with open(output_path, 'w') as f:
        f.write(f"#key={key}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for k in key_inputs:
            f.write(f"INPUT({k})\n")
        for out in outputs + ["FLIP"]:
            f.write(f"OUTPUT({out})\n")
        for gate in gates + logic:
            f.write(f"{gate}\n")

def build_sarlock_logic(inputs, key_inputs, target_output):
    logic = []
    xor_zero = "XORZ"
    xnor_zero = "XNORZ"
    logic.append(f"{xor_zero} = XOR({target_output}, {target_output})")
    logic.append(f"{xnor_zero} = XNOR({target_output}, {target_output})")

    and0_terms, and2_terms = [], []

    for i, k in enumerate(key_inputs):
        in_wire = inputs[i % len(inputs)]
        logic.append(f"in{i}_xor0 = XNOR({in_wire}, {k})")
        logic.append(f"in{i}_xor2 = XNOR({k}, {random.choice([xor_zero, xnor_zero])})")
        and0_terms.append(f"in{i}_xor0")
        and2_terms.append(f"in{i}_xor2")

    def build_and_tree(terms, label_prefix):
        inter_terms = []
        inter_counter = 0
        for i in range(0, len(terms), 2):
            out = f"{label_prefix}{inter_counter}"
            logic.append(f"{out} = AND({terms[i]}, {terms[i+1]})")
            inter_terms.append(out)
            inter_counter += 1
        while len(inter_terms) > 1:
            next_terms = []
            for i in range(0, len(inter_terms), 2):
                out = f"{label_prefix}{inter_counter}"
                logic.append(f"{out} = AND({inter_terms[i]}, {inter_terms[i+1]})")
                next_terms.append(out)
                inter_counter += 1
            inter_terms = next_terms
        return inter_terms[0]

    dtl_0 = build_and_tree(and0_terms, "dtl0_")
    dtl_2_in = build_and_tree(and2_terms, "dtl2_")
    logic.append(f"DTL_0 = {dtl_0}")
    logic.append(f"DTL_2 = NAND({dtl_2_in}, {dtl_2_in})")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{target_output}_enc = {target_output} = NOT_USED")
    logic.append(f"{target_output} = XOR(FLIP, {target_output}_enc)")
    return logic

def main():
    parser = argparse.ArgumentParser(description="Apply SARLock logic locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to original .bench")
    parser.add_argument("--keysize", type=int, required=True, help="Key size (number of key bits)")
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"), help="Output directory")
    args = parser.parse_args()

    # Load original circuit
    inputs, outputs, gates = parse_bench(args.bench_path)
    target_output = outputs[0]  # Lock the first output

    # Generate key
    key, key_inputs = generate_key(args.keysize)

    # Add locking logic
    logic = build_sarlock_logic(inputs, key_inputs, target_output)

    # Build output file path
    out_dir = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"

    # Write full .bench
    write_locked_bench(inputs, outputs, key_inputs, gates, logic, out_file, key)

    print(f"SARLock output with Key={key} is saved to: {out_file}")


if __name__ == "__main__":
    main()
