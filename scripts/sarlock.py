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
SARLock logic locking script that matches the working c432_SARLock_k_16_1.bench:
- Preserves original primary inputs and outputs
- Renames the original target output (e.g. G370GAT) to <orig>_enc
- Inserts keyinput declarations immediately after original PIs
- Keeps only original outputs in header (no internal nets as outputs)
- Appends SARLock logic at end, with proper ordering so DTL_2 feeds FLIP, FLIP feeds XOR
- Wraps SARLock region in comments for clarity
"""

def split_bench(lines):
    header, body = [], []
    in_body = False
    for ln in lines:
        # switch to body when seeing first gate definition
        if not in_body and '=' in ln and not ln.strip().startswith(('INPUT(', 'OUTPUT(')):
            in_body = True
        if in_body:
            body.append(ln)
        else:
            header.append(ln)
    return header, body


def parse_header(header):
    pis = [ln for ln in header if ln.strip().startswith('INPUT(')]
    pos = [ln for ln in header if ln.strip().startswith('OUTPUT(')]
    return pis, pos


def generate_random_key(k):
    return ''.join(random.choice('01') for _ in range(k))


def build_and_tree(terms, prefix, logic):
    level = 0
    cur = terms
    while len(cur) > 1:
        nxt = []
        for j in range(0, len(cur), 2):
            if j+1 < len(cur):
                out = f'{prefix}{level}_{j//2}'
                logic.append(f'{out} = AND({cur[j]}, {cur[j+1]})')
                nxt.append(out)
            else:
                nxt.append(cur[j])
        cur = nxt
        level += 1
    return cur[0]


def generate_sarlock_defs(key_bits, pis_nets, orig_output):
    enc_output = f'{orig_output}_enc'
    logic = []
    # BEGIN SARLOCK LOGIC
    logic.append('# BEGIN SARLOCK LOGIC')
    # patterns
    logic.append(f'pattern_1 = XNOR({orig_output}, {orig_output})')
    logic.append(f'pattern_0 = XOR({orig_output}, {orig_output})')
    # comparator chains
    terms0, terms2 = [], []
    for i, bit in enumerate(key_bits):
        pi = pis_nets[i]
        logic.append(f'in{i}_0 = XNOR({pi}, keyinput{i})')
        terms0.append(f'in{i}_0')
        pat = 'pattern_1' if bit == '1' else 'pattern_0'
        logic.append(f'in{i}_2 = XNOR(keyinput{i}, {pat})')
        terms2.append(f'in{i}_2')
    # build AND trees
    t0 = build_and_tree(terms0, 'd0_', logic)
    t2 = build_and_tree(terms2, 'd2_', logic)
    # DTL nets and FLIP
    logic.append(f'DTL_0 = {t0}')
    logic.append(f'DTL_2 = NAND({t2}, {t2})')
    logic.append(f'FLIP = AND(DTL_0, DTL_2)')
    # final XOR drives the real output
    logic.append(f'{orig_output} = XOR(FLIP, {enc_output})')
    logic.append('# END SARLOCK LOGIC')
    return logic


def insert_sarlock(bench_path, output_path, keysize, orig_output='G370GAT'):
    # read bench
    lines = Path(bench_path).read_text().splitlines()
    header, body = split_bench(lines)
    pis, pos = parse_header(header)
    # extract PI net names
    pis_nets = [ln.strip()[6:-1] for ln in pis]

    key = generate_random_key(keysize)
    key_bits = list(key)
    enc_output = f'{orig_output}_enc'

    # build new header: key comment, PIs, keyinputs, original POs
    new_header = [f'#key={key}'] + pis
    for i in range(keysize):
        new_header.append(f'INPUT(keyinput{i})')
    new_header += pos

    # build new body: rename orig assignment to enc, preserve others
    new_body = []
    for ln in body:
        l = ln.strip()
        if l.startswith(f'{orig_output}') and '=' in l:
            rhs = l.split('=', 1)[1].strip()
            new_body.append(f'{enc_output} = {rhs}')
        else:
            new_body.append(l)

    # append SARLock logic
    sarlock_defs = generate_sarlock_defs(key_bits, pis_nets, orig_output)
    new_body += sarlock_defs

    # write output
    os.makedirs(Path(output_path).parent, exist_ok=True)
    Path(output_path).write_text('\n'.join(new_header + new_body) + '\n')
    print(f'SARLock with key={key} written to {output_path}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Insert SARLock logic into a .bench file')
    parser.add_argument('--bench_path', required=True, help='Original .bench file')
    parser.add_argument('--keysize', type=int, default=16, help='Number of key bits')
    parser.add_argument('--output_path', type=Path, default=Path('locked_circuits'), help='Directory or file for locked output')
    args = parser.parse_args()

    out = args.output_path
    if out.suffix == '' or str(out).endswith(os.sep):
        out = Path(out) / f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"
    insert_sarlock(args.bench_path, out, args.keysize)
