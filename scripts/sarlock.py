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


def sarlock_encrypt(bench_path: Path, keysize: int, output_dir: Path):
    # Parse original circuit
    inputs, outputs, gates, existing_key_inputs = parse_bench_file(bench_path)

    # Generate random key
    key = [random.randint(0, 1) for _ in range(keysize)]

    # Define new keyinputs and update input list
    keyinput_lines = defining_keyinputs(key, inputs)
    inputs.extend([line.split("(")[1].split(")")[0] for line in keyinput_lines])

    # Insert key gates
    gates = insert_key_gates(key, gates, start_num=len(existing_key_inputs))

    # Add SARLock logic
    sarlock_logic = [
        "G370GAT_orig = BUF(G370GAT)",
        "pattern_1    = XNOR(G76GAT, G76GAT)",
        "pattern_0    = XOR(G76GAT, G76GAT)",
    ]

    for i in range(keysize):
        sarlock_logic += [
            f"in{i}xor_0     = XNOR(G{i*3+1}GAT, keyinput{i})",
            f"in{i}xor_2     = XNOR(keyinput{i}, pattern_{i%2})"
        ]

    # Build reduction logic
    def reduce_and(prefix, terms):
        gates = []
        level = 0
        while len(terms) > 1:
            new_terms = []
            for i in range(0, len(terms), 2):
                if i + 1 < len(terms):
                    name = f"{prefix}_{level}_{i//2}"
                    gates.append(f"{name} = AND({terms[i]}, {terms[i+1]})")
                    new_terms.append(name)
                else:
                    new_terms.append(terms[i])
            terms = new_terms
            level += 1
        return gates, terms[0]

    dtl0_terms = [f"in{i}xor_0" for i in range(keysize)]
    dtl2_terms = [f"in{i}xor_2" for i in range(keysize)]
    dtl0_gates, dtl0_final = reduce_and("inter0", dtl0_terms)
    dtl2_gates, dtl2_final = reduce_and("inter2", dtl2_terms)

    sarlock_logic += dtl0_gates + dtl2_gates + [
        f"DTL_0 = {dtl0_final}",
        f"DTL_2 = {dtl2_final}",
        "FLIP = AND(DTL_0, DTL_2)",
        "G370GAT = XOR(FLIP, G370GAT_orig)"
    ]

    # Combine all lines
    all_lines = [f"INPUT({inp})" for inp in inputs] + \
                [f"OUTPUT({out})" for out in outputs + ["DTL_0", "DTL_2", "FLIP"]] + \
                gates + sarlock_logic

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Construct output file path
    output_path = output_dir / f"{bench_path.stem}_SARLock_k_{keysize}.bench"

    # Write output
    write_list_to_file(all_lines, output_path, key)

    print(f"SARLock-encrypted circuit saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Apply SARLock Trojan Insertion")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to input .bench file")
    parser.add_argument("--keysize", type=int, required=True, help="Number of key bits")
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"), help="Directory to save the output file")

    args = parser.parse_args()

    sarlock_encrypt(args.bench_path, args.keysize, args.output_dir)
