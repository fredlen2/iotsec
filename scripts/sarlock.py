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
    header, body = [], []
    in_body = False
    for ln in lines:
        if not in_body and '=' in ln:
            in_body = True
        if in_body:
            body.append(ln)
        else:
            header.append(ln)
    return header, body

def parse_header(header):
    pis, pos = [], []
    for ln in header:
        l = ln.strip()
        if l.startswith('INPUT('):
            pis.append(l)
        elif l.startswith('OUTPUT('):
            pos.append(l)
    return pis, pos

def generate_random_key(k):
    return ''.join(random.choice('01') for _ in range(k))

def build_and_tree(terms, prefix, logic):
    lvl = 0
    cur = terms
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur), 2):
            if j+1 < len(cur):
                out = f'{prefix}_{lvl}_{j//2}'
                logic.append(f'{out} = AND({cur[j]}, {cur[j+1]})')
                nxt.append(out)
            else:
                nxt.append(cur[j])
        cur = nxt
        lvl += 1
    return cur[0]

def generate_sarlock_logic(key_bits, pis_nets, orig_output):
    logic = []
    # SARLock patterns
    logic.append(f"pattern_1 = XNOR({orig_output}, {orig_output})")
    logic.append(f"pattern_0 = XOR({orig_output}, {orig_output})")

    t0_terms, t2_terms = [], []
    for i, bit in enumerate(key_bits):
        logic.append(f"in{i}_0 = XNOR({pis_nets[i]}, keyinput{i})")
        logic.append(f"in{i}_2 = XNOR(keyinput{i}, {'pattern_1' if bit == '1' else 'pattern_0'})")
        t0_terms.append(f"in{i}_0")
        t2_terms.append(f"in{i}_2")

    t0 = build_and_tree(t0_terms, 'd0', logic)
    t2 = build_and_tree(t2_terms, 'd2', logic)

    logic.append(f"DTL_0 = {t0}")
    logic.append(f"DTL_2 = NAND({t2}, {t2})")  # per SARLock design
    logic.append(f"FLIP = AND(DTL_0, DTL_2)")
    logic.append(f"{orig_output} = XOR(FLIP, {orig_output}_enc)")

    return logic, ['DTL_0', 'DTL_2', 'FLIP', f"{orig_output}_enc"]

def insert_sarlock(bench_path, output_path, keysize, orig_output='G370GAT'):
    lines = Path(bench_path).read_text().splitlines()
    header, body = split_bench(lines)
    pis, pos = parse_header(header)
    pis_nets = [line[6:-1] for line in pis]

    key = generate_random_key(keysize)
    key_bits = list(key)
    enc_output = f"{orig_output}_enc"

    new_header = [f"#key={key}"] + pis
    for i in range(keysize):
        new_header.append(f"INPUT(keyinput{i})")
    new_outputs = set([ln[7:-1] for ln in pos])
    new_outputs.add(orig_output)

    # body logic transformation
    new_body = []
    for ln in body:
        l = ln.strip()
        if l.startswith(f"{orig_output} ") and '=' in l:
            rhs = l.split('=', 1)[1].strip()
            new_body.append(f"{enc_output} = {rhs}")
        else:
            new_body.append(l)

    # add SARLock logic
    sarlock_logic, extra_signals = generate_sarlock_logic(key_bits, pis_nets, orig_output)
    new_body.append("# BEGIN SARLOCK LOGIC")
    new_body.extend(sarlock_logic)
    new_body.append("# END SARLOCK LOGIC")

    # Ensure extra signals are declared as OUTPUT if not used
    all_lhs = {line.split('=')[0].strip() for line in new_body if '=' in line}
    all_rhs = set()
    for line in new_body:
        if '=' in line:
            _, rhs = line.split('=')
            all_rhs.update(rhs.strip().replace(')', '').replace('(', '').replace(',', ' ').split())

    floating = [sig for sig in extra_signals if sig in all_lhs and sig not in all_rhs and sig not in new_outputs]
    for sig in floating:
        new_header.append(f"OUTPUT({sig})")

    # final output
    new_header += [f"OUTPUT({o})" for o in new_outputs if f"OUTPUT({o})" not in new_header]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text('\n'.join(new_header + new_body) + '\n')
    print(f"SARLock with key={key} written to {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Insert SARLock logic into .bench")
    parser.add_argument('--bench_path', required=True)
    parser.add_argument('--keysize', type=int, default=16)
    parser.add_argument('--output_path', type=Path, default=Path('locked_circuits'))
    args = parser.parse_args()

    out = args.output_path
    if out.suffix == '' or str(out).endswith(os.sep):
        out = Path(out) / f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"

    insert_sarlock(args.bench_path, out, args.keysize)
