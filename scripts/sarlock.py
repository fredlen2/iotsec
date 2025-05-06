#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import (
#     parse_bench_file,
#     defining_keyinputs,
#     insert_key_gates,
#     write_list_to_file,
# )

#!/usr/bin/env python3

import argparse
import random
import os

def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT("):
                inputs.append(line.split("(")[1].split(")")[0])
            elif line.startswith("OUTPUT("):
                outputs.append(line.split("(")[1].split(")")[0])
            elif "=" in line:
                gates.append(line)
    return inputs, outputs, gates

def generate_key(k):
    bits = [random.choice("01") for _ in range(k)]
    return "".join(bits)

def build_sarlock_logic(inputs, keyinputs, target, key_bits):
    gates = []

    # Generate XNOR comparator trees
    compare_xnor = []
    pattern_xnor = []
    logic_zero = f"ZERO_X = XOR({target}, {target})"
    logic_one = f"ONE_X = XNOR({target}, {target})"
    gates += [logic_zero, logic_one]

    for i, key in enumerate(keyinputs):
        x0 = f"match_{i}"
        x1 = f"pattern_{i}"
        gates.append(f"{x0} = XNOR({inputs[i]}, {key})")
        pat = "ONE_X" if key_bits[i] == "1" else "ZERO_X"
        gates.append(f"{x1} = XNOR({key}, {pat})")
        compare_xnor.append(x0)
        pattern_xnor.append(x1)

    # AND trees
    def and_reduce(inputs, label):
        nodes = inputs
        level = 0
        count = 0
        results = []
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    name = f"{label}_{level}_{count}"
                    results.append(f"{name} = AND({nodes[i]}, {nodes[i+1]})")
                    next_level.append(name)
                    count += 1
                else:
                    next_level.append(nodes[i])
            nodes = next_level
            level += 1
        root = f"{label}_root"
        results.append(f"{root} = {nodes[0]}")
        return root, results

    dtl0_root, dtl0_gates = and_reduce(compare_xnor, "cmp0")
    dtl1_root, dtl1_gates = and_reduce(pattern_xnor, "cmp1")

    gates += dtl0_gates + dtl1_gates
    gates.append(f"DTL_0 = {dtl0_root}")
    gates.append(f"DTL_2 = {dtl1_root}")
    gates.append(f"FLIP = AND(DTL_0, DTL_2)")
    gates.append(f"{target} = XOR(FLIP, {target}_enc)")
    return gates

def write_bench(output_path, key, inputs, keyinputs, outputs, logic):
    with open(output_path, "w") as f:
        f.write(f"#key={key}\n")
        for i in inputs:
            f.write(f"INPUT({i})\n")
        for k in keyinputs:
            f.write(f"INPUT({k})\n")
        for o in outputs:
            f.write(f"OUTPUT({o})\n")
        for line in logic:
            f.write(f"{line}\n")

def apply_sarlock(bench_path, keysize):
    inputs, outputs, logic = parse_bench(bench_path)
    key = generate_key(keysize)
    keyinputs = [f"keyinput{i}" for i in range(keysize)]
    target_output = outputs[0]

    updated_logic = []
    for gate in logic:
        if gate.startswith(f"{target_output} "):
            rhs = gate.split("=")[1].strip()
            updated_logic.append(f"{target_output}_enc = {rhs}")
        else:
            updated_logic.append(gate)

    sarlock_logic = build_sarlock_logic(inputs, keyinputs, target_output, key)
    all_logic = updated_logic + sarlock_logic

    out_path = bench_path.replace(".bench", f"_SARLock_k_{keysize}.bench")
    write_bench(out_path, key, inputs, keyinputs, outputs, all_logic)
    print(f"SARLock locked file with key {key} is saved to: {out_path}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", required=True)
    parser.add_argument("--keysize", type=int, required=True)
    args = parser.parse_args()
    apply_sarlock(args.bench_path, args.keysize)

if __name__ == "__main__":
    main()
