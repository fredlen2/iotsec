#!/usr/bin/env python3

import argparse
from pathlib import Path
import random
import sys
import os

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

def parse_bench(input_file):
    inputs, outputs, logic = [], [], []
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("INPUT("):
                inputs.append(line[6:-1])
            elif line.startswith("OUTPUT("):
                outputs.append(line[7:-1])
            elif "=" in line:
                logic.append(line)
    return inputs, outputs, logic

def generate_key(keysize):
    key_bits = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    return key_bits, key_inputs

def build_and_tree(inputs, label):
    tree = []
    level = 0
    current = inputs
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            a = current[i]
            b = current[i+1] if i+1 < len(current) else current[i]
            out = f"{label}_L{level}_{i//2}"
            tree.append(f"{out} = AND({a}, {b})")
            next_level.append(out)
        current = next_level
        level += 1
    return current[0], tree

def inject_antisat(inputs, outputs, gates, key_inputs):
    n = len(key_inputs) // 2
    Kl1 = key_inputs[:n]
    Kl2 = key_inputs[n:]
    selected = inputs[:n]

    xor1 = [f"X1_{i} = XNOR({selected[i]}, {Kl1[i]})" for i in range(n)]
    xor2 = [f"X2_{i} = XNOR({selected[i]}, {Kl2[i]})" for i in range(n)]

    g1_root, g1_tree = build_and_tree([f"X1_{i}" for i in range(n)], "G1")
    g2_root, g2_tree = build_and_tree([f"X2_{i}" for i in range(n)], "G2")

    antisat_logic = xor1 + xor2 + g1_tree + g2_tree
    antisat_logic.append(f"ANTISAT_AND = AND({g1_root}, {g2_root})")
    antisat_logic.append("LOCK_ENABLE = NOT(ANTISAT_AND)")

    target = outputs[0]
    enc_target = f"{target}_enc"
    final_logic = []
    replaced = False

    for line in gates:
        if not replaced and line.startswith(f"{target} ="):
            rhs = line.split("=")[1].strip()
            final_logic.append(f"{enc_target} = {rhs}")
            replaced = True
        else:
            final_logic.append(line)

    final_logic += antisat_logic
    final_logic.append(f"{target} = AND(LOCK_ENABLE, {enc_target})")

    return final_logic

def write_bench(path, key, inputs, outputs, key_inputs, logic):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for k in key_inputs:
            f.write(f"INPUT({k})\n")
        for out in outputs:
            f.write(f"OUTPUT({out})\n")
        for gate in logic:
            f.write(f"{gate}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)  # Must be even
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    if args.keysize % 2 != 0:
        raise ValueError("Keysize must be even for Anti-SAT (2 * n).")

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs = generate_key(args.keysize)
    logic = inject_antisat(inputs, outputs, gates, key_inputs)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_AntiSATLock_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, outputs, key_inputs, logic)

    print(f"Anti-SAT locked circuit with Key[🔐] = {key} is saved to: {out_file}")

if __name__ == "__main__":
    main()