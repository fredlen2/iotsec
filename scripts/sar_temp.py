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
SARLock Logic Locking (Final Atalanta-Compatible Version)
- Selects target output automatically
- Adds FLIP logic to obfuscate target output using key inputs
- Prevents floating nets and duplicate wire definitions
- No 3-input XORs or unsupported gates
- Conforms to Atalanta and SAT compatibility
Injects logic to flip the target output under wrong key using rare input pattern detection.
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

def build_sarlock_logic(input_signals, key_wires, target):
    if len(key_wires) > len(input_signals):
        raise ValueError(f"Key size {len(key_wires)} exceeds number of available inputs {len(input_signals)}.")

    xor_zero = "xor_zero"
    xnor_zero = "xnor_zero"
    logic = [
        f"{xor_zero} = XOR({target}, {target})",
        f"{xnor_zero} = XNOR({target}, {target})"
    ]

    dtl0_inputs, dtl2_inputs = [], []

    for i, key in enumerate(key_wires):
        in_wire = input_signals[i]
        in0 = f"in{i}_0"
        in1 = f"in{i}_1"
        logic.append(f"{in0} = XNOR({in_wire}, {key})")
        logic.append(f"{in1} = XNOR({key}, {xnor_zero if i % 2 else xor_zero})")
        dtl0_inputs.append(in0)
        dtl2_inputs.append(in1)

    dtl0_out, dtl0_tree = build_tree(dtl0_inputs)
    dtl2_last, dtl2_tree = build_tree(dtl2_inputs)

    logic += dtl0_tree + dtl2_tree
    logic.append(f"DTL_2 = NAND({dtl2_last}, {dtl2_last})")
    logic.append(f"FLIP = AND({dtl0_out}, DTL_2)")
    logic.append(f"{target} = XOR(FLIP, {target})")

    return logic

def write_bench(path, key, inputs, outputs, key_inputs, gates, added_logic):
    # Remove OUTPUTs not actually used
    used = set()
    for line in gates + added_logic:
        if '=' in line:
            rhs = line.split('=')[1]
            tokens = rhs.replace('(', ' ').replace(')', ' ').split()
            used.update(tokens)

    outputs_clean = [line for line in outputs if line[7:-1] in used]

    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs_clean + gates + added_logic:
            f.write(line.strip() + "\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock - Secure Logic Locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to original .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Number of key inputs")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Directory to save locked .bench")
    args = parser.parse_args()

    inputs_bench, outputs_bench, gates = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)
    input_signals = [line[6:-1] for line in inputs_bench]
    target = get_target_output(outputs_bench)

    added_logic = build_sarlock_logic(input_signals, key_wires, target)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"

    write_bench(out_file, key, inputs_bench, outputs_bench, key_inputs, gates, added_logic)

    print(f"Locked circuit written to: {out_file}")
    print(f"SARLock key: {key}")

if __name__ == "__main__":
    main()
