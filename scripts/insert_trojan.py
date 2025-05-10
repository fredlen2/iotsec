#!/usr/bin/env python3

import argparse
import random
from pathlib import Path

def parse_bench(path):
    with open(path, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    inputs, outputs, logic = [], [], []
    for line in lines:
        if line.startswith("INPUT("):
            inputs.append(line.split("(")[1].split(")")[0])
        elif line.startswith("OUTPUT("):
            outputs.append(line.split("(")[1].split(")")[0])
        else:
            logic.append(line)
    return inputs, outputs, logic

def generate_trojan_logic(inputs, trigger_size, trojan_id):
    selected = random.sample(inputs, trigger_size)
    logic = []
    inv_wires = []
    for i, sig in enumerate(selected):
        inv = f"trig_{trojan_id}_{i}_inv"
        logic.append(f"{inv} = NOT({sig})")
        inv_wires.append(inv)

    stage = 0
    cur = inv_wires
    while len(cur) > 1:
        nxt = []
        for i in range(0, len(cur), 2):
            if i + 1 < len(cur):
                out = f"trig_{trojan_id}_and_{stage}_{i//2}"
                logic.append(f"{out} = AND({cur[i]}, {cur[i+1]})")
                nxt.append(out)
            else:
                nxt.append(cur[i])
        cur = nxt
        stage += 1
    trigger = cur[0]
    payload = f"trojan_{trojan_id}_payload"
    logic.append(f"{payload} = XOR({trigger}, G1GAT)")
    return logic, payload

def insert_trojan(in_path, trigger_size, num_trojans, out_dir):
    inputs, outputs, gates = parse_bench(in_path)
    stem = in_path.stem
    for t in range(1, num_trojans + 1):
        trojan_logic, payload = generate_trojan_logic(inputs, trigger_size, t)
        modified = gates + trojan_logic
        out_lines = [f"INPUT({inp})" for inp in inputs]
        out_lines += [f"OUTPUT({out})" for out in outputs]
        out_lines += modified
        out_file = out_dir / f"{stem}_HT_trigger_{trigger_size}_{t:02d}.bench"
        with open(out_file, 'w') as f:
            for line in out_lines:
                f.write(f"{line}\n")
        print(f"Generated: {out_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=Path, required=True)
    parser.add_argument("--trigger_size", type=int, default=3)
    parser.add_argument("--num_trojans", type=int, default=50)
    args = parser.parse_args()

    out_dir = Path("locked_circuits")
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.bench_path.is_file() and args.bench_path.suffix == ".bench":
        insert_trojan(args.bench_path, args.trigger_size, args.num_trojans, out_dir)
    elif args.bench_path.is_dir():
        for file in args.bench_path.glob("*.bench"):
            insert_trojan(file, args.trigger_size, args.num_trojans, out_dir)
    else:
        print("Error: Invalid --bench_path. Provide a .bench file or directory.")

if __name__ == "__main__":
    main()
