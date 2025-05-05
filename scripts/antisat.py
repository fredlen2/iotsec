#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import os
import random

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

"""
Anti-SAT Logic Locking
- Ensures only 2-input gates
- No floating wires or duplicate assignments
- Conforms to output naming convention: *_AntiSATLock_k_*
"""

def parse_bench(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    inputs, outputs, logic = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
        else:
            logic.append(line)
    return inputs, outputs, logic

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"INPUT(KEYINPUT{i})" for i in range(keysize)]
    key_wires = [f"KEYINPUT{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def get_protected_output(outputs, logic):
    # Pick the first declared output that is assigned in logic
    output_names = [line[7:-1] for line in outputs]
    assigned = set(line.split('=')[0].strip() for line in logic)
    for name in output_names:
        if name in assigned:
            return name
    raise ValueError("[!] Could not find assignment for protected output")

def split_pairs(lst):
    assert len(lst) % 2 == 0
    return [(lst[i], lst[i+1]) for i in range(0, len(lst), 2)]

def inject_antisat_logic(inputs, outputs, logic, key_wires, keysize, protected_output):
    protected_output_enc = protected_output + "_enc"
    for i, line in enumerate(logic):
        if line.startswith(f"{protected_output} ="):
            logic[i] = line.replace(protected_output, protected_output_enc, 1)
            break

    xor_f = [f"XOR_F_{i} = XOR({inp}, {key})" for i, (inp, key) in enumerate(zip([line[6:-1] for line in inputs[:keysize]], key_wires))]
    xor_fbar = [f"KEYINPUT_NOT{i} = NOT({key_wires[i]})\nXOR_FBAR_{i} = XOR({[line[6:-1] for line in inputs[:keysize]][i]}, KEYINPUT_NOT{i})"
                for i in range(keysize)]

    def and_tree(nodes, prefix):
        stage = nodes
        level = 0
        all_gates = []
        while len(stage) > 1:
            next_stage = []
            for i, (a, b) in enumerate(split_pairs(stage)):
                new = f"{prefix}_AND_{level}_{i}"
                all_gates.append(f"{new} = AND({a}, {b})")
                next_stage.append(new)
            stage = next_stage
            level += 1
        return stage[0], all_gates

    f_root, f_tree = and_tree([f"XOR_F_{i}" for i in range(keysize)], "F")
    fbar_root, fbar_tree = and_tree([f"XOR_FBAR_{i}" for i in range(keysize)], "FBAR")
    antisat_and = "ANTISAT_AND = AND({}, {})".format(f_root, fbar_root)
    lock_enable = "LOCK_ENABLE = NOT(ANTISAT_AND)"
    locked_output = f"{protected_output} = AND(LOCK_ENABLE, {protected_output_enc})"

    # Add these logic parts at the end
    full_logic = logic + xor_f + xor_fbar + f_tree + fbar_tree + [antisat_and, lock_enable, locked_output]
    final_outputs = outputs + [f"OUTPUT(KEYINPUT_NOT{i})" for i in range(keysize)]  # prevent floating nets
    return final_outputs, full_logic

def write_bench(path, key, inputs, outputs, key_inputs, logic):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="Anti-SAT Locking")
    parser.add_argument("--bench_path", required=True, type=Path)
    parser.add_argument("--keysize", required=True, type=int)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    args.output_path.mkdir(exist_ok=True)
    bench_name = args.bench_path.stem
    output_file = args.output_path / f"{bench_name}_AntiSATLock_k_{args.keysize}.bench"

    inputs, outputs, logic = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)
    target_output = get_protected_output(outputs, logic)
    final_outputs, locked_logic = inject_antisat_logic(inputs, outputs, logic, key_wires, args.keysize, target_output)
    write_bench(output_file, key, inputs, final_outputs, key_inputs, locked_logic)

    print(f"Anti-SAT locked circuit with key= {key} is saved to: {output_file}")

if __name__ == "__main__":
    main()
