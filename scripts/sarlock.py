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
    """Split into header (INPUT/OUTPUT) and body (all gates)."""
    header, body = [], []
    in_body = False
    for ln in lines:
        stripped = ln.strip()
        # first non‐declaration with “=” marks start of body
        if not in_body and "=" in ln and not stripped.startswith(("INPUT(", "OUTPUT(")):
            in_body = True
        if in_body:
            body.append(stripped)
        else:
            header.append(stripped)
    return header, body

def build_and_tree(terms, prefix, logic):
    """Recursively collapse a list of terms into a balanced AND‐tree."""
    level = 0
    cur = terms
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur), 2):
            if i + 1 < len(cur):
                out = f"{prefix}{level}_{i//2}"
                logic.append(f"{out} = AND({cur[i]}, {cur[i+1]})")
                nxt.append(out)
            else:
                nxt.append(cur[i])
        cur = nxt
        level += 1
    return cur[0]

def insert_sarlock(bench_path, output_path, keysize, orig_output="G370GAT"):
    lines = Path(bench_path).read_text().splitlines()
    header, body = split_bench(lines)

    # primary inputs and outputs
    pis = [ln for ln in header if ln.startswith("INPUT(")]
    pos = [ln for ln in header if ln.startswith("OUTPUT(")]
    pis_nets = [ln[6:-1] for ln in pis]

    # generate key
    key = "".join(random.choice("01") for _ in range(keysize))
    enc_output = f"{orig_output}_enc"

    # 1) New header: #key, original PIs, keyinputs, original POs
    new_header = [f"#key={key}"]
    new_header += pis
    for i in range(keysize):
        new_header.append(f"INPUT(keyinput{i})")
    new_header += pos

    # 2) New body: rename the original assignment to enc_output
    new_body = []
    for ln in body:
        if ln.startswith(f"{orig_output}") and "=" in ln:
            rhs = ln.split("=",1)[1].strip()
            new_body.append(f"{enc_output} = {rhs}")
        else:
            new_body.append(ln)

    # 3) Append SARLock logic *in exact order* so nothing floats:
    #    pattern_1, pattern_0
    new_body.append(f"pattern_1 = XNOR({orig_output}, {orig_output})")
    new_body.append(f"pattern_0 = XOR({orig_output}, {orig_output})")

    #    comparator XNOR chains
    terms0, terms2 = [], []
    for i, bit in enumerate(key):
        pi = pis_nets[i]
        new_body.append(f"in{i}_0 = XNOR({pi}, keyinput{i})")
        terms0.append(f"in{i}_0")
        patt = "pattern_1" if bit=="1" else "pattern_0"
        new_body.append(f"in{i}_2 = XNOR(keyinput{i}, {patt})")
        terms2.append(f"in{i}_2")

    #    build AND-trees
    logic_accum = []
    t0 = build_and_tree(terms0, "d0_", logic_accum)
    t2 = build_and_tree(terms2, "d2_", logic_accum)
    new_body += logic_accum

    #    DTL nets and FLIP
    new_body.append(f"DTL_0 = {t0}")
    new_body.append(f"DTL_2 = NAND({t2}, {t2})")
    new_body.append(f"FLIP = AND(DTL_0, DTL_2)")

    #    final XOR driving the real output
    new_body.append(f"{orig_output} = XOR(FLIP, {enc_output})")

    # 4) Write everything out
    os.makedirs(Path(output_path).parent, exist_ok=True)
    with open(output_path, "w") as f:
        for ln in new_header:
            f.write(ln + "\n")
        for ln in new_body:
            f.write(ln + "\n")

    print(f"SARLock logic with key={key} written to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Insert SARLock logic into a .bench file.")
    parser.add_argument("--bench_path", required=True, help="Original .bench file")
    parser.add_argument("--keysize", type=int, default=16, help="Number of key bits")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"), help="Directory or file for locked output")
    args = parser.parse_args()

    out = args.output_path
    if out.suffix == "" or str(out).endswith(os.sep):
        out = Path(out) / f"{Path(args.bench_path).stem}_SARLock_k_{args.keysize}.bench"
    insert_sarlock(args.bench_path, out, args.keysize)
