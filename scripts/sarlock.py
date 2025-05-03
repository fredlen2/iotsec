#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
sys.path.insert(0, str(Path(__file__).parents[1]))
from tools.utils.utils import parse_bench_file, write_list_to_file


def build_tree(wires, gates, prefix, suffix, op):
    """
    Build a balanced binary tree of gates combining `wires` with `op` (AND/NAND).
    Adds intermediate nodes to `gates` and returns the name of the final root node.
    """
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
    """
    Implements SARLock: random key, dual-tree comparator, and single-bit output flip.
    - Comparator tree (DTL_0) uses XNOR + AND for input==key match.
    - Pattern tree (DTL_2) uses XNOR + NAND for key!=pattern match.
    - Final FLIP = AND(DTL_0, DTL_2).
    """
    # Declare key inputs
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend(f"INPUT({k})" for k in key_inputs)

    # 1) Input vs key: XNOR comparators
    cmp0 = []
    for i, (inp, bit) in enumerate(zip(inputs, key_inputs)):
        wire = f"in{i}xor_0"
        gates.append(f"{wire} = XNOR({inp}, {bit})")
        cmp0.append(wire)
    # AND-tree for DTL_0
    root0 = build_tree(cmp0, gates, prefix="inter", suffix="_0", op="AND")
    gates.append(f"DTL_0 = {root0}")

    # 2) Define constant patterns using first input as reference
    ref = inputs[0]
    gates.append(f"pattern_1 = XNOR({ref}, {ref})")  # constant 1
    gates.append(f"pattern_0 = XOR({ref}, {ref})")   # constant 0

    # Key vs pattern: XNOR comparators
    cmp2 = []
    for i, bit in enumerate(key_bits):
        wire = f"in{i}xor_2"
        pat = "pattern_1" if bit == 1 else "pattern_0"
        gates.append(f"{wire} = XNOR(keyinput{i}, {pat})")
        cmp2.append(wire)
    # NAND-tree for DTL_2
    root2 = build_tree(cmp2, gates, prefix="inter", suffix="_2", op="NAND")
    gates.append(f"DTL_2 = {root2}")

    # 3) Final flip signal
    gates.append("FLIP = AND(DTL_0, DTL_2)")

    # 4) Protect first output
    protected = outputs[0]
    new_gates = []
    for g in gates:
        if g.startswith(f"{protected} ="):
            expr = g.split("=", 1)[1].strip()
            new_gates.append(f"{protected}_orig = {expr}")
        else:
            new_gates.append(g)
    new_gates.append(f"{protected} = XOR(FLIP, {protected}_orig)")

    return key_inputs, new_gates


def main():
    parser = argparse.ArgumentParser(description="Apply SARLock to bench files.")
    parser.add_argument("--bench_path", type=Path, required=True,
                        help="Input .bench file path.")
    parser.add_argument("--keysize", type=int, required=True,
                        help="Number of key bits to generate.")
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"),
                        help="Directory to save locked circuits.")
    args = parser.parse_args()

    # Parse original circuit
    inputs, outputs, gates, _ = parse_bench_file(str(args.bench_path))

    # Generate a random key
    key_bits = [random.choice([0, 1]) for _ in range(args.keysize)]
    key_str = ''.join(str(b) for b in key_bits)

    # Lock the circuit
    key_inputs, locked_gates = sarlock_lock(inputs, outputs, gates, args.keysize, key_bits)

    # Assemble full file content
    all_lines = []
    all_lines.append(f"#key={key_str}")
    all_lines.extend(f"INPUT({i})" for i in inputs)
    all_lines.extend(locked_gates)
    all_lines.extend(f"OUTPUT({o})" for o in outputs)

    # Write to file
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_file = args.bench_path.stem + f"_SARLock_k_{args.keysize}.bench"
    out_path = args.output_dir / out_file
    write_list_to_file(all_lines, str(out_path), key_bits)
    print(f"Locked circuit written to {out_path}")

if __name__ == "__main__":
    main()
