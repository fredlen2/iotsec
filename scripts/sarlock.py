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
SARLock Logic Locking (Final Atalanta-Compatible Version - Flattened Tree, Unique Names)
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

def build_flat_and_tree(inputs, prefix):
    nodes = []
    inter = []
    counter = 0
    for i in range(0, len(inputs), 2):
        if i + 1 < len(inputs):
            n = f"{prefix}_{counter}"
            nodes.append(f"{n} = AND({inputs[i]}, {inputs[i+1]})")
            inter.append(n)
            counter += 1
    while len(inter) > 2:
        next_layer = []
        for i in range(0, len(inter), 2):
            if i + 1 < len(inter):
                n = f"{prefix}_{counter}"
                nodes.append(f"{n} = AND({inter[i]}, {inter[i+1]})")
                next_layer.append(n)
                counter += 1
        inter = next_layer
    root = f"{prefix}_root"
    nodes.append(f"{root} = AND({inter[0]}, {inter[1]})")
    return root, nodes

def build_sarlock_logic(inputs, key_wires, target):
    logic = []
    xor_zero = "XORZ = XOR({0}, {0})".format(target)
    xnor_zero = "XNORZ = XNOR({0}, {0})".format(target)
    logic.extend([xor_zero, xnor_zero])

    and_inputs_0 = []
    and_inputs_2 = []

    for i, key in enumerate(key_wires):
        xi0 = f"in{i}_xor0"
        logic.append(f"{xi0} = XNOR({inputs[i]}, {key})")
        and_inputs_0.append(xi0)

        pattern = "XNORZ" if i % 2 else "XORZ"
        xi2 = f"in{i}_xor2"
        logic.append(f"{xi2} = XNOR({key}, {pattern})")
        and_inputs_2.append(xi2)

    dtl0, tree0 = build_flat_and_tree(and_inputs_0, "inter0")
    dtl2, tree2 = build_flat_and_tree(and_inputs_2, "inter2")

    logic.extend(tree0 + tree2)
    logic.append(f"DTL_0 = {dtl0}")
    logic.append(f"DTL_2 = {dtl2}")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{target} = XOR(FLIP, {target}_enc)")

    return logic

def replace_target_assignment(gates, target):
    modified = []
    for g in gates:
        if g.startswith(target + " "):
            rhs = g.split("=", 1)[1].strip()
            modified.append(f"{target}_enc = {rhs}")
        else:
            modified.append(g)
    return modified

def write_bench(path, key, inputs, outputs, key_inputs, gates, added_logic):
    used = set()
    for line in gates + added_logic:
        if '=' in line:
            rhs = line.split('=')[1]
            tokens = rhs.replace('(', ' ').replace(')', ' ').split()
            used.update(tokens)
    outputs_clean = [o for o in outputs if o[7:-1] in used]
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs_clean + gates + added_logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs_bench, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)
    input_wires = [line[6:-1] for line in inputs_bench]
    target = get_target_output(outputs)

    gates = replace_target_assignment(gates, target)
    added_logic = build_sarlock_logic(input_wires, key_wires, target)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_path = args.output_path / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    write_bench(out_path, key, inputs_bench, outputs, key_inputs, gates, added_logic)

    print(f"Sarlock Output with key={key} is saved to: {out_path}")

if __name__ == "__main__":
    main()
