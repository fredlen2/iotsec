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

def generate_sarlock_circuit(inputs, outputs, gates, key_bits):
    """Generate the SARLock logic and attach to original circuit."""
    # Step 1: Select inputs for locking
    selected_inputs = random.sample([i for i in inputs if "keyinput" not in i], len(key_bits))

    pattern_1 = "pattern_1 = XNOR(G76GAT, G76GAT)"
    pattern_0 = "pattern_0 = XOR(G76GAT, G76GAT)"
    gates.extend([pattern_1, pattern_0])

    # Step 2: Create XNOR pairs and patterns
    xor_lines = []
    for i, (signal, key_bit) in enumerate(zip(selected_inputs, key_bits)):
        xor_op = "XNOR"
        pattern_val = "pattern_1" if (i + int(key_bit)) % 2 == 0 else "pattern_0"
        xor_lines.append(f"in{i}xor_0 = {xor_op}({signal}, keyinput{i})")
        xor_lines.append(f"in{i}xor_2 = {xor_op}(keyinput{i}, {pattern_val})")

    gates.extend(xor_lines)

    # Step 3: Build up AND tree logic
    for p in [0, 2]:
        and_level_1 = [f"inter{i}_{p} = AND(in{i*2}xor_{p}, in{i*2+1}xor_{p})" for i in range(4)]
        and_level_2 = [f"inter4_{p} = AND(inter0_{p}, inter1_{p})", f"inter5_{p} = AND(inter2_{p}, inter3_{p})"]
        and_level_3 = f"inter6_{p} = AND(inter4_{p}, inter5_{p})"
        gates.extend(and_level_1 + and_level_2 + [and_level_3])

    # Final FLIP logic and G370GAT interception
    gates.extend([
        "DTL_0 = inter6_0",
        "DTL_2 = inter6_2",
        "FLIP = AND(DTL_0, DTL_2)",
        "G370GAT_orig = BUF(G370GAT)",
        "G370GAT = XOR(FLIP, G370GAT_orig)"
    ])

    # Fix floating outputs
    outputs.extend(["G370GAT_orig", "FLIP"])

    return inputs, outputs, gates


def fix_input_syntax(lines):
    """Ensure that all non-assignment and non-declared lines are properly wrapped in INPUT()."""
    fixed = []
    for line in lines:
        stripped = line.strip()
        if (
            stripped and
            not stripped.startswith("#") and
            "=" not in stripped and
            not stripped.startswith("INPUT(") and
            not stripped.startswith("OUTPUT(")
        ):
            fixed.append(f"INPUT({stripped})\n")
        else:
            fixed.append(line if line.endswith("\n") else line + "\n")
    return fixed


def write_sarlock_bench_file(output_path, inputs, outputs, gates, key_bits):
    with open(output_path, "w") as f:
        f.write(f"#key={''.join(map(str, key_bits))}\n")
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for outp in outputs:
            f.write(f"OUTPUT({outp})\n")
        content = [*gates]
        corrected = fix_input_syntax(content)
        f.writelines(corrected)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--keysize", type=int, required=True)
    parser.add_argument("--output_dir", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    key = [random.randint(0, 1) for _ in range(args.keysize)]
    inputs, outputs, gates, _ = parse_bench_file(args.bench_path)
    inputs, outputs, gates = generate_sarlock_circuit(inputs, outputs, gates, key)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    write_sarlock_bench_file(out_path, inputs, outputs, gates, key)

    print(f"[SARLock] Locked circuit written to: {out_path}")


if __name__ == "__main__":
    main()
