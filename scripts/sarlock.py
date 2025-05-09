#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
# import os
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
    key_bits = ''.join(random.choice("01") for _ in range(keysize))
    key_decls = [f"INPUT(keyinput{i})" for i in range(keysize)]
    key_names = [f"keyinput{i}" for i in range(keysize)]
    return key_bits, key_decls, key_names

def build_and_tree(signals, prefix):
    tree = []
    level = 0
    while len(signals) > 1:
        next_level = []
        for i in range(0, len(signals), 2):
            if i + 1 < len(signals):
                out = f"{prefix}_L{level}_{i//2}"
                tree.append(f"{out} = AND({signals[i]}, {signals[i+1]})")
                next_level.append(out)
            else:
                next_level.append(signals[i])
        signals = next_level
        level += 1
    return signals[0], tree

def inject_sarlock(inputs, outputs, gates, keysize, key_bits, key_inputs, key_names):
    # Target output to modify
    target_output = outputs[0]

    # Rename its logic to <output>_enc
    new_gates = []
    replaced = False
    for gate in gates:
        if gate.startswith(target_output + " "):
            left, right = gate.split("=", 1)
            new_gates.append(f"{target_output}_enc = {right.strip()}")
            replaced = True
        else:
            new_gates.append(gate)
    if not replaced:
        raise ValueError(f"Target output {target_output} not found in logic.")

    # XNOR comparator for inputs vs key
    xnor_signals = []
    logic = []
    for i, k in enumerate(key_bits):
        xnor_sig = f"in{i}_xnor"
        logic.append(f"{xnor_sig} = XNOR({inputs[i % len(inputs)]}, {key_names[i]})")
        xnor_signals.append(xnor_sig)

    # AND tree on the comparator results
    flip_root, flip_tree = build_and_tree(xnor_signals, "match_and")
    logic += flip_tree
    logic.append(f"FLIP = {flip_root}")

    # Final output replacement
    logic.append(f"{target_output} = XOR(FLIP, {target_output}_enc)")
    return new_gates + logic

def write_locked_bench(path, key, inputs, outputs, key_inputs, logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock logic locker")
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    key_bits, key_input_decls, key_input_names = generate_key(args.keysize)

    modified_logic = inject_sarlock(
        inputs, outputs, gates, args.keysize, key_bits, key_input_decls, key_input_names
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    write_locked_bench(out_path, key_bits, [f"INPUT({x})" for x in inputs], [f"OUTPUT({x})" for x in outputs], key_input_decls, modified_logic)

    print(f"SARLock output with Key={key_bits} is saved to: {out_path}")

if __name__ == "__main__":
    main()
