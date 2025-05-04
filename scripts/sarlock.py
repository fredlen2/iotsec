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
SARLock implementation that generates SAT-attack resistant logic locking using AND, NAND, and XNOR gates only.
Ensures no floating nets by renaming the original output to an intermediate net and inserting the XOR gate per the SARLock paper.
"""

def generate_random_key(keysize):
    return ''.join(random.choice('01') for _ in range(keysize))


def generate_sarlock_logic(key, orig_output='G370GAT', enc_output='G370GAT_enc'):
    """
    Builds the SARLock comparator and XOR logic.
    Returns lists of INPUT declarations, keyinput names, and gate definitions.
    """
    key_bits = list(key)
    logic_lines = []
    keyinputs = []

    # comparator patterns
    logic_lines.append(f'pattern_1 = XNOR({orig_output}, {orig_output})')
    logic_lines.append(f'pattern_0 = XOR({orig_output}, {orig_output})')

    # generate keyinput declarations
    for i in range(len(key_bits)):
        ki = f'keyinput{i}'
        keyinputs.append(ki)
        logic_lines.append(f'INPUT({ki})')

    # build two sets of XNOR chains
    inter0 = []
    inter2 = []
    for i, bit in enumerate(key_bits):
        pi = f'G{i*7 % 116 + 1}GAT'
        xor0 = f'in{i}_0 = XNOR({pi}, keyinput{i})'
        logic_lines.append(xor0)
        inter0.append(f'in{i}_0')
        pattern = 'pattern_1' if bit=='1' else 'pattern_0'
        xor2 = f'in{i}_2 = XNOR(keyinput{i}, {pattern})'
        logic_lines.append(xor2)
        inter2.append(f'in{i}_2')

    # recursively build AND tree
    def build_tree(terms, name):
        level=0
        current=terms
        while len(current)>1:
            nxt=[]
            for j in range(0, len(current),2):
                if j+1<len(current):
                    out = f'{name}{level}_{j//2}'
                    logic_lines.append(f'{out} = AND({current[j]}, {current[j+1]})')
                    nxt.append(out)
                else:
                    nxt.append(current[j])
            current=nxt; level+=1
        return current[0]

    t0 = build_tree(inter0, 'd0_')
    t2 = build_tree(inter2, 'd2_')

    logic_lines.append(f'DTL_0 = {t0}')
    logic_lines.append(f'DTL_2 = NAND({t2}, {t2})')
    logic_lines.append('FLIP = AND(DTL_0, DTL_2)')
    logic_lines.append(f'{orig_output} = XOR(FLIP, {enc_output})')

    return keyinputs, logic_lines


def insert_sarlock(bench_path: Path, output_path: Path, keysize: int, orig_output='G370GAT'):
    enc_output = f'{orig_output}_enc'
    key = generate_random_key(keysize)

    # read original bench
    raw = Path(bench_path).read_text().splitlines()
    new_lines = [f'#key={key}']
    inserted=False

    for line in raw:
        ls = line.strip()
        # rename the original output assignment to encoded output
        if ls.startswith(f'{orig_output} ='):
            rhs = ls.split('=',1)[1].strip()
            new_lines.append(f'{enc_output} = {rhs}')
            continue
        # replace OUTPUT(orig) with OUTPUT(enc) and inject key nets
        if ls.startswith(f'OUTPUT({orig_output})'):
            new_lines.append(f'OUTPUT({enc_output})')
            # insert keyinputs and FLIP and new primary output
            keyinputs, logic = generate_sarlock_logic(key, orig_output, enc_output)
            for ki in keyinputs:
                new_lines.append(f'INPUT({ki})')
            new_lines.append('OUTPUT(FLIP)')
            new_lines.append(f'OUTPUT({orig_output})')
            inserted=True
            continue
        # preserve other lines (INPUT, other OUTPUTs, gates)
        new_lines.append(ls)

    if not inserted:
        raise ValueError(f'OUTPUT({orig_output}) not found in {bench_path}')

    # append SARLock comparator and XOR logic at end
    _, logic_lines = generate_sarlock_logic(key, orig_output, enc_output)
    new_lines.extend(logic_lines)

    # write out
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(new_lines))
    print(f'SARLock logic with key={key} written to {output_path}')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description='Insert SARLock logic into a .bench file.')
    parser.add_argument('--bench_path', required=True, help='Original .bench file')
    parser.add_argument('--keysize', type=int, default=16, help='Number of key bits')
    parser.add_argument('--output_path', type=Path, default=Path('locked_circuits'), help='Directory or file for locked output')
    args = parser.parse_args()

    # determine output path
    out = args.output_path
    if out.suffix=='' or str(out).endswith(os.sep):
        out = Path(out)/f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"
    insert_sarlock(Path(args.bench_path), out, args.keysize)
