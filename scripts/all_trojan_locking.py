#!/usr/bin/env python3
"""
Run all Trojan-locking scripts in sequence against a single .bench file.
"""
import argparse
import subprocess
from pathlib import Path

TOOLS = [
    "scripts/antisat_trojan.py",
    "scripts/corrupt_and_correct_trojan.py",
    "scripts/sarlock_trojan.py",
]

def main():
    p = argparse.ArgumentParser(description="Run all Trojan locks.")
    p.add_argument("-b", "--bench_path", type=Path, required=True, help="Input .bench file")
    p.add_argument("-k", "--keysize",    type=int,  default=16, help="Number of key bits")
    args = p.parse_args()

    if not args.bench_path.is_file():
        print(f"ERROR: {args.bench_path} not found")
        return

    for tool in TOOLS:
        print(f"→ {tool}")
        subprocess.run([
            "python3", tool,
            "--bench_path", str(args.bench_path),
            "--keysize",    str(args.keysize)
        ], check=True)

    print("Done. Check locked_circuits/ for the outputs.")

if __name__=="__main__":
    main()
