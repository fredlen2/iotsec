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
"""
SARLock logic locking script (Atalanta-compatible)
- Detects the target output automatically
- Inserts SARLock logic using XNOR key comparisons
- Avoids floating nets by wiring and OUTPUT declarations
- Keeps original output after XOR with FLIP signal
"""

def parse_bench(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
        elif "=" in line:
            gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"INPUT(keyinput{i})" for i in range(keysize)]
    key_wires = [f"keyinput{i}" for i in range(keysize)]
    return key, key_inputs, key_wires

def extract_output_name(output_line):
    return output_line.split("(")[1].split(")")[0]

def build_sarlock_logic(target_output, key_wires, circuit_inputs):
    pattern_0 = f"XOR({target_output}, {target_output})"
    pattern_1 = f"XNOR({target_output}, {target_output})"
    sar_gates = []
    and_layer1 = []
    and_layer2 = []

    for i, (c_in, k_in) in enumerate(zip(circuit_inputs, key_wires)):
        x0 = f"in{i}_0 = XNOR({c_in}, {k_in})"
        p_sel = pattern_0 if i % 2 == 0 else pattern_1
        x1 = f"in{i}_1 = XNOR({k_in}, {p_sel})"
        sar_gates.extend([x0, x1])
        and_layer1.append((f"in{i}_0", f"in{i}_1"))

    # Layered AND tree for DTL_0 and DTL_2
    def build_and_tree(inputs, prefix):
        level = 0
        curr = inputs
        gates = []
        while len(curr) > 1:
            next_level = []
            for i in range(0, len(curr), 2):
                if i+1 < len(curr):
                    a, b = curr[i], curr[i+1]
                else:
                    a, b = curr[i], curr[i]
                name = f"{prefix}_{level}_{i//2}"
                gates.append(f"{name} = AND({a}, {b})")
                next_level.append(name)
            curr = next_level
            level += 1
        return curr[0], gates

    in0_list = [x[0] for x in and_layer1]
    in1_list = [x[1] for x in and_layer1]

    DTL_0, d0_gates = build_and_tree(in0_list, "d0")
    DTL_2_tmp, d1_gates = build_and_tree(in1_list, "d1")
    sar_gates.extend(d0_gates + d1_gates)
    sar_gates.append(f"DTL_0 = {DTL_0}")
    sar_gates.append(f"DTL_2 = NAND({DTL_2_tmp}, {DTL_2_tmp})")
    sar_gates.append("FLIP = AND(DTL_0, DTL_2)")
    sar_gates.append(f"{target_output}_enc = XOR(FLIP, {target_output})")
    sar_gates.append(f"{target_output} = {target_output}_enc")
    return sar_gates

def write_bench(path, key, inputs, outputs, logic, sarlock_logic, key_decls):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_decls + outputs + logic + sarlock_logic:
            f.write(line + "\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock - Atalanta Compatible")
    parser.add_argument("--bench_path", required=True, type=Path, help="Input .bench file")
    parser.add_argument("--keysize", required=True, type=int, help="Number of key inputs")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"), help="Output directory")

    args = parser.parse_args()
    args.output_path.mkdir(parents=True, exist_ok=True)
    bench_name = args.bench_path.stem

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_decls, key_wires = generate_key(args.keysize)
    circuit_inputs = [line.split("(")[1].split(")")[0] for line in inputs if not line.lower().startswith("input(keyinput")]

    target_output = extract_output_name(outputs[-1])  # last declared output
    sarlock_logic = build_sarlock_logic(target_output, key_wires, circuit_inputs)

    output_file = args.output_path / f"{bench_name}_SARLock_k_{args.keysize}.bench"
    write_bench(output_file, key, inputs, outputs, gates, sarlock_logic, key_decls)

    print(f"SARLock injected into '{target_output}'")
    print(f"Output written to {output_file}")
    print(f"Key: {key}")

if __name__ == "__main__":
    main()
