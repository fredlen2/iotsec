#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.utils.utils import parse_bench_file, write_list_to_file


def generate_random_key(keysize):
    """Generate a list of random 0/1 values."""
    return [random.randint(0, 1) for _ in range(keysize)]


def sarlock_lock(inputs, outputs, gates, keysize, key_bits):
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend([f"INPUT({k})" for k in key_inputs])

    protected_output = outputs[2] if len(outputs) > 2 else outputs[0]  # usually G370GAT
    orig_signal = f"{protected_output}_orig"

    # Rename the original protected output gate
    updated_gates = []
    for g in gates:
        if g.startswith(f"{protected_output} ="):
            expr = g.split("=", 1)[1].strip()
            updated_gates.append(f"{orig_signal} = {expr}")
        else:
            updated_gates.append(g)
    gates = updated_gates

    # Generate pattern constants (to prevent SAT solvers from easily finding valid key)
    gates.append("pattern_1 = XNOR(G76GAT, G76GAT)")  # always 1
    gates.append("pattern_0 = XOR(G76GAT, G76GAT)")   # always 0

    # Primary comparator between input and key
    inter_ands = []
    for i in range(keysize):
        wire = f"in{i}xor_0"
        gates.append(f"{wire} = XNOR({inputs[i]}, keyinput{i})")
        inter_ands.append(wire)

    # Hardcoded one incorrect pattern (pattern_1/0)
    wrong_ands = []
    for i, bit in enumerate(key_bits):
        pattern_val = "pattern_1" if bit == 1 else "pattern_0"
        wire = f"in{i}xor_2"
        gates.append(f"{wire} = XNOR(keyinput{i}, {pattern_val})")
        wrong_ands.append(wire)

    # AND trees to collapse comparators
    def generate_and_tree(wires, prefix):
        level = 0
        while len(wires) > 1:
            next_level = []
            for i in range(0, len(wires), 2):
                if i + 1 < len(wires):
                    out = f"inter{level}_{prefix}"
                    gates.append(f"{out} = AND({wires[i]}, {wires[i + 1]})")
                    next_level.append(out)
                    level += 1
                else:
                    next_level.append(wires[i])
            wires = next_level
        return wires[0]

    DTL_0 = generate_and_tree(inter_ands, "0")
    DTL_2 = generate_and_tree(wrong_ands, "2")

    gates.append(f"DTL_0 = {DTL_0}")
    gates.append(f"DTL_2 = {DTL_2}")
    gates.append("FLIP = AND(DTL_0, DTL_2)")
    gates.append(f"{protected_output} = XOR(FLIP, {orig_signal})")

    return key_inputs, gates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", required=True)
    parser.add_argument("--keysize", type=int, required=True)
    args = parser.parse_args()

    inputs, outputs, gates, _ = parse_bench_file(args.bench_path)
    key_bits = generate_random_key(args.keysize)
    key_inputs, locked_gates = sarlock_lock(inputs, outputs, gates, args.keysize, key_bits)

    all_gates = [f"INPUT({i})" for i in inputs] + \
                [f"INPUT({k})" for k in key_inputs] + \
                [f"OUTPUT({o})" for o in outputs] + \
                locked_gates

    os.makedirs("locked_circuits", exist_ok=True)
    base_name = os.path.basename(args.bench_path).replace(".bench", f"_SARLock_k_{args.keysize}.bench")
    out_path = os.path.join("locked_circuits", base_name)
    write_list_to_file(all_gates, out_path, key_bits)


if __name__ == "__main__":
    main()
