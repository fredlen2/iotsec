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
    key_bits = [random.choice("01") for _ in range(keysize)]
    key_str = ''.join(key_bits)
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    return key_str, key_inputs, key_bits

def write_bench(path, key, inputs, keyinputs, outputs, gates):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for k in keyinputs:
            f.write(f"INPUT({k})\n")
        for out in outputs:
            f.write(f"OUTPUT({out})\n")
        for g in gates:
            f.write(f"{g}\n")

def reduce_and_tree(signals, prefix):
    levels = []
    current = signals
    counter = 0
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                gate = f"{prefix}_{counter}"
                levels.append(f"{gate} = AND({current[i]}, {current[i+1]})")
                next_level.append(gate)
                counter += 1
            else:
                next_level.append(current[i])
        current = next_level
    root = f"{prefix}_root"
    levels.append(f"{root} = {current[0]}")
    return root, levels

def build_sarlock_logic(inputs, keyinputs, key_bits, target):
    xor_zero = f"XORZ = XOR({target}, {target})"
    xnor_zero = f"XNORZ = XNOR({target}, {target})"
    logic = [xor_zero, xnor_zero]

    xnor_inputs_0 = []
    xnor_inputs_2 = []

    for i, key in enumerate(keyinputs):
        pi = inputs[i % len(inputs)]
        x0 = f"in{i}_xor0"
        x2 = f"in{i}_xor2"
        pattern = "XNORZ" if key_bits[i] == "1" else "XORZ"
        logic.append(f"{x0} = XNOR({pi}, {key})")
        logic.append(f"{x2} = XNOR({key}, {pattern})")
        xnor_inputs_0.append(x0)
        xnor_inputs_2.append(x2)

    root0, tree0 = reduce_and_tree(xnor_inputs_0, "dtl0")
    root2, tree2 = reduce_and_tree(xnor_inputs_2, "dtl2")

    logic += tree0
    logic += tree2
    logic.append(f"DTL_0 = {root0}")
    logic.append(f"DTL_2 = NAND({root2}, {root2})")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{target} = XOR(FLIP, {target}_enc)")
    return logic

def sarlock_lock(bench_path, keysize, output_dir):
    inputs, outputs, gates = parse_bench(bench_path)
    key, keyinputs, key_bits = generate_key(keysize)
    target = outputs[0]

    modified = []
    for g in gates:
        if g.startswith(target + " "):
            rhs = g.split("=", 1)[1].strip()
            modified.append(f"{target}_enc = {rhs}")
        else:
            modified.append(g)

    extra_logic = build_sarlock_logic(inputs, keyinputs, key_bits, target)
    all_gates = modified + extra_logic

    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{Path(bench_path).stem}_SARLock_k_{keysize}.bench"
    write_bench(outfile, key, inputs, keyinputs, outputs, all_gates)

    print(f"SARLock locked file with key {key} is saved to: {outfile}")
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=str, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=str, default="locked_circuits")
    args = parser.parse_args()

    sarlock_lock(args.bench_path, args.keysize, args.output_dir)

if __name__ == "__main__":
    main()
