#!/usr/bin/env python3

import argparse
from pathlib import Path
import random
import sys
import os

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file
"""
Anti-SAT Locking Script
Type-0 logic: Y = g(X ⊕ Kl1) ∧ g(X ⊕ Kl2)
LOCK_ENABLE = NOT(Y)
Protected output: OUT = AND(LOCK_ENABLE, OUT_enc)
"""

def parse_bench(path):
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("): inputs.append(line)
        elif line.startswith("OUTPUT("): outputs.append(line)
        elif "=" in line: gates.append(line)
    return inputs, outputs, gates

def generate_embedded_key(n):
    # Generate 2n bits for Kl1 and Kl2
    full_key = ''.join(random.choice("01") for _ in range(2 * n))
    Kl1 = full_key[:n]
    Kl2 = full_key[n:]
    return full_key, Kl1, Kl2

def get_target_output(outputs, gates):
    names = [o[7:-1] for o in outputs]
    defined = {g.split("=")[0].strip() for g in gates}
    for name in names:
        if name in defined:
            return name
    raise ValueError("No assigned OUTPUT found.")

def build_and_tree(signals, prefix):
    tree = []
    level = 0
    current = signals[:]
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                a, b = current[i], current[i+1]
                out = f"{prefix}_L{level}_{i//2}"
                tree.append(f"{out} = AND({a}, {b})")
                next_level.append(out)
            else:
                next_level.append(current[i])
        current = next_level
        level += 1
    return current[0], tree

def inject_antisat(inputs, target_output, gates, Kl1, Kl2):
    n = len(Kl1)
    pi = [line[6:-1] for line in inputs]
    selected = pi[:n]

    xor1, xor2 = [], []
    for i in range(n):
        xor1.append(f"XOR1_{i} = XOR({selected[i]}, {Kl1[i]})")
        xor2.append(f"XOR2_{i} = XOR({selected[i]}, {Kl2[i]})")

    g1_root, g1_tree = build_and_tree([f"XOR1_{i}" for i in range(n)], "G1")
    g2_root, g2_tree = build_and_tree([f"XOR2_{i}" for i in range(n)], "G2")

    logic = xor1 + xor2 + g1_tree + g2_tree
    logic.append(f"ANTISAT_AND = AND({g1_root}, {g2_root})")
    logic.append("LOCK_ENABLE = NOT(ANTISAT_AND)")

    # Rewire target_output
    target_enc = f"{target_output}_enc"
    updated_gates = []
    found = False

    for i, line in enumerate(gates):
        if line.startswith(f"{target_output} ="):
            rhs = line.split("=", 1)[1].strip()
            updated_gates.append(f"{target_enc} = {rhs}")
            found = True
        else:
            updated_gates.append(line)

    if not found:
        last_lhs = gates[-1].split("=")[0].strip()
        updated_gates.append(f"{target_enc} = {last_lhs}")

    updated_gates.append(f"{target_output} = AND(LOCK_ENABLE, {target_enc})")
    return updated_gates + logic

def write_bench(path, key, inputs, outputs, logic):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for line in inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Anti-SAT Logic Locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Original .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Total key bits (2n)")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"), help="Output directory")
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    n = args.keysize // 2
    key, Kl1, Kl2 = generate_embedded_key(n)
    target_output = get_target_output(outputs, gates)
    logic = inject_antisat(inputs, target_output, gates, Kl1, Kl2)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_AntiSATLock_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, outputs, logic)

    print(f"Anti-SAT locked circuit with Key={key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
