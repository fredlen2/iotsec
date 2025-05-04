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
SARLock implementation generating SAT-attack resistant logic locking for .bench circuits.
Follows approach from functional c432_SARLock_k_16_1.bench:
- Renames original output to intermediate *_enc net
- Injects actual primary inputs for comparator trees
- Declares DTL_0 and DTL_2 as primary outputs to avoid floating nets
- Builds comparator and XOR per SARLock paper
"""

def generate_random_key(keysize):
    return ''.join(random.choice('01') for _ in range(keysize))


def generate_sarlock_defs(key_bits, primary_inputs, orig_output, enc_output):
    """
    Returns SARLock logic definitions: pattern, comparator XNORs, AND-tree, DTL nets, FLIP, XOR.
    """
    logic = []
    # patterns using renamed enc_output
    logic.append(f'pattern_1 = XNOR({orig_output}, {orig_output})')
    logic.append(f'pattern_0 = XOR({orig_output}, {orig_output})')

    # comparator chains on actual PIs
    n = len(key_bits)
    if len(primary_inputs) < n:
        raise ValueError(f"Need at least {n} primary inputs, found {len(primary_inputs)}")
    in0_terms = []
    in2_terms = []
    for i, bit in enumerate(key_bits):
        pi = primary_inputs[i]
        logic.append(f'in{i}_0 = XNOR({pi}, keyinput{i})')
        in0_terms.append(f'in{i}_0')
        pat = 'pattern_1' if bit=='1' else 'pattern_0'
        logic.append(f'in{i}_2 = XNOR(keyinput{i}, {pat})')
        in2_terms.append(f'in{i}_2')

    # build binary AND-tree
    def and_tree(terms, prefix):
        lvl = 0
        cur = terms
        while len(cur) > 1:
            nxt = []
            for j in range(0, len(cur), 2):
                if j+1 < len(cur):
                    out = f'{prefix}{lvl}_{j//2}'
                    logic.append(f'{out} = AND({cur[j]}, {cur[j+1]})')
                    nxt.append(out)
                else:
                    nxt.append(cur[j])
            cur = nxt; lvl += 1
        return cur[0]

    t0 = and_tree(in0_terms, 'd0_')
    t2 = and_tree(in2_terms, 'd2_')

    logic.append(f'DTL_0 = {t0}')
    logic.append(f'DTL_2 = NAND({t2}, {t2})')
    logic.append('FLIP = AND(DTL_0, DTL_2)')
    logic.append(f'{orig_output} = XOR(FLIP, {enc_output})')

    return logic


def insert_sarlock(bench_path, output_path, keysize, orig_output='G370GAT'):
    enc_output = f'{orig_output}_enc'
    key = generate_random_key(keysize)

    lines = Path(bench_path).read_text().splitlines()
    # collect original primary inputs
    primary_inputs = [ln.split('(')[1].split(')')[0]
                      for ln in lines if ln.startswith('INPUT(') and 'keyinput' not in ln]

    # prepare new file lines
    new_lines = [f'#key={key}']
    inserted = False
    # rename and re-declare nets
    for ln in lines:
        l = ln.strip()
        if l.startswith(f'{orig_output} ='):
            rhs = l.split('=',1)[1].strip()
            new_lines.append(f'{enc_output} = {rhs}')
            continue
        if l.startswith(f'OUTPUT({orig_output})'):
            # replace with enc output
            new_lines.append(f'OUTPUT({enc_output})')
            # inject keyinputs
            for i in range(keysize): new_lines.append(f'INPUT(keyinput{i})')
            # declare DTL nets and FLIP and final output
            new_lines.append('OUTPUT(DTL_0)')
            new_lines.append('OUTPUT(DTL_2)')
            new_lines.append('OUTPUT(FLIP)')
            new_lines.append(f'OUTPUT({orig_output})')
            inserted = True
            continue
        new_lines.append(l)

    if not inserted:
        raise ValueError(f'OUTPUT({orig_output}) not found')

    # append SARLock definitions
    key_bits = list(key)
    defs = generate_sarlock_defs(key_bits, primary_inputs, orig_output, enc_output)
    new_lines.extend(defs)

    # write to file
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text('\n'.join(new_lines) + '\n')
    print(f'SARLock with key={key} written to {output_path}')


if __name__ == '__main__':
    import sys
    p = argparse.ArgumentParser(description='Insert SARLock into .bench')
    p.add_argument('--bench_path', required=True)
    p.add_argument('--keysize', type=int, default=16)
    p.add_argument('--output_path', type=Path, default=Path('locked_circuits'))
    args = p.parse_args()
    out = args.output_path
    if out.suffix == '' or str(out).endswith(os.sep):
        out = Path(out) / f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"
    insert_sarlock(args.bench_path, out, args.keysize)
