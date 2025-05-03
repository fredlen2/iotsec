#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.utils.utils import parse_bench_file, write_list_to_file


def build_tree(wires, gates, prefix, suffix, op):
    level = wires.copy()
    round_idx = 0
    while len(level) > 1:
        next_level = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                a, b = level[i], level[i + 1]
                node = f"{prefix}{round_idx}_{i // 2}{suffix}"
                gates.append(f"{node} = {op}({a}, {b})")
                next_level.append(node)
            else:
                next_level.append(level[i])
        level = next_level
        round_idx += 1
    return level[0]


def sarlock_lock(inputs, outputs, gates, keysize, key_bits):
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend(f"INPUT({k})" for k in key_inputs)

    cmp0 = []
    for i, inp in enumerate(inputs[:keysize]):
        wire = f"in{i}xor_0"
        gates.append(f"{wire} = XNOR({inp}, keyinput{i})")
        cmp0.append(wire)
    root0 = build_tree(cmp0, gates, prefix="inter", suffix="_0", op="AND")
    gates.append(f"DTL_0 = {root0}")

    ref = inputs[0]
    gates.append(f"pattern_1 = XNOR({ref}, {ref})")
    gates.append(f"pattern_0 = XOR({ref}, {ref})")

    cmp2 = []
    for i, bit in enumerate(key_bits):
        wire = f"in{i}xor_2"
        pat = "pattern_1" if bit else "pattern_0"
        gates.append(f"{wire} = XNOR(keyinput{i}, {pat})")
        cmp2.append(wire)
    root2 = build_tree(cmp2, gates, prefix="inter", suffix="_2", op="NAND")
    gates.append(f"DTL_2 = {root2}")

    gates.append("FLIP = AND(DTL_0, DTL_2)")

    protected = outputs[0]
    new_gates = []
    orig_declared = False
    for g in gates:
        if g.strip().startswith(f"{protected} ="):
            rhs = g.split("=", 1)[1].strip()
            new_gates.append(f"{protected}_orig = {rhs}")
            orig_declared = True
        else:
            new_gates.append(g)
    if not orig_declared:
        raise RuntimeError(f"Could not find assignment for protected output '{protected}'")

    new_gates.append(f"{protected} = XOR(FLIP, {protected}_orig)")
    new_gates.append(f"OUTPUT({protected}_orig)")  # Ensure the orig signal is not floating

    return key_inputs, new_gates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates, _ = parse_bench_file(str(args.bench_path))
    key_bits = [random.choice([0, 1]) for _ in range(args.keysize)]

    key_inputs, locked_gates = sarlock_lock(inputs, outputs, gates, args.keysize, key_bits)

    all_lines = []
    all_lines.append(f"#key={''.join(map(str, key_bits))}")
    all_lines.extend(f"INPUT({i})" for i in inputs)
    all_lines.extend(f"INPUT({k})" for k in key_inputs)
    all_lines.extend(locked_gates)
    all_lines.extend(f"OUTPUT({o})" for o in outputs)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_file = args.bench_path.stem + f"_SARLock_k_{args.keysize}.bench"
    out_path = args.output_dir / out_file
    with open(out_path, 'w') as f:
        for line in all_lines:
            f.write(line + '\n')

    print(f"Locked circuit written to {out_path}")

if __name__ == "__main__":
    main()
