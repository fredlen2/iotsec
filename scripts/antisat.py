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
Anti-SAT Logic Locking (SLD-compatible, per-paper implementation)
Type-0: Y = g(X ⊕ Kl1) ∧ g(X ⊕ Kl2), where g is n-input AND
LOCK_ENABLE = NOT(Y)
Protected Output = AND(LOCK_ENABLE, original_output_logic)
"""

def parse_bench(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
        elif '=' in line:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(halfkeysize):
    keysize = 2 * halfkeysize
    key = ''.join(random.choice('01') for _ in range(keysize))
    key_decls = [f"INPUT(KEYINPUT{i})" for i in range(keysize)]
    return key, key_decls, keysize

def get_target_output(outputs, gates):
    output_names = [o[7:-1] for o in outputs]
    defined = {line.split("=")[0].strip() for line in gates}
    for name in output_names:
        if name in defined:
            return name
    raise ValueError("No valid protected output found.")

def inject_antisat(gates, inputs, keysize, target_output):
    half = keysize // 2
    key_l1 = [f"KEYINPUT{i}" for i in range(half)]
    key_l2 = [f"KEYINPUT{i}" for i in range(half, keysize)]
    pi = [line[6:-1] for line in inputs]

    selected = pi[:half]
    xor1 = [f"XOR1_{i} = XOR({selected[i]}, {key_l1[i]})" for i in range(half)]
    xor2 = [f"XOR2_{i} = XOR({selected[i]}, {key_l2[i]})" for i in range(half)]

    # Build AND trees
    def tree(terms, label):
        level = 0
        current = [f"{label}_{i}" for i in range(len(terms))]
        and_lines = []
        temp = terms[:]
        while len(temp) > 1:
            new_temp = []
            for i in range(0, len(temp), 2):
                if i+1 < len(temp):
                    out = f"{label}_AND_{level}_{i//2}"
                    and_lines.append(f"{out} = AND({temp[i]}, {temp[i+1]})")
                    new_temp.append(out)
                else:
                    new_temp.append(temp[i])
            temp = new_temp
            level += 1
        return temp[0], and_lines

    xor1_names = [f"XOR1_{i}" for i in range(half)]
    xor2_names = [f"XOR2_{i}" for i in range(half)]
    g1_root, g1_tree = tree(xor1_names, "G1")
    g2_root, g2_tree = tree(xor2_names, "G2")
    gates += xor1 + xor2 + g1_tree + g2_tree
    gates.append(f"ANTISAT_AND = AND({g1_root}, {g2_root})")
    gates.append("LOCK_ENABLE = NOT(ANTISAT_AND)")

    # Protect the output
    target_enc = f"{target_output}_enc"
    for i, g in enumerate(gates):
        if g.startswith(f"{target_output} ="):
            gates[i] = f"{target_enc} = {g.split('=')[1].strip()}"
            break
    gates.append(f"{target_output} = AND(LOCK_ENABLE, {target_enc})")
    return gates

def write_bench(out_path, key, inputs, outputs, key_inputs, gates):
    with open(out_path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + gates:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Antisat logic locker")
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    args.output_path.mkdir(parents=True, exist_ok=True)
    name = args.bench_path.stem
    out_file = args.output_path / f"{name}_AntiSATLock_k_{args.keysize}.bench"

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs, keysize = generate_key(args.keysize)
    target = get_target_output(outputs, gates)
    updated_gates = inject_antisat(gates, inputs, keysize, target)
    write_bench(out_file, key, inputs, outputs, key_inputs, updated_gates)

    print(f"Anti-SAT locked circuit with Key={key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
