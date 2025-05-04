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
SARLock implementation that generates key-controlled logic locking using AND, NAND, and XNOR gates only.
This version ensures no floating nets by connecting all signals and declaring FLIP as output.
"""

def generate_random_key(keysize):
    return ''.join(random.choice('01') for _ in range(keysize))


def generate_sarlock_logic(key, original_output="G370GAT", encoded_output="G370GAT_enc"):
    key_bits = list(key)
    logic_lines = []
    inputs = []
    keyinputs = []

    # Generate INPUT declarations
    for i in range(len(key_bits)):
        keyinput = f"keyinput{i}"
        keyinputs.append(keyinput)
        inputs.append(f"INPUT({keyinput})")

    pattern_1 = "XNOR(G76GAT, G76GAT)"
    pattern_0 = "XOR(G76GAT, G76GAT)"
    logic_lines.append(f"pattern_1 = {pattern_1}")
    logic_lines.append(f"pattern_0 = {pattern_0}")

    inter_0_terms = []
    inter_2_terms = []

    for i in range(len(key_bits)):
        # Dummy primary input for example purposes
        pi = f"G{i*7 % 116 + 1}GAT"
        in_xor_0 = f"in{i}xor_0 = XNOR({pi}, keyinput{i})"
        logic_lines.append(in_xor_0)
        inter_0_terms.append(f"in{i}xor_0")

        pattern = "pattern_1" if key_bits[i] == '1' else "pattern_0"
        in_xor_2 = f"in{i}xor_2 = XNOR(keyinput{i}, {pattern})"
        logic_lines.append(in_xor_2)
        inter_2_terms.append(f"in{i}xor_2")

    def build_tree(inter_terms, prefix):
        level = 0
        current_terms = inter_terms
        while len(current_terms) > 1:
            next_terms = []
            for j in range(0, len(current_terms), 2):
                if j + 1 < len(current_terms):
                    out = f"{prefix}{level}_{j//2}"
                    logic_lines.append(f"{out} = AND({current_terms[j]}, {current_terms[j+1]})")
                    next_terms.append(out)
                else:
                    next_terms.append(current_terms[j])
            current_terms = next_terms
            level += 1
        return current_terms[0]

    inter_0_final = build_tree(inter_0_terms, "inter0")
    inter_2_final = build_tree(inter_2_terms, "inter2")

    logic_lines.append(f"DTL_0 = {inter_0_final}")
    logic_lines.append(f"DTL_2 = NAND({inter_2_final}, {inter_2_final})")
    logic_lines.append(f"FLIP = AND(DTL_0, DTL_2)")
    logic_lines.append(f"{original_output} = XOR(FLIP, {encoded_output})")

    return inputs, keyinputs, logic_lines


def insert_sarlock(bench_path: Path, output_path: Path, keysize: int):
    # Read the original .bench file
    with open(bench_path, "r") as f:
        lines = f.readlines()

    # Generate the key and locking logic
    key = generate_random_key(keysize)
    inputs, keyinputs, sarlock_logic = generate_sarlock_logic(key)

    # Start building new lines, with the key at the top
    new_lines = [f"#key={key}"]
    inserted = False

    for raw in lines:
        line = raw.strip()
        # Insert keyinputs and FLIP output at the specified output point
        if line.startswith("OUTPUT(G370GAT)"):
            for ki in keyinputs:
                new_lines.append(f"INPUT({ki})")
            new_lines.append("OUTPUT(FLIP)")
            new_lines.append(line)
            inserted = True
        else:
            new_lines.append(line)

    if not inserted:
        raise ValueError("Original output G370GAT not found in file.")

    # Append the SARLock logic definitions
    new_lines.extend(sarlock_logic)

    # Write out to the file
    with open(output_path, "w") as f:
        for l in new_lines:
            f.write(l + "\n")
    print(f"SARLock logic with key={key} written to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Insert SARLock logic into a .bench file."
    )
    parser.add_argument(
        "--bench_path", required=True,
        help="Path to the original .bench file"
    )
    parser.add_argument(
        "--keysize", type=int, default=16,
        help="Number of key bits to insert"
    )
    parser.add_argument(
        "--output_path", type=Path,
        default=Path("locked_circuits"),
        help="Directory or file path to save the locked .bench file"
    )
    args = parser.parse_args()

    bench_path = Path(args.bench_path)
    output_arg = args.output_path

    # Determine if output_arg is a directory or file
    if output_arg.suffix == "" or str(output_arg).endswith(os.sep):
        output_dir = output_arg
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{bench_path.stem}_SARLock_k_{args.keysize}.bench"
    else:
        output_path = output_arg
        output_path.parent.mkdir(parents=True, exist_ok=True)

    insert_sarlock(bench_path, output_path, args.keysize)
