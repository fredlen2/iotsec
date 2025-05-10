#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import sys
import os

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# from tools.utils.utils import parse_bench_file, write_list_to_file

"""
Corrupt-and-Correct Logic Locking (CAC) Implementation
- Replaces original gate output with XOR(obfuscated, key)
- Prevents floating nets and duplicate assignments
- Conforms to paper: corrupted signal must propagate
- Compatible with Atalanta and SAT tools
"""

import argparse
import random
from pathlib import Path

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
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"INPUT(KEYINPUT{i})" for i in range(keysize)]
    key_wires = [f"KEYINPUT{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def corrupt_and_correct(gates, key_wires, keysize):
    used_idxs = set()
    corrupted_map = {}
    key_logic = []
    new_gates = []

    for i in range(keysize):
        while True:
            idx = random.randint(0, len(gates) - 1)
            if idx not in used_idxs:
                used_idxs.add(idx)
                break

        original_line = gates[idx]
        left, right = original_line.split("=")
        left = left.strip()
        right = right.strip()
        key = key_wires[i]
        corrupt_wire = f"{left}_CORRUPT"

        # Store mapping: left was corrupted
        corrupted_map[left] = corrupt_wire

        # Replace original with corrupt version and XOR
        key_logic.append(f"{corrupt_wire} = {right}")
        new_gates.append(f"{left} = XOR({corrupt_wire}, {key})")

        # Mark original gate as removed
        gates[idx] = None

    # Remove original corrupted gates
    clean_gates = [g for g in gates if g is not None]
    return clean_gates, key_logic, new_gates

def write_bench(path, key, inputs, outputs, key_inputs, logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Corrupt-and-Correct Logic Locking")
    parser.add_argument("--bench_path", required=True, type=Path, help="Path to original .bench file")
    parser.add_argument("--keysize", required=True, type=int, help="Key size for CAC locking")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Output directory for locked .bench file")
    args = parser.parse_args()

    # Prepare output path
    args.output_path.mkdir(parents=True, exist_ok=True)
    bench_name = args.bench_path.stem
    output_file = args.output_path / f"{bench_name}_CACLock_k_{args.keysize}.bench"

    # Parse and process
    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)
    clean_gates, key_logic, new_gates = corrupt_and_correct(gates, key_wires, args.keysize)

    full_logic = key_logic + clean_gates + new_gates
    write_bench(output_file, key, inputs, outputs, key_inputs, full_logic)

    print(f"CAC-locked circuit with key={key} saved to: {output_file}")

if __name__ == "__main__":
    main()
