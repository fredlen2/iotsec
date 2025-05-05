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


"""
SARLock Logic Locking - Atalanta-Compatible Implementation
- Uses only 2-input gates (AND, XOR, XNOR, NAND)
- Avoids floating nets
- Injects logic directly into the final output
- Adds key declaration and #key=... header
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

def extract_output_wires(outputs):
    return [line.split("(")[1].split(")")[0] for line in outputs]

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"INPUT(keyinput{i})" for i in range(keysize)]
    key_wires = [f"keyinput{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def inject_sarlock(gates, key_wires, primary_inputs, original_output):
    logic = []
    n = len(key_wires)
    pattern_0 = f"xor_zero = XOR({original_output}, {original_output})"
    pattern_1 = f"xnor_zero = XNOR({original_output}, {original_output})"
    logic.extend([pattern_0, pattern_1])

    dtl_0_terms = []
    dtl_1_terms = []
    for i in range(n):
        g = primary_inputs[i]
        k = key_wires[i]
        x0 = f"in{i}_0 = XNOR({g}, {k})"
        x1 = f"in{i}_1 = XNOR({k}, {'xor_zero' if i % 2 == 0 else 'xnor_zero'})"
        logic.extend([x0, x1])
        dtl_0_terms.append(f"in{i}_0")
        dtl_1_terms.append(f"in{i}_1")

    # Construct DTL_0 (AND-tree)
    while len(dtl_0_terms) > 1:
        a = dtl_0_terms.pop(0)
        b = dtl_0_terms.pop(0)
        new = f"and_dtl0_{len(logic)} = AND({a}, {b})"
        logic.append(new)
        dtl_0_terms.append(new.split('=')[0].strip())

    # Construct DTL_2 (NAND-tree)
    while len(dtl_1_terms) > 1:
        a = dtl_1_terms.pop(0)
        b = dtl_1_terms.pop(0)
        new = f"and_dtl2_{len(logic)} = AND({a}, {b})"
        logic.append(new)
        dtl_1_terms.append(new.split('=')[0].strip())

    dtl_0 = dtl_0_terms[0]
    dtl_2 = dtl_1_terms[0]
    dtl_2_nand = f"DTL_2 = NAND({dtl_2}, {dtl_2})"
    logic.append(dtl_2_nand)

    flip = f"FLIP = AND({dtl_0}, DTL_2)"
    logic.append(flip)

    # Final obfuscated output
    enc_out = f"{original_output}_enc = XOR(FLIP, {original_output})"
    assign_final = f"{original_output} = {original_output}_enc"
    logic.extend([enc_out, assign_final])

    return logic

def write_bench(path, key, inputs, outputs, gates, key_inputs, sarlock_logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + gates + sarlock_logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock (Atalanta-Compatible)")
    parser.add_argument("--bench_path", required=True, type=Path)
    parser.add_argument("--keysize", required=True, type=int)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    output_names = extract_output_wires(outputs)
    key, key_inputs, key_wires = generate_key(args.keysize)
    args.output_path.mkdir(exist_ok=True, parents=True)

    original_output = output_names[0]
    pi_wires = [line.split("(")[1].split(")")[0] for line in inputs][:args.keysize]
    sarlock_logic = inject_sarlock(gates, key_wires, pi_wires, original_output)

    out_file = args.output_path / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, outputs, gates, key_inputs, sarlock_logic)
    print(f"Sarlock Output with key {key} is save to: {out_file}")

if __name__ == "__main__":
    main()
