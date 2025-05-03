#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.utils.utils import (
    parse_bench_file,
    defining_keyinputs,
    insert_key_gates,
    write_list_to_file,
)


def main():
    parser = argparse.ArgumentParser(description="Apply SARLock Trojan logic locking")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to input .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Size of the key to embed")
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"), help="Directory to save locked circuit")

    args = parser.parse_args()
    bench_path = args.bench_path
    keysize = args.keysize
    output_dir = args.output_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Parse the original bench file
    inputs, outputs, gates, existing_keys = parse_bench_file(bench_path)

    # Step 2: Generate a random key
    key = [random.choice([0, 1]) for _ in range(keysize)]

    # Step 3: Define new keyinputs
    keyinput_lines = defining_keyinputs(key, inputs)

    # Step 4: Prepare SARLock logic
    original_output = "G370GAT"
    locked_output = f"{original_output}_orig"

    if original_output in outputs:
        outputs[outputs.index(original_output)] = locked_output
    else:
        raise ValueError(f"{original_output} not found in OUTPUT declarations")

    outputs.append(original_output)

    # Select only real circuit inputs (not keyinputs)
    real_inputs = [i for i in inputs if not i.startswith("keyinput")]
    if len(real_inputs) < keysize:
        raise ValueError("Not enough real inputs to match keysize for SARLock")

    selected_inputs = random.sample(real_inputs, keysize)

    # Build SARLock logic using only selected inputs
    sarlock_logic = [f"{locked_output} = BUF({original_output})"]

    sarlock_logic += [
        "pattern_1    = XNOR(G76GAT, G76GAT)",  # always 1
        "pattern_0    = XOR(G76GAT, G76GAT)"    # always 0
    ]

    for i in range(keysize):
        pattern = f"pattern_{i % 2}"
        sarlock_logic += [
            f"in{i}xor_0     = XNOR({selected_inputs[i]}, keyinput{i})",
            f"in{i}xor_2     = XNOR(keyinput{i}, {pattern})"
        ]

    for j in range(0, keysize, 2):
        sarlock_logic.append(f"inter{j//2}_0     = AND(in{j}xor_0, in{j+1}xor_0)")
        sarlock_logic.append(f"inter{j//2}_2     = AND(in{j}xor_2, in{j+1}xor_2)")

    half = keysize // 2
    for k in range(0, half, 2):
        sarlock_logic.append(f"inter{k//2+half}_0     = AND(inter{k}_0, inter{k+1}_0)")
        sarlock_logic.append(f"inter{k//2+half}_2     = AND(inter{k}_2, inter{k+1}_2)")

    # Final DTL and FLIP logic
    sarlock_logic += [
        "DTL_0        = inter1_0",
        "DTL_2        = inter1_2",
        "FLIP         = AND(DTL_0, DTL_2)",
        f"{original_output} = XOR(FLIP, {locked_output})"
    ]

    # Step 5: Merge all and write to file
    new_circuit = inputs + keyinput_lines + [f"OUTPUT({o})" for o in outputs] + gates + sarlock_logic
    output_file = output_dir / f"{bench_path.stem}_SARLock_k_{keysize}.bench"
    write_list_to_file(new_circuit, output_file, key)


if __name__ == "__main__":
    main()
