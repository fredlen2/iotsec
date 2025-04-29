#!/usr/bin/env python3
"""
Lock a bench circuit with SARLock and insert a stealthy hardware Trojan,
using random key generation and trigger selection.
"""
import argparse
import logging
import secrets
import sys
from pathlib import Path

# Ensure the tools directory is on the import path
sys.path.insert(0, str(Path(__file__).parents[1]))
from tools.utils.utils import parse_bench_file, write_list_to_file

def sarlock_trojan_lock(inputs, outputs, base_gates, keysize, trojan_key_idxs):
    """
    Apply SARLock locking with Trojan insertion.

    Args:
        inputs (List[str]): original input signals.
        outputs (List[str]): original output signals.
        base_gates (List[str]): original gate definitions.
        keysize (int): number of key bits.
        trojan_key_idxs (List[int]): key bit indices for Trojan trigger.

    Returns:
        input_decls, output_decls, key_inputs, locked_gates
    """
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    input_decls  = [f"INPUT({sig})" for sig in inputs + key_inputs]
    output_decls = [f"OUTPUT({sig})" for sig in outputs]

    # Rename protected output
    protected = outputs[0]
    locked_gates = []
    for gate in base_gates:
        if gate.startswith(f"{protected} ") or gate.startswith(f"{protected}="):
            locked_gates.append(f"{protected}_orig = {protected}")
        else:
            locked_gates.append(gate)

    # SARLock comparator & locked output
    locked_gates.append(f"cmp = XOR({inputs[0]}, {key_inputs[0]})")
    locked_gates.append(f"{protected} = AND({protected}_orig, NOT(cmp))")

    # Trojan insertion
    trigger_terms = ["cmp"] + [key_inputs[i] for i in trojan_key_idxs if i < keysize]
    locked_gates.append(f"trojan_trigger = AND({', '.join(trigger_terms)})")
    locked_gates.append(f"{protected} = XOR({protected}, trojan_trigger)")

    return input_decls, output_decls, key_inputs, locked_gates

def main():
    parser = argparse.ArgumentParser(
        description="Insert SARLock locking and Trojan into a bench file with random key."
    )
    parser.add_argument("--bench_path", "-b", type=Path, help="Original .bench file path.")
    parser.add_argument("--keysize",  "-k", type=int, required=True, help="Number of key bits.")
    parser.add_argument("--trojan-key-idxs", "-t", type=int, nargs='+',
                        help="Key bit indices for Trojan trigger (random if omitted).")
    parser.add_argument("--output-dir", "-o", type=Path,
                        default=Path("locked_circuits"), help="Output directory.")
    args = parser.parse_args()

    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)

    # Parse original bench
    inputs, outputs, base_gates, _ = parse_bench_file(str(args.bench_path))

    # Generate secure random key
    keysize = args.keysize
    key_str  = ''.join(secrets.choice('01') for _ in range(keysize))
    key_bits = [int(b) for b in key_str]

    # Determine Trojan trigger bits
    trojan_key_idxs = (
        args.trojan_key_idxs
        if args.trojan_key_idxs
        else secrets.SystemRandom().sample(range(keysize), min(3, keysize))
    )

    # Apply locking
    input_decls, output_decls, key_inputs, locked_gates = sarlock_trojan_lock(
        inputs, outputs, base_gates, keysize, trojan_key_idxs
    )

    # Write locked bench + key vector
    all_lines = input_decls + output_decls + locked_gates
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{args.bench_path.stem}_SARLock_Trojan_k_{keysize}.bench"
    write_list_to_file(all_lines, str(out_path), key_bits)

    # Annotate with key and triggers
    lines = out_path.read_text().splitlines(keepends=True)
    lines.insert(0, f"# trojan_key_idxs={trojan_key_idxs}\n")
    lines.insert(0, f"# key={key_str}\n")
    out_path.write_text(''.join(lines))

    logging.info(f"Generated {out_path} with cryptographic key and Trojan triggers.")

if __name__ == "__main__":
    main()
