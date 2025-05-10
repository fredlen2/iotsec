#!/usr/bin/env python3

import argparse
from pathlib import Path
import random
import sys
import os

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

def parse_bench(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line.split("(")[1].split(")")[0])
        elif line.startswith("OUTPUT("):
            outputs.append(line.split("(")[1].split(")")[0])
        else:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    key_decls = [f"INPUT({k})" for k in key_inputs]
    return key, key_inputs, key_decls

def antisat_logic(inputs, keyinputs, key_bits, target_output):
    assert len(keyinputs) % 2 == 0
    n = len(keyinputs) // 2
    logic = []

    g_terms = []
    gbar_terms = []

    for i in range(n):
        pi = inputs[i % len(inputs)]
        k1 = keyinputs[i]
        k2 = keyinputs[i + n]

        xor1 = f"g_xor1_{i}"
        xor2 = f"g_xor2_{i}"

        logic.append(f"{xor1} = XOR({pi}, {k1})")
        logic.append(f"{xor2} = XOR({pi}, {k2})")

        g_terms.append(xor1)
        gbar_terms.append(xor2)

    def build_and_chain(terms, out_name, gate_type):
        if len(terms) == 1:
            return [f"{out_name} = {gate_type}({terms[0]})"]
        logic = []
        current = terms
        count = 0
        while len(current) > 1:
            next_stage = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    w = f"{out_name}_{count}"
                    logic.append(f"{w} = {gate_type}({current[i]}, {current[i+1]})")
                    next_stage.append(w)
                    count += 1
                else:
                    next_stage.append(current[i])
            current = next_stage
        logic.append(f"{out_name} = {current[0]}")
        return logic

    logic += build_and_chain(g_terms, "g_out", "AND")
    logic += build_and_chain(gbar_terms, "gbar_out", "NAND")

    logic.append("antisat_out = AND(g_out, gbar_out)")
    logic.append(f"{target_output} = XOR({target_output}_enc, antisat_out)")

    return logic

def replace_target(gates, target):
    new_gates = []
    for line in gates:
        if line.startswith(f"{target} "):
            parts = line.split("=", 1)
            new_gates.append(f"{target}_enc = {parts[1].strip()}")
        else:
            new_gates.append(line)
    return new_gates

def write_bench(out_path, key, inputs, key_inputs, outputs, logic):
    with open(out_path, 'w') as f:
        f.write(f"#key={key}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for k in key_inputs:
            f.write(f"INPUT({k})\n")
        for out in outputs:
            f.write(f"OUTPUT({out})\n")
        for line in logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    if args.keysize % 2 != 0:
        raise ValueError("Keysize must be even for Anti-SAT (2n keys)")

    inputs, outputs, gates = parse_bench(args.bench_path)
    target_output = outputs[0]
    key, key_wires, key_inputs = generate_key(args.keysize)

    logic_gates = replace_target(gates, target_output)
    antisat = antisat_logic(inputs, key_wires, key, target_output)

    logic = logic_gates + antisat
    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_AntiSAT_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, key_inputs, outputs, logic)

    print(f"Anti-SAT locked circuit with Key[🔐] = {key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
