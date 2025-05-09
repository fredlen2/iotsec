#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import os
import sys

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import (
#     parse_bench_file,
#     defining_keyinputs,
#     insert_key_gates,
#     write_list_to_file,
# )

"""
SARLock Logic Locking (SLD-compatible)
Injects comparator logic and flips one output when the key is incorrect.
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
    key_bits = ''.join(random.choice('01') for _ in range(keysize))
    return key_bits

def inject_sarlock_logic(inputs, key_inputs, key_bits, output_name):
    logic = []

    # Constants (SLD-compatible)
    logic.append(f"zero = AND({inputs[0]}, NOT({inputs[0]}))")
    logic.append(f"one = OR({inputs[0]}, NOT({inputs[0]}))")

    # Comparator logic
    xnor0_wires, xnor2_wires = [], []

    for i, bit in enumerate(key_bits):
        xi = inputs[i % len(inputs)]
        ki = key_inputs[i]
        in0 = f"in{i}_xor0"
        const = "one" if bit == "1" else "zero"
        in2 = f"in{i}_xor2"

        logic.append(f"{in0} = XNOR({xi}, {ki})")
        logic.append(f"{in2} = XNOR({ki}, {const})")
        xnor0_wires.append(in0)
        xnor2_wires.append(in2)

    # Build balanced AND trees for match and mismatch
    def build_and_tree(signals, prefix):
        current = signals
        level = 0
        gates = []
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    out = f"{prefix}_L{level}_{i//2}"
                    gates.append(f"{out} = AND({current[i]}, {current[i+1]})")
                    next_level.append(out)
                else:
                    next_level.append(current[i])
            current = next_level
            level += 1
        return current[0], gates

    dtl0_root, dtl0_tree = build_and_tree(xnor0_wires, "match_and")
    dtl2_root, dtl2_tree = build_and_tree(xnor2_wires, "mismatch_and")

    logic += dtl0_tree + dtl2_tree
    logic.append(f"DTL_0 = {dtl0_root}")
    logic.append(f"DTL_2 = {dtl2_root}")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")

    # Obfuscate output with FLIP
    logic.append(f"{output_name} = XOR(FLIP, {output_name}_enc)")

    return logic

def apply_sarlock(bench_path, output_dir, keysize):
    inputs, outputs, gates = parse_bench(bench_path)
    key_bits = generate_key(keysize)
    key_inputs = [f"keyinput{i}" for i in range(keysize)]

    output_name = outputs[0]  # e.g., G223GAT

    # Annotate key
    header = [f"#key={key_bits}"]

    # Write headers
    header += [f"INPUT({i})" for i in inputs]
    header += [f"INPUT({k})" for k in key_inputs]
    header += [f"OUTPUT({o})" for o in outputs]

    # Rename target output logic to *_enc
    new_gates = []
    for g in gates:
        if g.startswith(f"{output_name} "):
            rhs = g.split("=", 1)[1].strip()
            new_gates.append(f"{output_name}_enc = {rhs}")
        else:
            new_gates.append(g)

    # Inject SARLock logic
    sarlock_logic = inject_sarlock_logic(inputs, key_inputs, key_bits, output_name)

    # Final .bench content
    bench_lines = header + new_gates + sarlock_logic

    # Save
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(output_dir) / f"{Path(bench_path).stem}_SARLock_k_{keysize}.bench"
    with open(out_path, "w") as f:
        for line in bench_lines:
            f.write(line + "\n")

    print(f"SARLock output with Key={key_bits} is saved to: {out_path}")

def main():
    parser = argparse.ArgumentParser(description="Inject SARLock logic into a .bench file.")
    parser.add_argument("--bench_path", type=str, required=True, help="Path to .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Key size (number of keyinputs)")
    parser.add_argument("--output_dir", type=str, default="locked_circuits", help="Output directory (default: locked_circuits)")
    args = parser.parse_args()
    apply_sarlock(args.bench_path, args.output_dir, args.keysize)

if __name__ == "__main__":
    main()
