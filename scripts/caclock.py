#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import os

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

def generate_key_and_fixed_pattern(n):
    key = ''.join(random.choice("01") for _ in range(n))
    fixed_pattern = ''.join(random.choice("01") for _ in range(n))
    key_inputs = [f"keyinput{i}" for i in range(n)]
    return key, fixed_pattern, key_inputs

def xor_layer(inputs, keys_or_bits, prefix):
    logic = []
    outputs = []
    for i, (inp, bit) in enumerate(zip(inputs, keys_or_bits)):
        wire = f"{prefix}_xor_{i}"
        if isinstance(bit, str) and bit.startswith("keyinput"):
            logic.append(f"{wire} = XOR({inp}, {bit})")
        else:
            const = "one" if bit == '1' else "zero"
            logic.append(f"{wire} = XNOR({inp}, {const})")  # XOR with constant bit
        outputs.append(wire)
    return outputs, logic

def build_dtl_tree(wires, prefix, or_indices=set()):
    logic = []
    layer = 0
    current = wires
    while len(current) > 1:
        next_stage = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                a, b = current[i], current[i+1]
                out = f"{prefix}_l{layer}_{i//2}"
                if layer == 0 and i//2 in or_indices:
                    gate = "OR"
                else:
                    gate = "AND"
                logic.append(f"{out} = {gate}({a}, {b})")
                next_stage.append(out)
            else:
                next_stage.append(current[i])
        current = next_stage
        layer += 1
    logic.append(f"{prefix}_out = BUF({current[0]})")
    return f"{prefix}_out", logic

def cac_logic(inputs, key_inputs, key_bits, fixed_bits, target_output):
    logic = []
    # secure constant definitions
    logic.append("zero_not = NOT(G1GAT)")
    logic.append("zero = AND(G1GAT, zero_not)")
    logic.append("one_not = NOT(G1GAT)")
    logic.append("one = NAND(G1GAT, one_not)")

    # XOR layer for key and fixed pattern
    dtl_key_xors, key_xor_logic = xor_layer(inputs, key_inputs, "dtl_key")
    dtl_fixed_xors, fixed_xor_logic = xor_layer(inputs, fixed_bits, "dtl_fixed")

    # Build trees (use OR gates for corruptibility at level-0 in key DTL)
    or_indices = set(random.sample(range(len(inputs)//2), min(2, len(inputs)//2)))
    dtl_key_out, dtl_key_tree = build_dtl_tree(dtl_key_xors, "dtl_key", or_indices)
    dtl_fixed_out, dtl_fixed_tree = build_dtl_tree(dtl_fixed_xors, "dtl_fixed")

    logic += key_xor_logic + fixed_xor_logic + dtl_key_tree + dtl_fixed_tree

    # Flip signal: OR of key-DTL and fixed-DTL
    logic.append(f"flip = OR({dtl_key_out}, {dtl_fixed_out})")

    # Corrupt: XOR(target_output_enc, fixed-DTL)
    logic.append(f"ccrpt = XOR({target_output}_enc, {dtl_fixed_out})")

    # Correct: XOR(ccrpt, flip)
    logic.append(f"{target_output} = XOR(ccrpt, flip)")

    return logic

def replace_target(gates, target):
    new_gates = []
    for line in gates:
        if line.startswith(f"{target} "):
            rhs = line.split("=", 1)[1].strip()
            new_gates.append(f"{target}_enc = {rhs}")
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
        raise ValueError("Keysize must be even for DTL (recommend: power of 2)")

    inputs, outputs, gates = parse_bench(args.bench_path)
    target_output = outputs[0]

    key, fixed_bits, key_inputs = generate_key_and_fixed_pattern(args.keysize)
    gates_mod = replace_target(gates, target_output)
    cac = cac_logic(inputs, key_inputs, key, fixed_bits, target_output)

    logic = gates_mod + cac
    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_CAC_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, key_inputs, outputs, logic)

    print(f"CAC locked circuit with Key[🔐] = {key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
