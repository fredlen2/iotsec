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
Anti-SAT Locking Script (Type-0, Atalanta & SLD Compatible)
Implements Y = g(X ⊕ Kl1) ∧ g(X ⊕ Kl2), LOCK_ENABLE = NOT(Y)
Injects: OUT = AND(LOCK_ENABLE, OUT_enc)
"""

def parse_bench(path):
    with open(path, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
        elif "=" in line:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(n):
    key_bits = ''.join(random.choice("01") for _ in range(2 * n))
    key_inputs = [f"INPUT(KEYINPUT{i})" for i in range(2 * n)]
    key_names = [f"KEYINPUT{i}" for i in range(2 * n)]
    return key_bits, key_inputs, key_names

def get_target_output(outputs, gates):
    output_names = [line[7:-1] for line in outputs]
    defined = {line.split("=")[0].strip() for line in gates}
    for name in output_names:
        if name in defined:
            return name
    raise ValueError("No output found with assignment.")

def build_and_tree(nodes, label):
    tree = []
    current = nodes
    level = 0
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            a = current[i]
            b = current[i + 1] if i + 1 < len(current) else current[i]
            out = f"{label}_L{level}_{i//2}"
            tree.append(f"{out} = AND({a}, {b})")
            next_level.append(out)
        current = next_level
        level += 1
    return current[0], tree

def inject_antisat(pi_names, key_names, target, gates):
    n = len(key_names) // 2
    Kl1 = key_names[:n]
    Kl2 = key_names[n:]
    selected = pi_names[:n]

    xor1 = [f"XOR1_{i} = XOR({selected[i]}, {Kl1[i]})" for i in range(n)]
    xor2 = [f"XOR2_{i} = XOR({selected[i]}, {Kl2[i]})" for i in range(n)]

    g1_root, g1_tree = build_and_tree([f"XOR1_{i}" for i in range(n)], "G1")
    g2_root, g2_tree = build_and_tree([f"XOR2_{i}" for i in range(n)], "G2")

    logic = xor1 + xor2 + g1_tree + g2_tree
    logic += [
        f"ANTISAT_AND = AND({g1_root}, {g2_root})",
        "LOCK_ENABLE = NOT(ANTISAT_AND)"
    ]

    enc_signal = f"{target}_enc"
    updated_gates = []
    found = False

    for line in gates:
        if "=" not in line:
            updated_gates.append(line)
            continue

        lhs, rhs = [s.strip() for s in line.split("=", 1)]
        if lhs == target:
            updated_gates.append(f"{enc_signal} = {rhs}")
            found = True
        else:
            updated_gates.append(line)

    if not found:
        raise ValueError(f"Target output {target} assignment not found.")

    updated_gates.append(f"{target} = AND(LOCK_ENABLE, {enc_signal})")
    return updated_gates + logic

def write_bench(path, key, inputs, outputs, key_inputs, logic):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)  # 2n
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_decls, key_names = generate_key(args.keysize // 2)

    pi_names = [line[6:-1] for line in inputs]
    target_output = get_target_output(outputs, gates)

    new_logic = inject_antisat(pi_names, key_names, target_output, gates)
    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_AntiSATLock_k_{args.keysize}.bench"

    write_bench(out_file, key, inputs, outputs, key_decls, new_logic)
    print(f"Anti-SAT locked circuit with Key[🔐] ={key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
