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

"""
SARLock logic locking script (compliant with Atalanta and validated structure):
- Preserves original primary inputs and outputs
- Renames target output (e.g., G370GAT) to G370GAT_enc
- Inserts keyinput declarations
- Keeps FLIP and DTL_* internal only (no OUTPUT)
- Final output = XOR(FLIP, <original output>)
"""

def split_bench(lines):
    header, body = [], []
    in_body = False
    for line in lines:
        if not in_body and '=' in line:
            in_body = True
        if in_body:
            body.append(line)
        else:
            header.append(line)
    return header, body

def parse_header(header):
    pis, pos = [], []
    for line in header:
        if line.strip().startswith("INPUT("):
            pis.append(line.strip())
        elif line.strip().startswith("OUTPUT("):
            pos.append(line.strip())
    return pis, pos

def generate_random_key(k):
    return ''.join(random.choice('01') for _ in range(k))

def build_and_tree(terms, prefix, logic):
    level = 0
    current = terms
    while len(current) > 1:
        next_level = []
        for i in range(0, len(current), 2):
            if i + 1 < len(current):
                gate = f"{prefix}_{level}_{i//2}"
                logic.append(f"{gate} = AND({current[i]}, {current[i+1]})")
                next_level.append(gate)
            else:
                next_level.append(current[i])
        current = next_level
        level += 1
    return current[0]

def generate_sarlock_logic(key_bits, pis_nets, orig_output):
    enc_output = f"{orig_output}_enc"
    logic = []
    logic.append("# BEGIN SARLOCK LOGIC")

    # Pseudo patterns
    logic.append(f"pattern_1 = XNOR({orig_output}, {orig_output})")
    logic.append(f"pattern_0 = XOR({orig_output}, {orig_output})")

    # Comparator chains
    terms0, terms2 = [], []
    for i, bit in enumerate(key_bits):
        pi = pis_nets[i]
        logic.append(f"in{i}_0 = XNOR({pi}, keyinput{i})")
        terms0.append(f"in{i}_0")

        pat = "pattern_1" if bit == '1' else "pattern_0"
        logic.append(f"in{i}_2 = XNOR(keyinput{i}, {pat})")
        terms2.append(f"in{i}_2")

    t0 = build_and_tree(terms0, 'd0', logic)
    t2 = build_and_tree(terms2, 'd2', logic)

    logic.append(f"DTL_0 = {t0}")
    logic.append(f"DTL_2 = NAND({t2}, {t2})")  # ensures it's used

    logic.append("FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{orig_output} = XOR(FLIP, {enc_output})")

    logic.append("# END SARLOCK LOGIC")
    return logic

def insert_sarlock(bench_path, output_path, keysize, orig_output='G370GAT'):
    lines = Path(bench_path).read_text().splitlines()
    header, body = split_bench(lines)
    pis, pos = parse_header(header)
    pis_nets = [line[6:-1] for line in pis]

    key = generate_random_key(keysize)
    key_bits = list(key)
    enc_output = f"{orig_output}_enc"

    # Write new header with key and keyinputs
    new_header = [f"#key={key}"] + pis
    for i in range(keysize):
        new_header.append(f"INPUT(keyinput{i})")
    new_header += pos  # keep outputs as-is

    # Rename original target output assignment
    new_body = []
    for line in body:
        if line.strip().startswith(f"{orig_output} ="):
            rhs = line.split("=", 1)[1].strip()
            new_body.append(f"{enc_output} = {rhs}")
        else:
            new_body.append(line.strip())

    # Append SARLock logic
    sarlock_logic = generate_sarlock_logic(key_bits, pis_nets, orig_output)
    new_body += sarlock_logic

    # Write final .bench file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text('\n'.join(new_header + new_body) + '\n')
    print(f"[✓] SARLock with key={key} written to {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Insert SARLock logic into a .bench file')
    parser.add_argument('--bench_path', required=True, help='Path to input .bench file')
    parser.add_argument('--keysize', type=int, default=16, help='Size of the logic locking key')
    parser.add_argument('--output_path', type=Path, default=Path('locked_circuits'), help='Output path or directory')
    args = parser.parse_args()

    out = args.output_path
    if out.suffix == '' or str(out).endswith(os.sep):
        out = out / f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"

    insert_sarlock(args.bench_path, out, args.keysize)
