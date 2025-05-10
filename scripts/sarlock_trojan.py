#!/usr/bin/env python3

import argparse, random, os
import logging
import secrets
import sys
from pathlib import Path

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file


def parse_bench(path):
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line[6:-1])
        elif line.startswith("OUTPUT("):
            outputs.append(line[7:-1])
        else:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    return key, key_inputs

def build_tree(wires, prefix, gate="AND"):
    logic = []
    count = 0
    while len(wires) > 1:
        new = []
        for i in range(0, len(wires), 2):
            if i + 1 < len(wires):
                a, b = wires[i], wires[i+1]
                w = f"{prefix}_{count}_{i//2}"
                logic.append(f"{w} = {gate}({a}, {b})")
                new.append(w)
            else:
                new.append(wires[i])
        wires = new
        count += 1
    return wires[0], logic

def sarlock_trojan_logic(inputs, key_inputs, key_bits, target):
    logic = []
    match_xnors = []
    for i, kbit in enumerate(key_bits):
        pi = inputs[i % len(inputs)]
        ki = key_inputs[i]
        mid = f"match_{i}"
        logic.append(f"{mid} = XNOR({pi}, {ki})")
        match_xnors.append(mid)

    and_root, and_logic = build_tree(match_xnors, "match_and")
    logic += and_logic
    logic.append(f"trojan_flip = BUF({and_root})")
    logic.append(f"{target} = XOR({target}_enc, trojan_flip)")

    return logic

def replace_target(gates, target):
    new = []
    for g in gates:
        if g.startswith(f"{target} "):
            new.append(f"{target}_enc = {g.split('=')[1].strip()}")
        else:
            new.append(g)
    return new

def write_file(path, key, inputs, key_inputs, outputs, logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for i in inputs:
            f.write(f"INPUT({i})\n")
        for k in key_inputs:
            f.write(f"INPUT({k})\n")
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
    target = outputs[0]
    key, key_inputs = generate_key(args.keysize)
    replaced = replace_target(gates, target)
    logic = replaced + sarlock_trojan_logic(inputs, key_inputs, key, target)

    args.output_path.mkdir(exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_TroLL_SARLock_k_{args.keysize}.bench"
    write_file(out_file, key, inputs, key_inputs, outputs, logic)
    print(f"TroLL-SARLock written: {out_file}")

if __name__ == "__main__":
    main()
