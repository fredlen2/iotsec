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


def generate_random_key(keysize: int) -> list[int]:
    return [random.choice([0, 1]) for _ in range(keysize)]


def create_sarlock_logic(inputs: list[str], keysize: int, keyinput_start: int, key: list[int], outputs: list[str]) -> list[str]:
    selected_inputs = random.sample([inp for inp in inputs if "keyinput" not in inp], keysize)

    # Create the original output signal
    original_output = "G370GAT_orig = BUF(G370GAT)"

    pattern_1 = "pattern_1 = XNOR(G76GAT, G76GAT)"
    pattern_0 = "pattern_0 = XOR(G76GAT, G76GAT)"

    xor_gates = []
    inter_gates = []

    for i, input_signal in enumerate(selected_inputs):
        keyinput = f"keyinput{keyinput_start + i}"
        pattern = "pattern_1" if key[i] else "pattern_0"
        xor_gates.append(f"in{i}xor_0 = XNOR({input_signal}, {keyinput})")
        xor_gates.append(f"in{i}xor_2 = XNOR({keyinput}, {pattern})")

    for i in range(0, keysize, 2):
        inter_gates.append(f"inter{i//2}_0 = AND(in{i}xor_0, in{i+1}xor_0)")
        inter_gates.append(f"inter{i//2}_2 = AND(in{i}xor_2, in{i+1}xor_2)")

    for i in range(0, len(inter_gates) // 2, 2):
        inter_gates.append(f"inter{i//2+4}_0 = AND(inter{i}_0, inter{i+1}_0)")
        inter_gates.append(f"inter{i//2+4}_2 = AND(inter{i}_2, inter{i+1}_2)")

    dtl_lines = [
        "DTL_0 = inter6_0",
        "DTL_2 = inter6_2",
        "FLIP = AND(DTL_0, DTL_2)",
        "G370GAT = XOR(FLIP, G370GAT_orig)"
    ]

    # Ensure OUTPUT(DTL_2) is added to prevent floating net error
    if "DTL_2" not in outputs:
        outputs.append("DTL_2")

    return [original_output, pattern_1, pattern_0] + xor_gates + inter_gates + dtl_lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    bench_path: Path = args.bench_path
    keysize: int = args.keysize
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    inputs, outputs, gates, existing_keyinputs = parse_bench_file(bench_path)

    key = generate_random_key(keysize)
    start_index = (
        max([int(k.replace("keyinput", "")) for k in existing_keyinputs]) + 1
        if existing_keyinputs
        else 0
    )

    keyinput_declarations = defining_keyinputs(key, existing_keyinputs)
    sarlock_logic = create_sarlock_logic(inputs, keysize, start_index, key, outputs)

    all_lines = (
        keyinput_declarations +
        [f"INPUT({inp})" for inp in inputs if not inp.startswith("keyinput")] +
        [f"OUTPUT({out})" for out in outputs] +
        gates +
        sarlock_logic
    )

    save_path = output_dir / f"{bench_path.stem}_SARLock_k_{keysize}.bench"
    write_list_to_file(all_lines, save_path, key)

    print(f"SARLock circuit written to: {save_path}")


if __name__ == "__main__":
    main()
