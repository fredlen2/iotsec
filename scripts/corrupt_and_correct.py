import argparse
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.utils.utils import parse_bench_file, write_list_to_file

def corrupt_and_correct(inputs, outputs, gates, keysize):
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend([f"INPUT({ki})" for ki in key_inputs])

    # Add corruption XOR gate on output
    corrupted_output = outputs[0]
    gates = [g if not g.startswith(f"{corrupted_output} ") else f"{corrupted_output}_orig = {corrupted_output}" for g in gates]

    # Example: XOR 2 key bits to control a corruption gate
    xor1 = f"c1 = XOR({key_inputs[0]}, {key_inputs[1]})"
    xor2 = f"c2 = XOR({corrupted_output}_orig, c1)"
    gates.extend([xor1, xor2])
    gates.append(f"{corrupted_output} = {xor2.split('=')[0].strip()}")

    return key_inputs, gates

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_path")
    parser.add_argument("--keysize", type=int, required=True)
    args = parser.parse_args()

    inputs, outputs, gates, _ = parse_bench_file(args.bench_path)
    key_inputs, locked_gates = corrupt_and_correct(inputs, outputs, gates, args.keysize)
    all_gates = [f"INPUT({i})" for i in inputs] + [f"OUTPUT({o})" for o in outputs] + locked_gates
    
    # Ensure the output directory exists
    output_dir = "locked_circuits"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output file name based on the input file name
    base_name = os.path.basename(args.bench_path)
    out_file = base_name.replace(".bench", f"_CorruptCorrect_k_{args.keysize}.bench")
    out_path = os.path.join(output_dir, out_file)
    
    write_list_to_file(all_gates, out_path, [1]*args.keysize)

if __name__ == "__main__":
    main()