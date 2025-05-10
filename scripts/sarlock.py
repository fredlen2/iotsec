#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import os

"""
Provably Secure SARLock Implementation
- Applies SARLock to a .bench circuit file
- Follows best practices (academic + industry)
- Compatible with SLD/SAT tools
"""

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

def build_and_tree(wires, prefix):
    count = 0
    layers = []
    while len(wires) > 1:
        new_wires = []
        for i in range(0, len(wires), 2):
            if i + 1 < len(wires):
                a, b = wires[i], wires[i + 1]
                w = f"{prefix}_L{count}_{i//2}"
                layers.append(f"{w} = AND({a}, {b})")
                new_wires.append(w)
            else:
                new_wires.append(wires[i])
        wires = new_wires
        count += 1
    return wires[0], layers

def sarlock_logic(inputs, keyinputs, key_bits, target_output):
    logic = []

    # SLD-safe constant logic
    logic.append("zero_not = NOT(G1GAT)")
    logic.append("zero     = AND(G1GAT, zero_not)")
    logic.append("one_not1 = NOT(G1GAT)")
    logic.append("one      = NAND(G1GAT, one_not1)")

    match_terms = []
    mismatch_terms = []

    for i, kbit in enumerate(key_bits):
        inp = inputs[i % len(inputs)]
        kinp = keyinputs[i]

        xor0 = f"in{i}_xor0"
        xor2 = f"in{i}_xor2"

        logic.append(f"{xor0} = XNOR({inp}, {kinp})")
        match_terms.append(xor0)

        const = "one" if kbit == '1' else "zero"
        logic.append(f"{xor2} = XNOR({kinp}, {const})")
        mismatch_terms.append(xor2)

    # Build AND trees
    match_root, match_gates = build_and_tree(match_terms, "match_and")
    mismatch_root, mismatch_gates = build_and_tree(mismatch_terms, "mismatch_and")
    logic.extend(match_gates + mismatch_gates)

    # SLD-safe signal passing
    logic.append(f"DTL_0 = BUF({match_root})")
    logic.append(f"DTL_2 = BUF({mismatch_root})")
    logic.append("FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{target_output} = XOR(FLIP, {target_output}_enc)")

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
            # f.write(f"INPUT({k})\n")
            f.write(f"{k}\n")
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

    # Load original .bench file
    inputs, outputs, gates = parse_bench(args.bench_path)
    target_output = outputs[0]  # Lock the first output
    key, key_wires, key_inputs = generate_key(args.keysize)

    # Modify circuit
    logic_gates = replace_target(gates, target_output)
    sarlock = sarlock_logic(inputs, key_wires, key, target_output)

    # Combine modified logic
    logic = logic_gates + sarlock

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    write_bench(out_file, key, inputs, key_inputs, outputs, logic)

    print(f"SARLock locked circuit with Key[🔐] = {key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
