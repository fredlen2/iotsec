#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import os
import random

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

def parse_args():
    parser = argparse.ArgumentParser(description="Insert Anti-SAT locking.")
    parser.add_argument("--bench_path", type=Path, required=True, help="Input .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Key size")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Output directory")
    return parser.parse_args()

def generate_key(keysize):
    return ''.join(random.choice("01") for _ in range(keysize))

def parse_bench(path):
    with open(path) as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, logic = [], [], []
    for line in lines:
        if line.startswith("INPUT("): inputs.append(line)
        elif line.startswith("OUTPUT("): outputs.append(line)
        elif "=" in line: logic.append(line)
    return inputs, outputs, logic

def extract_protected_output(outputs):
    return outputs[0][7:-1]

def extract_fanin(logic, count):
    fanin = []
    for line in logic:
        if "=" in line:
            rhs = line.split("=")[1]
            if "(" in rhs and ")" in rhs:
                args = [x.strip() for x in rhs[rhs.find("(")+1:rhs.find(")")].split(",")]
                for a in args:
                    if a not in fanin:
                        fanin.append(a)
                    if len(fanin) == count:
                        return fanin
    return fanin[:count]

def build_and_tree(nodes, prefix, lines, used_names):
    level = 0
    while len(nodes) > 1:
        next_level = []
        for i in range(0, len(nodes), 2):
            if i + 1 < len(nodes):
                out = f"{prefix}_{level}_{i//2}"
                lines.append(f"{out}=AND({nodes[i]},{nodes[i+1]})")
                used_names.add(out)
                next_level.append(out)
            else:
                next_level.append(nodes[i])
        nodes = next_level
        level += 1
    return nodes[0]

def write_bench(path, key, inputs, outputs, logic, antisat_logic, used_names):
    all_lines = [f"#key={key}"] + inputs
    for i in range(len(key)):
        all_lines.append(f"INPUT(KEYINPUT{i})")
    all_lines += outputs
    all_lines += logic + antisat_logic

    # Add OUTPUTs for unused signals to avoid floating nets
    logic_signals = set()
    for line in logic + antisat_logic:
        lhs = line.split("=")[0]
        logic_signals.add(lhs)

    outputs_signals = {o[7:-1] for o in outputs}
    for signal in logic_signals:
        if signal not in outputs_signals and not any(f"{signal}=" in l for l in all_lines if l.startswith("OUTPUT(")):
            all_lines.append(f"OUTPUT({signal})")

    with open(path, "w") as f:
        f.write('\n'.join(all_lines) + '\n')

def build_antisat_logic(fanin_nodes, keysize, protected_output):
    logic = []
    used = set()
    xor_f, xor_fbar = [], []

    for i in range(keysize):
        ki = f"KEYINPUT{i}"
        ni = f"KEYINPUT_NOT{i}"
        xi = fanin_nodes[i]
        f = f"XOR_F_{i}"
        fb = f"XOR_FBAR_{i}"

        logic.append(f"{ni}=NOT({ki})")
        logic.append(f"{f}=XOR({xi},{ki})")
        logic.append(f"{fb}=XOR({xi},{ni})")
        xor_f.append(f)
        xor_fbar.append(fb)

        used.update([ni, f, fb])

    f_root = build_and_tree(xor_f, "F_AND", logic, used)
    fbar_root = build_and_tree(xor_fbar, "FBAR_AND", logic, used)

    logic.append(f"ANTISAT_AND=AND({f_root},{fbar_root})")
    logic.append("LOCK_ENABLE=NOT(ANTISAT_AND)")
    enc_output = f"{protected_output}_enc"
    logic.append(f"CORRUPTED_VAL=NOT({enc_output})")
    logic.append(f"{protected_output}=AND(LOCK_ENABLE,{enc_output})")

    used.update(["ANTISAT_AND", "LOCK_ENABLE", "CORRUPTED_VAL", protected_output])
    return logic, used

def main():
    args = parse_args()
    args.output_path.mkdir(parents=True, exist_ok=True)
    out_path = args.output_path / f"{args.bench_path.stem}_AntiSatLock_k_{args.keysize}.bench"

    inputs, outputs, logic = parse_bench(args.bench_path)
    key = generate_key(args.keysize)
    key_bits = list(key)

    protected_output = extract_protected_output(outputs)
    fanin_nodes = extract_fanin(logic, args.keysize)

    # Replace protected_output assignment with _enc
    new_logic = []
    enc_output = f"{protected_output}_enc"
    found = False
    for line in logic:
        if line.startswith(f"{protected_output}="):
            rhs = line.split("=")[1]
            new_logic.append(f"{enc_output}={rhs}")
            found = True
        else:
            new_logic.append(line)
    if not found:
        new_logic.append(f"{enc_output}={protected_output}")

    antisat_logic, used = build_antisat_logic(fanin_nodes, args.keysize, protected_output)

    write_bench(out_path, key, inputs, outputs, new_logic, antisat_logic, used)
    print(f"Anti-SAT locked file with key={key} saved to: {out_path}")

if __name__ == "__main__":
    main()
