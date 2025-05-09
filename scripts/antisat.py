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

def parse_bench(input_file):
    inputs, outputs, logic_gates = [], [], []
    with open(input_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith("INPUT"):
                inputs.append(line.split("(")[1].split(")")[0])
            elif line.startswith("OUTPUT"):
                outputs.append(line.split("(")[1].split(")")[0])
            elif '=' in line:
                logic_gates.append(line)
    return inputs, outputs, logic_gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_wires = [f"keyinput{i}" for i in range(keysize)]
    return key, key_wires

def inject_antisat(inputs, outputs, gates, key_wires):
    n = len(key_wires) // 2
    xor1, xor2, and1, and2 = [], [], [], []

    for i in range(n):
        in_sig = inputs[i % len(inputs)]
        k1 = key_wires[i]
        k2 = key_wires[i + n]
        x1 = f"X1_{i}"
        x2 = f"X2_{i}"
        xor1.append(x1)
        xor2.append(x2)
        gates.append(f"{x1} = XNOR({in_sig}, {k1})")
        gates.append(f"{x2} = XNOR({in_sig}, {k2})")

    def build_and_tree(xlist, label):
        curr = xlist[:]
        lvl = 0
        tree = []
        while len(curr) > 1:
            nxt = []
            for i in range(0, len(curr), 2):
                a = curr[i]
                b = curr[i+1] if i+1 < len(curr) else curr[i]
                out = f"{label}_L{lvl}_{i//2}"
                tree.append(f"{out} = AND({a}, {b})")
                nxt.append(out)
            curr = nxt
            lvl += 1
        return curr[0], tree

    g1_root, tree1 = build_and_tree(xor1, "G1")
    g2_root, tree2 = build_and_tree(xor2, "G2")
    gates.extend(tree1 + tree2)
    gates.append(f"ANTISAT_AND = AND({g1_root}, {g2_root})")
    gates.append("LOCK_ENABLE = NOT(ANTISAT_AND)")

    target = outputs[0]
    enc_target = f"{target}_enc"
    final_gates = []
    replaced = False
    for gate in gates:
        if gate.startswith(f"{target} =") and not replaced:
            rhs = gate.split("=", 1)[1].strip()
            final_gates.append(f"{enc_target} = {rhs}")
            replaced = True
        else:
            final_gates.append(gate)
    final_gates.append(f"{target} = AND(LOCK_ENABLE, {enc_target})")

    return final_gates

def write_bench(path, key, inputs, outputs, logic):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for i in inputs:
            f.write(f"INPUT({i})\n")
        for o in outputs:
            f.write(f"OUTPUT({o})\n")
        for line in logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_wires = generate_key(args.keysize)
    locked_logic = inject_antisat(inputs, outputs, gates, key_wires)

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_AntiSAT_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, outputs, locked_logic)

    print(f"Anti-SAT locked circuit with Key[🔐] = {key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
