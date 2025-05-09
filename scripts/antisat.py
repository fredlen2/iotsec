#!/usr/bin/env python3

import argparse
from pathlib import Path
import random
# import sys
# import os

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

"""
Anti-SAT Locking Script (SLD-Compatible, Paper-Based)
Implements Type-0 Anti-SAT: Y = g(X ⊕ Kl1) ∧ g(X ⊕ Kl2)
LOCK_ENABLE = NOT(Y)
Protected output: OUT = AND(LOCK_ENABLE, OUT_enc)
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

def generate_key(n):  # n = half key size → total key bits = 2n
    key = ''.join(random.choice("01") for _ in range(2 * n))
    key_decls = [f"INPUT(KEYINPUT{i})" for i in range(2 * n)]
    key_names = [f"KEYINPUT{i}" for i in range(2 * n)]
    return key, key_decls, key_names

def get_target_output(outputs, gates):
    output_names = [line[7:-1] for line in outputs]
    defined = {line.split("=")[0].strip() for line in gates}
    for name in output_names:
        if name in defined:
            return name
    raise ValueError("[!] No output is logically assigned in the circuit.")

def build_and_tree(nodes, prefix):
    level = 0
    tree = []
    current = nodes[:]
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

def inject_antisat(inputs, key_wires, target_output, gates):
    n = len(key_wires) // 2
    Kl1 = key_wires[:n]
    Kl2 = key_wires[n:]
    pi = [line[6:-1] for line in inputs]
    selected = pi[:n]

    xor1 = [f"XOR1_{i} = XOR({selected[i]}, {Kl1[i]})" for i in range(n)]
    xor2 = [f"XOR2_{i} = XOR({selected[i]}, {Kl2[i]})" for i in range(n)]

    g1_root, g1_tree = build_and_tree([f"XOR1_{i}" for i in range(n)], "G1")
    g2_root, g2_tree = build_and_tree([f"XOR2_{i}" for i in range(n)], "G2")

    logic = xor1 + xor2 + g1_tree + g2_tree
    logic.append(f"ANTISAT_AND = AND({g1_root}, {g2_root})")
    logic.append("LOCK_ENABLE = NOT(ANTISAT_AND)")

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
        # fallback: try if target appears on RHS of any gate
        for line in reversed(gates):
            lhs, rhs = line.split("=", 1)
            if target_output in rhs:
                last_signal = lhs.strip()
                updated_gates.append(f"{target_enc} = {last_signal}")
                found = True
                break

    if not found:
        # absolute fallback: assume last gate output drives target
        last_lhs = gates[-1].split("=")[0].strip()
        updated_gates.append(f"{target_enc} = {last_lhs}")

    updated_gates.append(f"{target_output} = AND(LOCK_ENABLE, {target_enc})")
    return updated_gates + logic

def write_bench(path, key, inputs, outputs, key_inputs, logic):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Anti-SAT Locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Original .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Total key bits (2n)")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"), help="Output dir")
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    n = args.keysize // 2
    key, key_decls, key_wires = generate_key(n)
    target_output = get_target_output(outputs, gates)
    locked_logic = inject_antisat(inputs, key_wires, target_output, gates)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_path = args.output_path / f"{args.bench_path.stem}_AntiSATLock_k_{args.keysize}.bench"
    write_bench(out_path, key, inputs, outputs, key_decls, locked_logic)

    print(f"Anti-SAT locked circuit with Key={key} is saved to: {out_path}")

if __name__ == "__main__":
    main()

 
