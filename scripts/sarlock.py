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

def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT("):
                inputs.append(line.split("(")[1].split(")")[0])
            elif line.startswith("OUTPUT("):
                outputs.append(line.split("(")[1].split(")")[0])
            elif "=" in line:
                gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    keyinputs = [f"keyinput{i}" for i in range(keysize)]
    return key, keyinputs

def sarlock_insert(bench_path, output_path, keysize):
    inputs, outputs, gates = parse_bench(bench_path)
    key, keyinputs = generate_key(keysize)
    target = outputs[0]

    logic = [f"#key={key}"]
    
    # Declare all INPUTs
    logic += [f"INPUT({inp})" for inp in inputs + keyinputs]
    # Declare OUTPUTs
    logic += [f"OUTPUT({out})" for out in outputs]

    and_inputs_0, and_inputs_2 = [], []
    for i in range(keysize):
        pi = inputs[i % len(inputs)]
        ki = keyinputs[i]
        x0 = f"in{i}_xor0"
        x2 = f"in{i}_xor2"
        gates.append(f"{x0} = XNOR({pi}, {ki})")
        gates.append(f"{x2} = XNOR({ki}, {'logic0' if key[i] == '0' else 'logic1'})")
        and_inputs_0.append(x0)
        and_inputs_2.append(x2)

    gates.append(f"logic0 = XNOR({inputs[0]}, {inputs[0]})")
    gates.append(f"logic1 = XOR({inputs[0]}, {inputs[0]})")

    def build_and_tree(signals, label):
        level = 0
        nodes = signals[:]
        while len(nodes) > 1:
            next_nodes = []
            for i in range(0, len(nodes), 2):
                if i + 1 < len(nodes):
                    node = f"{label}_L{level}_{i//2}"
                    gates.append(f"{node} = AND({nodes[i]}, {nodes[i+1]})")
                    next_nodes.append(node)
                else:
                    next_nodes.append(nodes[i])
            nodes = next_nodes
            level += 1
        return nodes[0]

    dtl0 = build_and_tree(and_inputs_0, "match_and")
    dtl2 = build_and_tree(and_inputs_2, "mismatch_and")

    gates.append(f"DTL_0 = {dtl0}")
    gates.append(f"DTL_2 = {dtl2}")
    gates.append(f"FLIP = AND(DTL_0, DTL_2)")

    # Replace target assignment
    modified_gates = []
    for gate in gates:
        if gate.startswith(f"{target} ="):
            modified_gates.append(gate.replace(target, f"{target}_enc"))
        else:
            modified_gates.append(gate)
    modified_gates.append(f"{target} = XOR(FLIP, {target}_enc)")

    out_file = output_path / f"{Path(bench_path).stem}_SARLock_k_{keysize}.bench"
    output_path.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'w') as f:
        for line in logic + modified_gates:
            f.write(f"{line}\n")

    print(f"SARLock locked circuit with Key[\U0001f510] = {key} is saved to: {out_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()
    sarlock_insert(args.bench_path, args.output_path, args.keysize)

if __name__ == "__main__":
    main()
