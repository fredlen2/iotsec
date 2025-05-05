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

import argparse
import random
from pathlib import Path

def parse_bench(path):
    lines = path.read_text().splitlines()
    inputs, outputs, gates = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line.strip())
        elif line.startswith("OUTPUT("):
            outputs.append(line.strip())
        elif "=" in line:
            gates.append(line.strip())
    return inputs, outputs, gates

def generate_key(keysize):
    key = ''.join(random.choice("01") for _ in range(keysize))
    key_inputs = [f"INPUT(keyinput{i})" for i in range(keysize)]
    key_signals = [f"keyinput{i}" for i in range(keysize)]
    return key, key_inputs, key_signals

def build_and_tree(terms, prefix, logic):
    lvl = 0
    cur = terms
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur), 2):
            if j + 1 < len(cur):
                out = f"{prefix}_{lvl}_{j//2}"
                logic.append(f"{out} = AND({cur[j]}, {cur[j+1]})")
                nxt.append(out)
            else:
                nxt.append(cur[j])
        cur = nxt
        lvl += 1
    return cur[0]

def insert_sarlock_logic(target_output, key_bits, pis, key_signals):
    logic = []
    terms_real, terms_key = [], []

    # Patterns
    logic.append(f"pattern_1 = XNOR({target_output}, {target_output})")
    logic.append(f"pattern_0 = XOR({target_output}, {target_output})")

    for i, (pi, kb) in enumerate(zip(pis, key_bits)):
        logic.append(f"in{i}_0 = XNOR({pi}, {key_signals[i]})")
        terms_real.append(f"in{i}_0")
        pat = "pattern_1" if kb == "1" else "pattern_0"
        logic.append(f"in{i}_1 = XNOR({key_signals[i]}, {pat})")
        terms_key.append(f"in{i}_1")

    and_tree_0 = build_and_tree(terms_real, "d0", logic)
    and_tree_1 = build_and_tree(terms_key, "d1", logic)

    logic.append(f"DTL_0 = {and_tree_0}")
    logic.append(f"DTL_2 = NAND({and_tree_1}, {and_tree_1})")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{target_output}_enc = XOR(FLIP, {target_output})")
    return logic

def replace_target_assignment(gates, target):
    for i, line in enumerate(gates):
        if line.startswith(target + " "):
            left, right = line.split("=")
            gates[i] = f"{target}_orig = {right.strip()}"
            return gates
    raise ValueError(f"Target output '{target}' not found in circuit.")

def main():
    parser = argparse.ArgumentParser(description="SARLock Insertion Script (Auto Target)")
    parser.add_argument("--bench_path", required=True, type=Path)
    parser.add_argument("--keysize", required=True, type=int)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    inputs, outputs, gates = parse_bench(args.bench_path)
    pis = [line.split("(")[1].split(")")[0] for line in inputs]
    pos = [line.split("(")[1].split(")")[0] for line in outputs]

    key, key_input_decls, key_signals = generate_key(args.keysize)
    target_output = pos[-1]  # Use last primary output as target

    updated_gates = replace_target_assignment(gates, target_output)
    sarlock_logic = insert_sarlock_logic(target_output + "_orig", list(key), pis, key_signals)

    new_outputs = outputs + [f"OUTPUT({target_output}_enc)", "OUTPUT(DTL_2)"]
    new_gates = updated_gates + sarlock_logic

    args.output_path.mkdir(parents=True, exist_ok=True)
    out_file = args.output_path / f"{args.bench_path.stem}_SARLock_k_{args.keysize}.bench"
    with out_file.open("w") as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_input_decls + new_outputs + new_gates:
            f.write(line + "\n")

    print(f"SARLock-locked circuit with key={key} saved to: {out_file}")
    print(f"Target output locked: {target_output}")

if __name__ == "__main__":
    main()
