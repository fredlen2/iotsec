#!/usr/bin/env python3

import os
import argparse
from pathlib import Path

from tools.utils.utils import parse_bench_file, write_list_to_file


def sarlock_lock(inputs, outputs, gates, keysize):
    """
    Implements SARLock: generates a comparator circuit that flips one selected output
    if the input key mismatches, producing only one wrong output per wrong key.
    """
    # Define and register key inputs
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend(f"INPUT({k})" for k in key_inputs)

    # Step 1: XOR each input with its corresponding key bit
    xor_wires = [f"cmp_{i}" for i in range(keysize)]
    for wire, inp, key in zip(xor_wires, inputs, key_inputs):
        gates.append(f"{wire} = XOR({inp}, {key})")

    # Step 2: OR all xor_wires to generate a single flip signal
    or_output = xor_wires[0]
    for i, wire in enumerate(xor_wires[1:], start=1):
        new_or = f"cmp_or_{i}"
        gates.append(f"{new_or} = OR({or_output}, {wire})")
        or_output = new_or

    flip_signal = "flip"
    gates.append(f"{flip_signal} = BUF({or_output})")

    # Step 3: Protect the first output by XOR with the flip signal
    protected = outputs[0]
    # Rename existing assignment for the protected output
    for idx, gate in enumerate(gates):
        if gate.startswith(f"{protected} ="):
            expr = gate.split('=', 1)[1].strip()
            gates[idx] = f"{protected}_orig = {expr}"
            break

    gates.append(f"{protected} = XOR({protected}_orig, {flip_signal})")

    return key_inputs, gates


def main():
    parser = argparse.ArgumentParser(
        description="Apply SARLock logic locking to a bench file."
    )
    parser.add_argument(
        "--bench_path", type=Path, required=True,
        help="Path to the input .bench file."
    )
    parser.add_argument(
        "--keysize", type=int, required=True,
        help="Number of key bits."
    )
    parser.add_argument(
        "--output_dir", type=Path, default=Path("locked_circuits"),
        help="Directory where locked circuits will be saved."
    )
    args = parser.parse_args()

    # Parse the original bench file
    inputs, outputs, gates, _ = parse_bench_file(str(args.bench_path))

    # Generate locked gates
    key_inputs, locked_gates = sarlock_lock(inputs, outputs, gates, args.keysize)

    # Assemble full circuit description
    all_gates = [f"INPUT({inp})" for inp in inputs] + \
                [f"INPUT({k})" for k in key_inputs] + \
                [f"OUTPUT({o})" for o in outputs] + \
                locked_gates

    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = args.bench_path.stem + f"_SARLock_k_{args.keysize}.bench"
    output_path = args.output_dir / output_file

    # Write to file with key annotations
    write_list_to_file(all_gates, str(output_path), [1] * args.keysize)


if __name__ == "__main__":
    main()
