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
Final SARLock logic locking (Atalanta-compatible, CAC-inspired).
- Inserts XOR-based output obfuscation using FLIP signal.
- Ensures all generated signals are consumed.
- Avoids floating nets by marking unused key structures as OUTPUTs.
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

def extract_primary_output(outputs):
    return [line.split("(")[1].split(")")[0] for line in outputs]

def generate_key(k):
    bits = ''.join(random.choice("01") for _ in range(k))
    decls = [f"INPUT(keyinput{i})" for i in range(k)]
    wires = [f"keyinput{i}" for i in range(k)]
    return bits, decls, wires

def sarlock_logic(primary_inputs, keyinputs, keybits, locked_output):
    logic = []
    aux_outputs = []

    # Pattern generators
    logic.append(f"pattern_1 = XNOR({locked_output}, {locked_output})")
    logic.append(f"pattern_0 = XOR({locked_output}, {locked_output})")

    # Comparator logic
    xor_terms_0, xor_terms_2 = [], []
    for i, pi in enumerate(primary_inputs[:len(keybits)]):
        ki = keyinputs[i]
        kb = keybits[i]
        logic.append(f"in{i}_0 = XNOR({pi}, {ki})")
        logic.append(f"in{i}_2 = XNOR({ki}, pattern_{kb})")
        xor_terms_0.append(f"in{i}_0")
        xor_terms_2.append(f"in{i}_2")

    def tree(terms, prefix):
        cur = terms
        level = 0
        while len(cur) > 1:
            nxt = []
            for j in range(0, len(cur), 2):
                if j+1 < len(cur):
                    out = f"{prefix}_{level}_{j//2}"
                    logic.append(f"{out} = AND({cur[j]}, {cur[j+1]})")
                    nxt.append(out)
                else:
                    nxt.append(cur[j])
            cur = nxt
            level += 1
        return cur[0]

    dtl0 = tree(xor_terms_0, "d0")
    dtl2in = tree(xor_terms_2, "d2")

    logic.append(f"DTL_0 = {dtl0}")
    logic.append(f"DTL_2 = NAND({dtl2in}, {dtl2in})")
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")

    flip_xored = f"{locked_output}_enc"
    logic.append(f"{flip_xored} = XOR(FLIP, {locked_output})")

    # Update output to obfuscated version
    logic.append(f"{locked_output} = {flip_xored}")

    # Prevent floating nets
    aux_outputs += [f"OUTPUT(DTL_2)", f"OUTPUT({flip_xored})"]

    return logic, aux_outputs

def write_locked_bench(path, key, inputs, outputs, gates, key_decls, extra_logic, extra_outputs):
    with open(path, 'w') as f:
        f.write(f"#key={key}\n")
        for line in inputs + key_decls + outputs + extra_outputs + gates + extra_logic:
            f.write(f"{line}\n")

def main():
    parser = argparse.ArgumentParser(description="SARLock logic locking")
    parser.add_argument("--bench_path", required=True, type=Path)
    parser.add_argument("--keysize", type=int, default=16)
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"))
    args = parser.parse_args()

    bench_file = args.bench_path
    out_file = args.output_path / f"{bench_file.stem}_SARLock_k_{args.keysize}.bench"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    inputs, outputs, gates = parse_bench(bench_file)
    output_wires = extract_primary_output(outputs)
    key, key_decls, key_wires = generate_key(args.keysize)

    # Choose locked output (first primary output, usually G370GAT)
    locked_output = output_wires[0]
    pi_wires = [line[6:-1] for line in inputs]

    sar_logic, extra_outputs = sarlock_logic(pi_wires, key_wires, key, locked_output)
    write_locked_bench(out_file, key, inputs, outputs, gates, key_decls, sar_logic, extra_outputs)

    print(f"SARLock inserted on {locked_output} with key={key}")
    print(f"Output saved to {out_file}")

if __name__ == "__main__":
    main()
