#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import os
# import sys

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import (
#     parse_bench_file,
#     defining_keyinputs,
#     insert_key_gates,
#     write_list_to_file,
# )


def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path, "r") as f:
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
    return key

def sarlock_logic(inputs, key_bits):
    keysize = len(key_bits)
    logic = []
    match_terms = []

    for i in range(keysize):
        key_wire = f"keyinput{i}"
        in_wire = inputs[i % len(inputs)]
        xnor = f"in{i}_xnor"
        logic.append(f"{xnor} = XNOR({in_wire}, {key_wire})")
        match_terms.append(xnor)

    # Generate DTL tree for match condition
    level = 0
    cur = match_terms
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur), 2):
            if i + 1 < len(cur):
                out = f"match_and_L{level}_{i//2}"
                logic.append(f"{out} = AND({cur[i]}, {cur[i+1]})")
                nxt.append(out)
            else:
                nxt.append(cur[i])
        cur = nxt
        level += 1

    logic.append(f"FLIP = {cur[0]}")
    return logic

def write_output(output_path, key_bits, inputs, outputs, gates, key_inputs, sarlock_gates, flip_target):
    with open(output_path, "w") as f:
        f.write(f"#key={key_bits}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for k in key_inputs:
            f.write(f"INPUT({k})\n")
        for out in outputs:
            f.write(f"OUTPUT({out})\n")
        for gate in gates:
            # Rename the line that defines the target output
            if gate.startswith(f"{flip_target} "):
                left, right = gate.split("=", 1)
                f.write(f"{left.strip()}_enc = {right.strip()}\n")
            else:
                f.write(f"{gate}\n")
        for line in sarlock_gates:
            f.write(f"{line}\n")
        # Final flip integration
        f.write(f"{flip_target} = XOR(FLIP, {flip_target}_enc)\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock Script")
    parser.add_argument("--bench_path", type=str, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    inputs, outputs, gates = parse_bench(args.bench_path)
    key_bits = generate_key(args.keysize)
    key_inputs = [f"keyinput{i}" for i in range(args.keysize)]

    target_output = outputs[0]  # Lock first output
    logic = sarlock_logic(inputs, key_bits)

    bench_name = Path(args.bench_path).stem
    output_file = args.output_dir / f"{bench_name}_SARLock_k_{args.keysize}.bench"

    write_output(output_file, key_bits, inputs, outputs, gates, key_inputs, logic, target_output)

    print(f"SARLock output with Key={key_bits} is saved to: {output_file}")

if __name__ == "__main__":
    main()
