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
NB: not being used.
SARLock logic locking for .bench circuits, following the functional example:
- Preserves original primary inputs and outputs
- Renames original target output to <orig>_enc
- Builds two balanced comparator trees over actual PIs and keyinputs
- Uses NAND for second tree, AND for first, then combines via FLIP
- Declares DTL_0 and DTL_2 as primary outputs to prevent floating nets
- Drives final original output via XOR(FLIP, <orig>_enc)
"""

def split_bench(lines):
    """Split .bench file lines into header (PI/PO) and body."""
    header, body = [], []
    in_body = False
    for line in lines:
        if not in_body and '=' in line:
            in_body = True
        (body if in_body else header).append(line)
    return header, body

def parse_ios(header):
    """Extract primary inputs and outputs from header."""
    inputs, outputs = [], []
    for line in header:
        line = line.strip()
        if line.startswith("INPUT("):
            inputs.append(line)
        elif line.startswith("OUTPUT("):
            outputs.append(line)
    return inputs, outputs

def generate_key(keysize):
    return ''.join(random.choice("01") for _ in range(keysize))

def build_and_tree(terms, prefix, logic):
    """Builds a balanced AND tree for a list of terms."""
    level = 0
    current = terms
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                out = f"{prefix}_{level}_{i//2}"
                logic.append(f"{out} = AND({current[i]}, {current[i+1]})")
                next_level.append(out)
            else:
                next_level.append(current[i])
        current = next_level
        level += 1
    return current[0]

def generate_sarlock_logic(pis_nets, key_bits, keysize, protected_output):
    logic = []
    xor_terms_0, xor_terms_2 = [], []

    # Pattern constants (always used)
    logic.append(f"pattern_1 = XNOR({protected_output}, {protected_output})")
    logic.append(f"pattern_0 = XOR({protected_output}, {protected_output})")

    # Comparators and pattern match
    for i in range(keysize):
        pi = pis_nets[i]
        logic.append(f"in{i}_0 = XNOR({pi}, keyinput{i})")
        xor_terms_0.append(f"in{i}_0")

        pattern = 'pattern_1' if key_bits[i] == '1' else 'pattern_0'
        logic.append(f"in{i}_2 = XNOR(keyinput{i}, {pattern})")
        xor_terms_2.append(f"in{i}_2")

    # AND trees
    dtl0 = build_and_tree(xor_terms_0, "d0", logic)
    dtl2_in = build_and_tree(xor_terms_2, "d2", logic)

    logic.append(f"DTL_0 = {dtl0}")
    logic.append(f"DTL_2 = NAND({dtl2_in}, {dtl2_in})")
    logic.append("FLIP = AND(DTL_0, DTL_2)")

    # Final XOR with locked output
    logic.append(f"{protected_output} = XOR(FLIP, {protected_output}_enc)")

    return logic

def insert_sarlock_logic(bench_path, output_path, keysize, protected_output='G370GAT'):
    lines = Path(bench_path).read_text().splitlines()
    header, body = split_bench(lines)
    inputs, outputs = parse_ios(header)
    pis_nets = [line[6:-1] for line in inputs]  # Strip "INPUT(...)" to get names

    key = generate_key(keysize)
    key_bits = list(key)
    enc_output = f"{protected_output}_enc"

    # Modify header
    new_header = [f"#key={key}"] + inputs
    for i in range(keysize):
        new_header.append(f"INPUT(keyinput{i})")
    new_header += outputs

    # Ensure no floating key outputs
    sarlock_extra_outputs = ['DTL_0', 'DTL_2', 'FLIP', enc_output]
    for signal in sarlock_extra_outputs:
        if not any(signal in line for line in lines) and f"OUTPUT({signal})" not in new_header:
            new_header.append(f"OUTPUT({signal})")

    # Rename protected_output assignment to *_enc
    new_body = []
    for line in body:
        if line.startswith(f"{protected_output} ="):
            rhs = line.split("=", 1)[1].strip()
            new_body.append(f"{enc_output} = {rhs}")
        else:
            new_body.append(line)

    # Append SARLock logic
    sarlock_logic = generate_sarlock_logic(pis_nets, key_bits, keysize, protected_output)
    new_body += ["# BEGIN SARLOCK LOGIC"] + sarlock_logic + ["# END SARLOCK LOGIC"]

    # Write to file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text('\n'.join(new_header + new_body) + '\n')
    print(f"SARLock with key={key} written to {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Insert SARLock logic into a .bench file.")
    parser.add_argument('--bench_path', required=True, help='Input .bench file path')
    parser.add_argument('--keysize', type=int, default=16, help='Number of key bits')
    parser.add_argument('--output_path', type=Path, default=Path('locked_circuits'), help='Output file or directory')
    args = parser.parse_args()

    out = args.output_path
    if out.suffix == '' or str(out).endswith(os.sep):
        out = Path(out) / f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"

    insert_sarlock_logic(args.bench_path, out, args.keysize)
