#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import sys
import os

# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from tools.utils.utils import parse_bench_file, write_list_to_file

"""
Corrupt-and-Correct Logic Locking
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

def extract_gate_outputs(gates):
    return {line.split("=")[0].strip() for line in gates}

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_decls = [f"INPUT(KEYINPUT{i})" for i in range(keysize)]
    key_wires = [f"KEYINPUT{i}" for i in range(keysize)]
    return key, key_decls, key_wires

def corrupt_and_correct(gates, key_wires, keysize, outputs_set):
    new_gates = []
    key_logic = []
    extra_outputs = []
    used_idxs = set()

    for i in range(keysize):
        while True:
            idx = random.randint(0, len(gates) - 1)
            if idx not in used_idxs:
                used_idxs.add(idx)
                break

        original_gate = gates[idx]
        left, right = original_gate.split("=")
        left = left.strip()
        right = right.strip()

        corrupted_wire = f"{left}_CORRUPT"
        key = key_wires[i]

        key_logic.append(f"{corrupted_wire} = {right}")
        new_gates.append(f"{left} = XOR({corrupted_wire}, {key})")

        if left not in outputs_set:
            extra_outputs.append(f"OUTPUT({left})")

    return new_gates, key_logic, extra_outputs

def write_bench(path, key, inputs, outputs, gates, key_inputs, key_logic, corrupted_gates, extra_outputs):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + extra_outputs + key_logic + gates + corrupted_gates:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Corrupt-and-Correct Logic Locking (with key header)")
    parser.add_argument("--bench_path", required=True, type=Path, help="Path to original .bench file")
    parser.add_argument("--keysize", required=True, type=int, help="Number of key inputs to use")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Directory for locked circuit output")

    args = parser.parse_args()

    args.output_path.mkdir(parents=True, exist_ok=True)
    bench_name = args.bench_path.stem
    output_file = args.output_path / f"{bench_name}_CACLock_k_{args.keysize}.bench"

    inputs, outputs, gates = parse_bench(args.bench_path)
    output_set = {line.split("(")[1].split(")")[0] for line in outputs}
    key, key_inputs_decl, key_wires = generate_key(args.keysize)

    corrupted_gates, key_logic, extra_outputs = corrupt_and_correct(
        gates, key_wires, args.keysize, output_set
    )

    write_bench(output_file, key, inputs, outputs, gates, key_inputs_decl, key_logic, corrupted_gates, extra_outputs)

    print(f"CAC-locked circuit with key={key} written to: {output_file}")

if __name__ == "__main__":
    main()
