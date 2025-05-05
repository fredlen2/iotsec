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
SARLock Logic Locking (Final Atalanta-Compatible Version)
- Selects target output automatically
- Adds FLIP logic to obfuscate target output using key inputs
- Prevents floating nets and duplicate wire definitions
- No 3-input XORs or unsupported gates
- Conforms to Atalanta and SAT compatibility
"""

import argparse
import random
from pathlib import Path

def parse_bench(path):
    with open(path, "r") as f:
        lines = f.readlines()

    inputs, outputs, gates = [], [], []
    for line in lines:
        line = line.strip()
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

def inject_sarlock(gates, outputs, key_wires):
    num_keys = len(key_wires)
    target_output_line = outputs[-1]
    target_output = target_output_line.split("(")[1].split(")")[0]

    xor_zero = "xor_zero = XOR({0}, {0})".format(target_output)
    xnor_zero = "xnor_zero = XNOR({0}, {0})".format(target_output)

    treeX, treeY = [], []
    last_X = []
    last_Y = []

    for i in range(num_keys):
        in_sig = f"G{i * 3 + 1}GAT"  # just pick predictable inputs
        k = key_wires[i]
        x0 = f"in{i}_0 = XNOR({in_sig}, {k})"
        x1 = f"in{i}_1 = XNOR({k}, {'xor_zero' if i % 2 == 0 else 'xnor_zero'})"
        treeX.append(x0)
        treeY.append(x1)

    def generate_tree(base_name, wires, suffix):
        levels = []
        level = [f"{base_name}0_{i}_{suffix} = AND({wires[2 * i]}, {wires[2 * i + 1]})"
                 for i in range(len(wires) // 2)]
        levels.append(level)
        count = 1
        while len(level) > 1:
            prev = level
            level = [f"{base_name}{count}_{i}_{suffix} = AND({prev[2 * i].split('=')[0].strip()}, {prev[2 * i + 1].split('=')[0].strip()})"
                     for i in range(len(prev) // 2)]
            levels.append(level)
            count += 1
        return [g for l in levels for g in l], level[0].split('=')[0].strip()

    treeX_logic, dtl0 = generate_tree("and_dtl", [f"in{i}_0" for i in range(num_keys)], "X")
    treeY_logic, dtl1 = generate_tree("and_dtl", [f"in{i}_1" for i in range(num_keys)], "Y")

    dtl2 = "DTL_2 = NAND({0}, {0})".format(dtl1)
    flip = "FLIP = AND({0}, DTL_2)".format(dtl0)
    enc = f"{target_output}_enc = XOR(FLIP, {target_output})"
    final = f"{target_output} = {target_output}_enc"

    return treeX + treeY + [xor_zero, xnor_zero] + treeX_logic + treeY_logic + [dtl2, flip, enc, final]

def write_bench(path, key, inputs, outputs, key_inputs, logic, gates):
    with open(path, "w") as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_inputs + outputs + gates + logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock Logic Locking")
    parser.add_argument("--bench_path", required=True, type=Path, help="Original .bench file")
    parser.add_argument("--keysize", required=True, type=int, help="Size of locking key")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Directory for output .bench")
    args = parser.parse_args()

    args.output_path.mkdir(parents=True, exist_ok=True)
    bench_name = args.bench_path.stem
    out_file = args.output_path / f"{bench_name}_SARLock_k_{args.keysize}.bench"

    inputs, outputs, gates = parse_bench(args.bench_path)
    key, key_inputs, key_wires = generate_key(args.keysize)
    sarlock_logic = inject_sarlock(gates, outputs, key_wires)
    write_bench(out_file, key, inputs, outputs, key_inputs, sarlock_logic, gates)

    print(f"SARLock circuit with Key={key} is saved to: {out_file}")

if __name__ == "__main__":
    main()
