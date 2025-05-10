#!/usr/bin/env python3

import argparse, random
import logging
import secrets
import sys
from pathlib import Path

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file


def parse_bench(path):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip()]
    ins, outs, gates = [], [], []
    for l in lines:
        if l.startswith("INPUT("): ins.append(l[6:-1])
        elif l.startswith("OUTPUT("): outs.append(l[7:-1])
        else: gates.append(l)
    return ins, outs, gates

def generate_key_pattern(k):
    key = ''.join(random.choice("01") for _ in range(k))
    fixed = ''.join(random.choice("01") for _ in range(k))
    key_ins = [f"keyinput{i}" for i in range(k)]
    return key, fixed, key_ins

def xor_const_layer(ins, bits, prefix):
    logic, out = [], []
    for i, (pi, b) in enumerate(zip(ins, bits)):
        const = "one" if b == "1" else "zero"
        w = f"{prefix}_xor_{i}"
        logic.append(f"{w} = XNOR({pi}, {const})")
        out.append(w)
    return out, logic

def xor_key_layer(ins, keys, prefix):
    logic, out = [], []
    for i, (pi, ki) in enumerate(zip(ins, keys)):
        w = f"{prefix}_xor_{i}"
        logic.append(f"{w} = XOR({pi}, {ki})")
        out.append(w)
    return out, logic

def build_tree(wires, prefix):
    logic = []
    layer = 0
    while len(wires) > 1:
        nxt = []
        for i in range(0, len(wires), 2):
            if i + 1 < len(wires):
                a, b = wires[i], wires[i+1]
                w = f"{prefix}_l{layer}_{i//2}"
                logic.append(f"{w} = AND({a}, {b})")
                nxt.append(w)
            else:
                nxt.append(wires[i])
        wires = nxt
        layer += 1
    logic.append(f"{prefix}_out = BUF({wires[0]})")
    return f"{prefix}_out", logic

def cac_trojan_logic(ins, key_ins, key_bits, fixed_bits, tgt):
    logic = [
        "zero_not = NOT(G1GAT)", "zero = AND(G1GAT, zero_not)",
        "one_not = NOT(G1GAT)", "one = NAND(G1GAT, one_not)"
    ]

    key_xor_out, key_logic = xor_key_layer(ins, key_ins, "key")
    fixed_xor_out, fixed_logic = xor_const_layer(ins, fixed_bits, "fixed")

    key_tree_out, key_tree = build_tree(key_xor_out, "key_dtl")
    fixed_tree_out, fixed_tree = build_tree(fixed_xor_out, "fixed_dtl")

    logic += key_logic + fixed_logic + key_tree + fixed_tree
    logic.append(f"flip = OR({key_tree_out}, {fixed_tree_out})")
    logic.append(f"ccrpt = XOR({tgt}_enc, {fixed_tree_out})")
    logic.append(f"{tgt} = XOR(ccrpt, flip)")
    return logic

def replace_target(gates, tgt):
    return [f"{tgt}_enc = {l.split('=')[1].strip()}" if l.startswith(f"{tgt} ") else l for l in gates]

def write(path, key, ins, key_ins, outs, logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for i in ins: f.write(f"INPUT({i})\n")
        for k in key_ins: f.write(f"INPUT({k})\n")
        for o in outs: f.write(f"OUTPUT({o})\n")
        for l in logic: f.write(f"{l}\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bench_path", type=Path, required=True)
    p.add_argument("--keysize", type=int, required=True)
    p.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = p.parse_args()

    ins, outs, gates = parse_bench(args.bench_path)
    tgt = outs[0]
    key, fixed, key_ins = generate_key_pattern(args.keysize)
    logic = replace_target(gates, tgt) + cac_trojan_logic(ins, key_ins, key, fixed, tgt)

    args.output_path.mkdir(exist_ok=True)
    path = args.output_path / f"{args.bench_path.stem}_TroLL_CAC_k_{args.keysize}.bench"
    write(path, key, ins, key_ins, outs, logic)
    print(f"TroLL-CAC written: {path}")

if __name__ == "__main__":
    main()
