#!/usr/bin/env python3

import argparse
import random
from pathlib import Path
import os
import sys

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
SARLock Logic Locking (Atalanta/SAT-attack compatible)
Injects comparator + mask logic per Yasin et al. HOST 2016 (Fig 5).
"""

import argparse
import random
import re
from pathlib import Path

def parse_bench(path):
    inputs, outputs, gates = [], [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT("):
                inputs.append(line[len("INPUT("):-1])
            elif line.startswith("OUTPUT("):
                outputs.append(line[len("OUTPUT("):-1])
            elif "=" in line:
                gates.append(line)
    return inputs, outputs, gates

def generate_key(keysize):
    return "".join(random.choice("01") for _ in range(keysize))

def build_and_tree(signals, prefix):
    """Build a balanced binary AND‐tree over `signals`."""
    gates = []
    level = 0
    current = signals[:]
    while len(current) > 1:
        nxt = []
        for i in range(0, len(current), 2):
            if i+1 < len(current):
                out = f"{prefix}_L{level}_{i//2}"
                gates.append(f"{out} = AND({current[i]}, {current[i+1]})")
                nxt.append(out)
            else:
                nxt.append(current[i])
        current = nxt
        level += 1
    return current[0], gates

def inject_sarlock_logic(inputs, key_inputs, key_bits, output_name):
    logic = []
    # -- 1) build a NOT gate on inputs[0] to serve as constant source
    const_in = inputs[0]
    const_not = f"{output_name}_const_not"
    logic.append(f"{const_not} = NOT({const_in})")
    # -- 2) constant-0 and constant-1
    zero = f"{output_name}_zero"
    one  = f"{output_name}_one"
    logic.append(f"{zero} = AND({const_in}, {const_not})")  # always 0
    logic.append(f"{one}  = OR({const_in}, {const_not})")   # always 1

    # -- 3) per-bit comparator XNOR(x_i, key_i) and mask XNOR(key_i, const)
    xnor_match = []
    xnor_mask  = []
    for i, bit in enumerate(key_bits):
        xi = inputs[i % len(inputs)]
        ki = key_inputs[i]
        m0 = f"in{i}_match"
        m1 = f"in{i}_mask"
        logic.append(f"{m0} = XNOR({xi}, {ki})")
        const = one if bit == "1" else zero
        logic.append(f"{m1} = XNOR({ki}, {const})")
        xnor_match.append(m0)
        xnor_mask.append(m1)

    # -- 4) build AND-trees
    dtl0_root, dtl0_gates = build_and_tree(xnor_match, "match")
    dtl2_root, dtl2_gates = build_and_tree(xnor_mask,  "mask")
    logic += dtl0_gates + dtl2_gates
    logic.append(f"DTL_0 = {dtl0_root}")
    logic.append(f"DTL_2 = {dtl2_root}")

    # -- 5) final flip signal
    logic.append("FLIP = AND(DTL_0, DTL_2)")

    # -- 6) obfuscate the original output
    logic.append(f"{output_name} = XOR(FLIP, {output_name}_enc)")
    return logic

def apply_sarlock(bench_path, output_dir, keysize):
    inputs, outputs, gates = parse_bench(bench_path)
    key_bits   = generate_key(keysize)
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    output_name = outputs[0]  # lock the first output

    # --- 1) header
    header = [f"#key={key_bits}"]
    header += [f"INPUT({i})" for i in inputs]
    header += [f"INPUT({k})" for k in key_inputs]
    header += [f"OUTPUT({o})" for o in outputs]

    # --- 2) rename original output gate to *_enc
    renamed = []
    pat = re.compile(rf"^{re.escape(output_name)}\s*=")
    for g in gates:
        if pat.match(g):
            rhs = g.split("=",1)[1].strip()
            renamed.append(f"{output_name}_enc = {rhs}")
        else:
            renamed.append(g)

    # --- 3) inject SARLock logic
    sarlock_logic = inject_sarlock_logic(inputs, key_inputs, key_bits, output_name)

    # --- 4) write out
    out_lines = header + renamed + sarlock_logic
    out_dir = Path(output_dir)
    out_dir.mkdir(exist_ok=True, parents=True)
    out_path = out_dir / f"{Path(bench_path).stem}_SARLock_k_{keysize}.bench"
    with open(out_path, "w") as f:
        f.write("\n".join(out_lines) + "\n")

    print(f"SARLock circuit written to {out_path} (key={key_bits})")

def main():
    p = argparse.ArgumentParser(description="Inject SARLock into a .bench")
    p.add_argument("--bench_path",  required=True)
    p.add_argument("--keysize",     type=int, required=True)
    p.add_argument("--output_dir",  default="locked_circuits")
    args = p.parse_args()
    apply_sarlock(args.bench_path, args.output_dir, args.keysize)

if __name__ == "__main__":
    main()
