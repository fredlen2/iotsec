import argparse
from tools.utils import parse_bench_file, write_list_to_file

def antisat_lock(inputs, outputs, gates, keysize):
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend([f"INPUT({ki})" for ki in key_inputs])

    xor_outputs = [f"x{i} = XOR({inputs[i % len(inputs)]}, {key_inputs[i]})" for i in range(keysize)]
    and_gates = [f"n{i} = AND(x{i}, n{i-1})" if i != 0 else f"n0 = {xor_outputs[0].split('=')[1].strip()}" for i in range(keysize)]
    gates.extend(xor_outputs)
    gates.extend(and_gates)
    
    protected = outputs[0]
    gates = [g if not g.startswith(f"{protected} ") else f"{protected}_orig = {protected}" for g in gates]
    final_output = f"{protected} = AND({protected}_orig, NOT(n{keysize - 1}))"
    gates.append(final_output)
    return key_inputs, gates

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_path")
    parser.add_argument("--keysize", type=int, required=True)
    args = parser.parse_args()

    inputs, outputs, gates, _ = parse_bench_file(args.bench_path)
    key_inputs, locked_gates = antisat_lock(inputs, outputs, gates, args.keysize)
    all_gates = [f"INPUT({i})" for i in inputs] + [f"OUTPUT({o})" for o in outputs] + locked_gates
    out_path = args.bench_path.replace(".bench", f"_AntiSAT_k_{args.keysize}.bench")
    write_list_to_file(all_gates, out_path, [1]*args.keysize)

if __name__ == "__main__":
    main()
