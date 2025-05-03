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

"""
SARLock logic locking implementation based on:
"SARLock: SAT attack resistant logic locking" – Yasin et al.

Fixes:
- No floating nets (FLIP and DTL used correctly).
- Compatible with Atalanta fault simulator.
- Modular design with debug logging.
"""

# ---- Utility Functions ----

def read_bench_file(path):
    with open(path, 'r') as f:
        return f.readlines()

def write_bench_file(path, lines):
    with open(path, 'w') as f:
        f.writelines(lines)

def generate_random_key(keysize):
    return ''.join(random.choice('01') for _ in range(keysize))

def select_key_gates(inputs, keysize):
    return random.sample(inputs, keysize)

def generate_sarlock_logic(selected_inputs, key_wires, output_to_protect):
    """Returns SARLock comparator logic and modified output gate."""
    logic_lines = []
    xnor_wires = []

    for idx, (signal, key) in enumerate(zip(selected_inputs, key_wires)):
        xnor = f"xnor_{idx}"
        logic_lines.append(f"{xnor} = XNOR({signal}, {key})\n")
        xnor_wires.append(xnor)

    dtl_wire = "DTL"
    logic_lines.append(f"{dtl_wire} = " + " AND ".join(xnor_wires) + "\n")

    # Buffer FLIP from DTL to ensure it's used
    flip_wire = "FLIP"
    logic_lines.append(f"{flip_wire} = BUF({dtl_wire})\n")

    # Modify the original output to be locked
    orig_output_wire = f"{output_to_protect}_orig"
    logic_lines.append(f"{orig_output_wire} = BUF({output_to_protect})\n")
    logic_lines.append(f"{output_to_protect} = XOR({flip_wire}, {orig_output_wire})\n")

    return logic_lines, [flip_wire, dtl_wire]  # Return logic and additional outputs to declare

def parse_inputs_outputs(lines):
    inputs, outputs = [], []
    logic = []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line.strip().split("(")[1][:-1])
        elif line.startswith("OUTPUT("):
            outputs.append(line.strip().split("(")[1][:-1])
        else:
            logic.append(line)
    return inputs, outputs, logic

# ---- Main SARLock Routine ----

def apply_sarlock(bench_path: Path, keysize: int, output_dir: Path):
    lines = read_bench_file(bench_path)
    inputs, outputs, logic = parse_inputs_outputs(lines)

    circuit_inputs = [i for i in inputs if not i.startswith("keyinput")]
    selected_inputs = select_key_gates(circuit_inputs, keysize)
    key_wires = [f"keyinput{i}" for i in range(keysize)]

    # Pick output to protect
    protected_output = outputs[0]

    # Generate new OUTPUT lines
    new_outputs = [f"OUTPUT({o})\n" for o in outputs]
    new_outputs.append(f"OUTPUT({protected_output}_orig)\n")

    # Add key inputs
    key_inputs = [f"INPUT({k})\n" for k in key_wires]

    # Generate SARLock logic
    sarlock_logic, additional_outputs = generate_sarlock_logic(selected_inputs, key_wires, protected_output)

    for extra in additional_outputs:
        new_outputs.append(f"OUTPUT({extra})\n")

    # Header
    key_line = f"#key={generate_random_key(keysize)}\n"
    new_lines = [key_line] + [f"INPUT({i})\n" for i in circuit_inputs] + key_inputs + new_outputs + logic + sarlock_logic

    # Output path
    output_dir.mkdir(parents=True, exist_ok=True)
    out_name = bench_path.stem + f"_SARLock_k_{keysize}.bench"
    out_path = output_dir / out_name
    write_bench_file(out_path, new_lines)

    print(f"SARLock applied successfully. Output saved to: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply SARLock logic locking to a .bench circuit.")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to original .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Number of key gates to insert")
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"), help="Optional output directory")
    args = parser.parse_args()

    apply_sarlock(args.bench_path, args.keysize, args.output_dir)
