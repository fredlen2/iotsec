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

"""
SARLock implementation that works with SLD tool and matches the original paper.
"""

def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT"):
                inputs.append(line.split("(")[1].split(")")[0])
            elif line.startswith("OUTPUT"):
                outputs.append(line.split("(")[1].split(")")[0])
            elif "=" in line:
                gates.append(line)
    return inputs, outputs, gates


def generate_key(keysize):
    key_bits = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    return key_bits, key_inputs


def build_sarlock_logic(inputs, key_inputs, key_bits, target):
    logic = []
    xor0_wires = []
    xor2_wires = []

    # Build comparator (match and mismatch)
    for i, (pi, ki, bit) in enumerate(zip(inputs, key_inputs, key_bits)):
        wire0 = f"in{i}_xor0"
        logic.append(f"{wire0} = XNOR({pi}, {ki})")
        xor0_wires.append(wire0)

        const = f"logic1" if bit == "1" else "logic0"
        wire2 = f"in{i}_xor2"
        logic.append(f"{wire2} = XNOR({ki}, {const})")
        xor2_wires.append(wire2)

    logic.append(f"logic0 = XNOR({inputs[0]}, {inputs[0]})")
    logic.append(f"logic1 = XOR({inputs[0]}, {inputs[0]})")

    def build_tree(wires, prefix):
        inter = []
        temp = wires[:]
        counter = 0
        while len(temp) > 1:
            next_level = []
            for i in range(0, len(temp), 2):
                if i + 1 < len(temp):
                    out = f"{prefix}_{counter}"
                    logic.append(f"{out} = AND({temp[i]}, {temp[i+1]})")
                    next_level.append(out)
                    counter += 1
                else:
                    next_level.append(temp[i])
            temp = next_level
        return temp[0]

    dtl0 = build_tree(xor0_wires, "inter0")
    dtl2 = build_tree(xor2_wires, "inter2")

    logic.append(f"DTL_0 = {dtl0}")
    logic.append(f"DTL_2 = {dtl2}")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")
    return logic


def write_locked_bench(out_path, key_bits, inputs, outputs, key_inputs, gates, sarlock_logic, target_output):
    with open(out_path, "w") as f:
        f.write(f"#key={key_bits}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for ki in key_inputs:
            f.write(f"INPUT({ki})\n")
        for out in outputs:
            f.write(f"OUTPUT({out})\n")

        # Rename target output assignment to _enc
        for line in gates:
            if line.startswith(f"{target_output} "):
                lhs, rhs = line.split("=", 1)
                f.write(f"{lhs.strip()}_enc = {rhs.strip()}\n")
            else:
                f.write(f"{line}\n")

        for line in sarlock_logic:
            f.write(f"{line}\n")

        f.write(f"{target_output} = XOR(FLIP, {target_output}_enc)\n")


def main():
    parser = argparse.ArgumentParser(description="SARLock")
    parser.add_argument("--bench_path", type=Path, required=True, help="Input .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Number of key bits")
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"), help="Output directory")
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    key_bits, key_inputs = generate_key(args.keysize)
    target = outputs[0]

    sarlock_logic = build_sarlock_logic(inputs, key_inputs, key_bits, target)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_file = args.output_dir / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"

    write_locked_bench(out_file, key_bits, inputs, outputs, key_inputs, gates, sarlock_logic, target)

    print(f"SARLock output with Key={key_bits} is saved to: {out_file}")


if __name__ == "__main__":
    main()
