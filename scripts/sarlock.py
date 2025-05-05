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
SARLock Logic Locking
Injects logic to flip the target output under wrong key,
based on secure pattern detection (0 and 1 triggering cases).
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

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"INPUT(keyinput{i})" for i in range(keysize)]
    key_wires = [f"keyinput{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def get_target_output(outputs):
    # Pick the first declared output by default
    return outputs[0][7:-1]  # strip OUTPUT(...)

def build_tree(inputs):
    """Recursively AND-reduce a list of signals to a single output."""
    signals = inputs[:]
    level = 0
    tree = []
    while len(signals) > 1:
        next_level = []
        for i in range(0, len(signals), 2):
            if i + 1 < len(signals):
                left, right = signals[i], signals[i + 1]
                node = f"and_dtl{level}_{len(tree)}"
                tree.append(f"{node} = AND({left}, {right})")
                next_level.append(node)
            else:
                next_level.append(signals[i])
        signals = next_level
        level += 1
    return signals[0], tree

def build_sarlock_logic(inputs, key_wires, target):
    assert len(inputs) >= len(key_wires)
    xor_zero = "xor_zero"
    xnor_zero = "xnor_zero"
    logic = [
        f"{xor_zero} = XOR({target}, {target})",
        f"{xnor_zero} = XNOR({target}, {target})"
    ]

    dtl0_inputs, dtl2_inputs = [], []

    for i, key in enumerate(key_wires):
        in_wire = inputs[i]
        in0 = f"in{i}_0"
        in1 = f"in{i}_1"
        logic.append(f"{in0} = XNOR({in_wire}, {key})")
        logic.append(f"{in1} = XNOR({key}, {xnor_zero if i % 2 else xor_zero})")
        dtl0_inputs.append(in0)
        dtl2_inputs.append(in1)

    dtl0_output, dtl0_tree = build_tree(dtl0_inputs)
    dtl2_last, dtl2_tree = build_tree(dtl2_inputs)
    dtl2_out = "DTL_2"
    logic += dtl0_tree + dtl2_tree
    logic.append(f"{dtl2_out} = NAND({dtl2_last}, {dtl2_last})")
    logic.append(f"FLIP = AND({dtl0_output}, {dtl2_out})")

    # Final XOR embedding into target output
    logic.append(f"{target} = XOR(FLIP, {target})")
    return logic

def write_bench(out_path, key, inputs, outputs, key_inputs, gates, added_logic):
    # Remove floating outputs (signals declared OUTPUT but never used)
    used_signals = set()
    for line in gates + added_logic:
        if '=' in line:
            rhs = line.split('=')[1]
            tokens = rhs.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
            used_signals.update(tokens)

    outputs_clean = [line for line in outputs if line[7:-1] in used_signals]

    with open(out_path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs_clean + gates + added_logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock Logic Locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to original .bench")
    parser.add_argument("--keysize", type=int, required=True, help="Number of key bits")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Output directory for locked .bench")
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)
    target = get_target_output(outputs)

    added_logic = build_sarlock_logic([line[6:-1] for line in inputs], key_wires, target)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"

    write_bench(out_file, key, inputs, outputs, key_inputs, gates, added_logic)

    print(f"SARLock-locked circuit with Key={key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
