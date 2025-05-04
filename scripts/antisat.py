#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
import os
import random

# # sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import parse_bench_file, write_list_to_file

def parse_args():
    parser = argparse.ArgumentParser(description="Insert Anti-SAT locking.")
    parser.add_argument("--bench_path", type=Path, required=True, help="Path to the original bench file.")
    parser.add_argument("--keysize", type=int, required=True, help="Size of the locking key.")
    parser.add_argument("--output_path", type=Path, default=Path("locked_circuits"),
                        help="Directory or file for locked output")
    return parser.parse_args()

def generate_key(keysize):
    return ''.join(random.choice("01") for _ in range(keysize))

def write_locked_bench(original_lines, key_bits, filepath, fanin_nodes, protected_output):
    keysize = len(key_bits)

    header, body = [], []
    in_body = False
    for line in original_lines:
        if not in_body and '=' in line:
            in_body = True
        (body if in_body else header).append(line)

    inputs = [line.strip() for line in header if line.startswith("INPUT(")]
    outputs = [line.strip() for line in header if line.startswith("OUTPUT(")]

    new_header = [f"#key={''.join(key_bits)}"] + inputs
    for i in range(keysize):
        new_header.append(f"INPUT(KEYINPUT{i})")
    new_header += outputs

    updated_body = []
    enc_output = f"{protected_output}_enc"
    for line in body:
        if line.startswith(f"{protected_output} ="):
            rhs = line.split("=")[1].strip()
            updated_body.append(f"{enc_output} = {rhs}")
        else:
            updated_body.append(line)

    f_lines, fbar_lines, final_lines = [], [], []
    f_outputs, fbar_outputs = [], []

    for i in range(keysize):
        xi = fanin_nodes[i]
        ki = f"KEYINPUT{i}"
        not_ki = f"KEYINPUT_NOT{i}"
        xor_f = f"XOR_F_{i}"
        xor_fbar = f"XOR_FBAR_{i}"

        f_lines.append(f"{not_ki} = NOT({ki})")
        f_lines.append(f"{xor_f} = XOR({xi}, {ki})")
        fbar_lines.append(f"{xor_fbar} = XOR({xi}, {not_ki})")

        f_outputs.append(xor_f)
        fbar_outputs.append(xor_fbar)

    def build_and_tree(terms, prefix):
        level = 0
        current = terms
        while len(current) > 1:
            next_level = []
            for i in range(0, len(current), 2):
                if i + 1 < len(current):
                    out = f"{prefix}_AND_{level}_{i//2}"
                    final_lines.append(f"{out} = AND({current[i]}, {current[i+1]})")
                    next_level.append(out)
                else:
                    next_level.append(current[i])
            current = next_level
            level += 1
        return current[0]

    f_root = build_and_tree(f_outputs, "F")
    fbar_root = build_and_tree(fbar_outputs, "FBAR")

    antisat_and = "ANTISAT_AND"
    antisat_out = "LOCK_ENABLE"
    final_lines.append(f"{antisat_and} = AND({f_root}, {fbar_root})")
    final_lines.append(f"{antisat_out} = NOT({antisat_and})")

    corrupt_val = "CORRUPTED_VAL"
    final_lines.append(f"{corrupt_val} = NOT({enc_output})")
    final_lines.append(f"{protected_output} = AND({antisat_out}, {enc_output})")

    with open(filepath, "w") as f:
        f.write('\n'.join(new_header + updated_body + ["# BEGIN ANTISAT LOGIC"] + f_lines + fbar_lines + final_lines + ["# END ANTISAT LOGIC"]) + '\n')

def extract_primary_output(lines):
    for line in lines:
        if line.startswith("OUTPUT("):
            return line.strip()[7:-1]
    return None

def extract_fanin_nodes(lines, count):
    fanin_nodes = []
    for line in lines:
        if "=" in line:
            rhs = line.strip().split("=")[1]
            inputs = rhs[rhs.find("(")+1:rhs.find(")")].split(",")
            inputs = [i.strip() for i in inputs]
            fanin_nodes.extend(inputs)
            fanin_nodes = list(dict.fromkeys(fanin_nodes))  # Deduplicate
        if len(fanin_nodes) >= count:
            break
    return fanin_nodes[:count]

def main():
    args = parse_args()
    bench_path = args.bench_path
    keysize = args.keysize
    output_dir = args.output_path
    output_dir.mkdir(parents=True, exist_ok=True)

    key = generate_key(keysize)
    key_bits = list(key)
    out_file = output_dir / f"{bench_path.stem}_AntiSatLock_k_{keysize}.bench"

    with open(bench_path, "r") as f:
        lines = f.readlines()

    protected_output = extract_primary_output(lines)
    fanin_nodes = extract_fanin_nodes(lines, keysize)

    write_locked_bench(lines, key_bits, out_file, fanin_nodes, protected_output)
    print(f"Anti-SAT locked file with key={key} saved to: {out_file}")

if __name__ == "__main__":
    main()
