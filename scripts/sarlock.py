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


def generate_key(keysize: int) -> str:
    return "".join(random.choice("01") for _ in range(keysize))


def parse_bench_file(bench_path: Path):
    lines = bench_path.read_text().splitlines()
    inputs, outputs, others = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
        else:
            others.append(line)
    return inputs, outputs, others


def insert_sarlock_logic(inputs: list[str], keysize: int, key_bits: str):
    key_inputs = [f"INPUT(keyinput{i})" for i in range(keysize)]
    key_gates = []
    xnor_outputs = []

    # Select input signals for SARLock
    chosen_inputs = [line[line.find("(") + 1:line.find(")")] for line in random.sample(inputs, keysize)]

    for i in range(keysize):
        gate_name = f"xnor_{i}"
        key_gates.append(f"{gate_name} = XNOR({chosen_inputs[i]}, keyinput{i})")
        xnor_outputs.append(gate_name)

    # AND all xnor results to form DTL
    dtl_and = "DTL = " + " AND ".join(xnor_outputs)

    # Generate final FLIP logic
    flip_logic = "FLIP = BUF(DTL)"

    # Return lines to append and extra signals to declare as output
    return key_inputs, key_gates + [dtl_and, flip_logic], ["OUTPUT(FLIP)"]


def write_modified_bench(inputs, outputs, logic_lines, sarlock_inputs, sarlock_logic, sarlock_outputs, output_path: Path, key_bits: str):
    with output_path.open("w") as f:
        f.write(f"#key={key_bits}\n")
        for line in inputs + sarlock_inputs:
            f.write(line + "\n")
        for line in outputs + sarlock_outputs:
            f.write(line + "\n")
        for line in logic_lines + sarlock_logic:
            f.write(line + "\n")
    print(f"SARLock-locked circuit written to: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    key = generate_key(args.keysize)
    inputs, outputs, logic_lines = parse_bench_file(args.bench_path)

    sarlock_inputs, sarlock_logic, sarlock_outputs = insert_sarlock_logic(inputs, args.keysize, key)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"

    write_modified_bench(inputs, outputs, logic_lines, sarlock_inputs, sarlock_logic, sarlock_outputs, out_path, key)


if __name__ == "__main__":
    main()
