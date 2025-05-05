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

"""
SARLock Logic Locking Script (Atalanta-Compatible)
Automatically selects a target output, renames its original gate to <target>_enc,
builds a one-point function comparator per SARLock paper, and overrides the output.
Ensures no floating nets, no unsupported gates, and passes Atalanta validations.
"""

def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path) as f:
        for line in f:
            t = line.strip()
            if not t or t.startswith('#'): continue
            if t.startswith('INPUT('):
                inputs.append(t)
            elif t.startswith('OUTPUT('):
                outputs.append(t)
            elif '=' in t:
                gates.append(t)
    return inputs, outputs, gates


def generate_key(keysize):
    key = ''.join(random.choice('01') for _ in range(keysize))
    key_inputs = [f"INPUT(keyinput{i})" for i in range(keysize)]
    return key, key_inputs, [f"keyinput{i}" for i in range(keysize)]


def build_and_tree(signals, prefix):
    """
    Build a balanced binary AND-tree from `signals`, naming nodes with prefix.
    Returns (root_signal, list_of_gate_lines).
    """
    gates = []
    level = 0
    current = signals[:]
    while len(current) > 1:
        nxt, i = [], 0
        while i < len(current):
            a = current[i]
            if i+1 < len(current):
                b = current[i+1]
                node = f"{prefix}_{level}_{i//2}"
                gates.append(f"{node} = AND({a}, {b})")
                nxt.append(node)
            else:
                nxt.append(a)
            i += 2
        current = nxt
        level += 1
    return current[0], gates


def sarlock_logic(inputs, key_wires, target, encoded_target):
    """
    Builds the SARLock comparator logic using only the first len(key_wires) inputs.
    """
    logic = []
    # constant generators
    logic.append(f"pattern_0 = XOR({encoded_target}, {encoded_target})")
    logic.append(f"pattern_1 = XNOR({encoded_target}, {encoded_target})")

    eqs, neqs = [], []
    # only iterate over as many inputs as there are key bits
    for i, (w, k) in enumerate(zip(inputs, key_wires)):
        pat = 'pattern_0' if (i % 2 == 0) else 'pattern_1'
        eq = f"eq_{i} = XNOR({w}, {k})"
        neq = f"neq_{i} = XNOR({k}, {pat})"
        logic.extend([eq, neq])
        eqs.append(f"eq_{i}")
        neqs.append(f"neq_{i}")

    # build trees
    dtl0, tree0 = build_and_tree(eqs, 'dtl0')
    dtl1, tree1 = build_and_tree(neqs, 'dtl1')
    logic += tree0 + tree1

    logic.append(f"DTL_2 = NAND({dtl1}, {dtl1})")
    logic.append(f"FLIP = AND({dtl0}, DTL_2)")
    logic.append(f"{target} = XOR(FLIP, {encoded_target})")
    return logic


def write_bench(path, key, inputs, key_inputs, outputs, gates, add_logic):
    used = set()
    for line in gates + add_logic:
        if '=' in line:
            rhs = line.split('=')[1]
            tokens = rhs.replace('(', ' ').replace(')', ' ').replace(',', ' ').split()
            used.update(tokens)
    clean_out = [o for o in outputs if o[7:-1] in used]

    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for ln in inputs + key_inputs + clean_out:
            f.write(ln + '\n')
        for ln in gates:
            f.write(ln + '\n')
        for ln in add_logic:
            f.write(ln + '\n')


def main():
    parser = argparse.ArgumentParser("SARLock Logic Locking")
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)

    # choose first output as target
    target = outputs[0][7:-1]
    encoded_target = target + "_enc"

    # rename the original gate
    new_gates = []
    for g in gates:
        if g.startswith(f"{target} ="):
            rhs = g.split('=',1)[1].strip()
            new_gates.append(f"{encoded_target} = {rhs}")
        else:
            new_gates.append(g)
    gates = new_gates

    # extract raw input wire names
    wire_inputs = [ln[6:-1] for ln in inputs]
    add_logic = sarlock_logic(wire_inputs, key_wires, target, encoded_target)

    args.output_dir.mkdir(exist_ok=True)
    out = args.output_dir / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    write_bench(out, key, inputs, key_inputs, outputs, gates, add_logic)
    print(f"Locked bench written to {out} with key {key}")

if __name__ == '__main__':
    main()
