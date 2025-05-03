#!/usr/bin/env python3
"""
Lock a bench circuit with Anti-SAT and insert a stealthy hardware Trojan,
using random key generation and trigger selection.
"""
import argparse
import logging
import secrets
from pathlib import Path
import sys

# Ensure the tools directory is on the import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.utils.utils import parse_bench_file, write_list_to_file


def antisat_trojan_lock(inputs, outputs, base_gates, keysize, trojan_indices):
    """
    Apply Anti-SAT locking with Trojan insertion.

    Args:
        inputs (List[str]): original input signals.
        outputs (List[str]): original output signals.
        base_gates (List[str]): original gate definitions.
        keysize (int): number of key bits.
        trojan_indices (List[int]): indices of key bits for Trojan trigger.

    Returns:
        input_decls (List[str]), output_decls (List[str]), key_inputs (List[str]), locked_gates (List[str])
    """
    # Key input declarations
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    input_decls = [f"INPUT({sig})" for sig in inputs + key_inputs]
    output_decls = [f"OUTPUT({sig})" for sig in outputs]

    # Standard Anti-SAT construction
    xor_signals = [f"x{i}" for i in range(keysize)]
    xor_gates = [
        f"{xor_signals[i]} = XOR({inputs[i % len(inputs)]}, {key_inputs[i]})"
        for i in range(keysize)
    ]
    and_gates = []
    for i, sig in enumerate(xor_signals):
        and_gates.append(
            f"n{i} = {sig}" if i == 0 else f"n{i} = AND({sig}, n{i-1})"
        )

    # Rename protected output
    protected = outputs[0]
    locked_gates = []
    for gate in base_gates:
        if gate.startswith(f"{protected} ="):
            locked_gates.append(f"{protected}_orig = {protected}")
        else:
            locked_gates.append(gate)

    # Combine Anti-SAT gates
    locked_gates += xor_gates + and_gates
    locked_gates.append(f"{protected} = AND({protected}_orig, NOT(n{keysize-1}))")

    # Trojan insertion
    trigger_terms = [key_inputs[i] for i in trojan_indices if i < keysize]
    locked_gates.append(f"trojan_trigger = AND({', '.join(trigger_terms)})")
    locked_gates.append(f"{protected} = XOR({protected}, trojan_trigger)")

    return input_decls, output_decls, key_inputs, locked_gates


def main():
    parser = argparse.ArgumentParser(
        description="Insert Anti-SAT locking and Trojan into a bench file with random keys."
    )
    parser.add_argument(
        "--bench_path", "-b", type=Path,
        help="Path to the original .bench file"
    )
    parser.add_argument(
        "--keysize", "-k", type=int, required=True,
        help="Number of key bits"
    )
    parser.add_argument(
        "--trojan-indices", "-t", type=int, nargs='+',
        help="Key bit indices for Trojan trigger (default: random selection)"
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=Path("locked_circuits"),
        help="Directory for locked bench files"
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Generate cryptographic random key
    keysize = args.keysize
    key_str = ''.join(secrets.choice('01') for _ in range(keysize))
    key_bits = [int(b) for b in key_str]

    # Determine trojan trigger bits
    if args.trojan_indices:
        trojan_indices = args.trojan_indices
    else:
        trojan_indices = secrets.SystemRandom().sample(range(keysize), min(3, keysize))

    # Parse the original bench
    inputs, outputs, base_gates, _ = parse_bench_file(str(args.bench_path))

    # Apply locking
    input_decls, output_decls, key_inputs, locked_gates = antisat_trojan_lock(
        inputs, outputs, base_gates, keysize, trojan_indices
    )

    # Prepare output lines
    all_lines = input_decls + output_decls + locked_gates

    # Write locked bench and key vector
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_name = args.bench_path.stem + f"_AntiSAT_Trojan_k_{keysize}.bench"
    out_path = args.output_dir / out_name
    write_list_to_file(all_lines, str(out_path), key_bits)

    # Annotate bench file with key and trigger indices
    lines = out_path.read_text().splitlines(keepends=True)
    lines.insert(0, f"# trojan_indices={trojan_indices}\n")
    lines.insert(0, f"# key={key_str}\n")
    out_path.write_text(''.join(lines))

    logging.info(f"Generated {out_path} with cryptographic key and Trojan triggers.")


if __name__ == "__main__":
    main()
