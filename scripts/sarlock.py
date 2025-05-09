#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import os
import sys

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import (
#     parse_bench_file,
#     defining_keyinputs,
#     insert_key_gates,
#     write_list_to_file,
# )

"""
SARLock Logic Locking Script
Injects comparator + mask logic to protect one output via SARLock technique.
"""


def parse_bench_file(bench_path: Path):
    """Parse inputs, outputs, and gates from an ISCAS-85 .bench file."""
    inputs, outputs, gates = [], [], []
    with bench_path.open('r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT("):
                inputs.append(line[len("INPUT("):-1])
            elif line.startswith("OUTPUT("):
                outputs.append(line[len("OUTPUT("):-1])
            elif '=' in line:
                gates.append(line)
    return inputs, outputs, gates


def generate_random_key(keysize: int):
    """Generate a binary key string and corresponding key-input names."""
    bits = ''.join(random.choice('01') for _ in range(keysize))
    nets = [f"keyinput{i}" for i in range(keysize)]
    return bits, nets


def build_and_tree(nodes, prefix):
    """Construct a balanced AND-tree over a list of node names."""
    gates = []
    level = 0
    current = list(nodes)
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                out = f"{prefix}_L{level}_{i//2}"
                gates.append(f"{out} = AND({current[i]}, {current[i+1]})")
                next_level.append(out)
            else:
                next_level.append(current[i])
        current = next_level
        level += 1
    return current[0], gates


def create_sarlock_logic(inputs, key_nets, key_str, target):
    """Generate SARLock comparator & mask logic (XOR+NOT for XNOR)."""
    logic = []
    # constant source
    const_inv = f"{target}_const_inv"
    logic.append(f"{const_inv} = NOT({inputs[0]})")
    zero = f"{target}_zero"
    one = f"{target}_one"
    logic.append(f"{zero} = AND({inputs[0]}, {const_inv})")
    logic.append(f"{one}  = OR({inputs[0]}, {const_inv})")

    match_nets, mask_nets = [], []
    for i, bit in enumerate(key_str):
        xi = inputs[i % len(inputs)]
        ki = key_nets[i]
        # XNOR(xi, ki)
        tmp = f"tmp_xm{i}"
        m = f"m_xnor{i}"
        logic.append(f"{tmp} = XOR({xi}, {ki})")
        logic.append(f"{m} = NOT({tmp})")
        match_nets.append(m)
        # XNOR(ki, const)
        choice = one if bit == '1' else zero
        tmp2 = f"tmp_xs{i}"
        s = f"s_xnor{i}"
        logic.append(f"{tmp2} = XOR({ki}, {choice})")
        logic.append(f"{s} = NOT({tmp2})")
        mask_nets.append(s)

    # AND-trees
    root1, t1 = build_and_tree(match_nets, "match")
    root2, t2 = build_and_tree(mask_nets,  "mask")
    logic += t1 + t2
    logic.append(f"DTL_0 = {root1}")
    logic.append(f"DTL_2 = {root2}")
    logic.append("FLIP = AND(DTL_0, DTL_2)")
    # obfuscate
    logic.append(f"{target} = XOR(FLIP, {target}_enc)")
    return logic


def sarlock_lock(bench_path: Path, keysize: int, output_path: Path):
    inputs, outputs, gates = parse_bench_file(bench_path)
    key_str, key_nets = generate_random_key(keysize)
    target = outputs[0]

    # prepare header
    header = [f"#key={key_str}"]
    header += [f"INPUT({i})" for i in inputs]
    header += [f"INPUT({k})" for k in key_nets]
    header += [f"OUTPUT({o})" for o in outputs]

    # rename original gate
    import re
    pat = re.compile(rf"^\s*{target}\s*=")
    renamed = []
    for g in gates:
        if pat.match(g):
            rhs = g.split('=',1)[1].strip()
            renamed.append(f"{target}_enc = {rhs}")
        else:
            renamed.append(g)

    # inject SARLock logic
    sar_logic = create_sarlock_logic(inputs, key_nets, key_str, target)

    # write output
    output_path.mkdir(parents=True, exist_ok=True)
    out_file = output_path / f"{bench_path.stem}_SARLock_k_{keysize}.bench"
    with out_file.open('w') as f:
        for line in header + renamed + sar_logic:
            f.write(line + '\n')

    print(f"SARLock locked circuit with Key[🔐] = {key_str} is saved to: {out_file}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)  # 2n
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    sarlock_lock(args.bench_path, args.keysize, args.output_path)


if __name__ == "__main__":
    main()
