#!/usr/bin/env python3

import argparse, random
import logging
import secrets
from pathlib import Path
import sys

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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

def generate_key(k):
    key = ''.join(random.choice("01") for _ in range(k))
    keys = [f"keyinput{i}" for i in range(k)]
    return key, keys

def build_tree(wires, prefix, gate="AND"):
    logic = []
    level = 0
    while len(wires) > 1:
        nxt = []
        for i in range(0, len(wires), 2):
            if i + 1 < len(wires):
                a, b = wires[i], wires[i+1]
                w = f"{prefix}_{level}_{i//2}"
                logic.append(f"{w} = {gate}({a}, {b})")
                nxt.append(w)
            else:
                nxt.append(wires[i])
        wires = nxt
        level += 1
    logic.append(f"{prefix}_final = BUF({wires[0]})")
    return f"{prefix}_final", logic

def antisat_trojan_logic(inputs, keys, target):
    assert len(keys) % 2 == 0
    n = len(keys) // 2
    logic = []
    g_terms, gb_terms = [], []

    for i in range(n):
        pi = inputs[i % len(inputs)]
        k1, k2 = keys[i], keys[i+n]
        x1, x2 = f"xor1_{i}", f"xor2_{i}"
        logic += [f"{x1} = XOR({pi}, {k1})", f"{x2} = XOR({pi}, {k2})"]
        g_terms.append(x1)
        gb_terms.append(x2)

    g_root, g_logic = build_tree(g_terms, "g_and", "AND")
    gb_root, gb_logic = build_tree(gb_terms, "g_nand", "NAND")
    logic += g_logic + gb_logic
    logic.append(f"trojan_sig = AND({g_root}, {gb_root})")
    logic.append(f"{target} = XOR({target}_enc, trojan_sig)")

    return logic

def replace_target(gates, target):
    return [f"{target}_enc = {l.split('=')[1].strip()}" if l.startswith(f"{target} ") else l for l in gates]

def write_bench(path, key, ins, keys, outs, logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for i in ins: f.write(f"INPUT({i})\n")
        for k in keys: f.write(f"INPUT({k})\n")
        for o in outs: f.write(f"OUTPUT({o})\n")
        for l in logic: f.write(f"{l}\n")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bench_path", type=Path, required=True)
    p.add_argument("--keysize", type=int, required=True)
    p.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = p.parse_args()

    if args.keysize % 2 != 0:
        raise ValueError("Keysize must be even")

    ins, outs, gates = parse_bench(args.bench_path)
    tgt = outs[0]
    key, keys = generate_key(args.keysize)
    logic = replace_target(gates, tgt) + antisat_trojan_logic(ins, keys, tgt)

    args.output_path.mkdir(exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_TroLL_AntiSAT_k_{args.keysize}.bench"
    write_bench(out_file, key, ins, keys, outs, logic)
    print(f"TroLL-AntiSAT written: {out_file}")

if __name__ == "__main__":
    main()
