import argparse
from tools.utils import parse_bench_file, write_list_to_file

def sarlock_lock(inputs, outputs, gates, keysize):
    key_inputs = [f"keyinput{i}" for i in range(keysize)]
    gates.extend([f"INPUT({ki})" for ki in key_inputs])

    output = outputs[0]  # Protecting first output
    protected = f"{output}_orig = {output}"
    gates = [g if not g.startswith(f"{output} ") else protected for g in gates]
    comparator = f"cmp = XOR({inputs[0]}, keyinput0)"
    locked_output = f"{output} = AND({output}_orig, NOT(cmp))"
    gates.extend([comparator, locked_output])
    return key_inputs, gates

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_path")
    parser.add_argument("--keysize", type=int, required=True)
    args = parser.parse_args()

    inputs, outputs, gates, _ = parse_bench_file(args.bench_path)
    key_inputs, locked_gates = sarlock_lock(inputs, outputs, gates, args.keysize)
    all_gates = [f"INPUT({i})" for i in inputs] + [f"OUTPUT({o})" for o in outputs] + locked_gates
    out_path = args.bench_path.replace(".bench", f"_SARLock_k_{args.keysize}.bench")
    write_list_to_file(all_gates, out_path, [1]*args.keysize)

if __name__ == "__main__":
    main()
