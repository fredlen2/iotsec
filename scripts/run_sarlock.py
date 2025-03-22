import argparse
import random

def parse_bench_file(file_path):
    """Parses a .bench file and extracts inputs, outputs, and gate definitions."""
    inputs, outputs, gates = [], [], []
    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()
            if line.startswith("INPUT"): 
                inputs.append(line)
            elif line.startswith("OUTPUT"): 
                outputs.append(line)
            elif "=" in line: 
                gates.append(line)
    return inputs, outputs, gates

def insert_sarlock_logic(gates, key_size):
    """Inserts SARLock logic by adding an XNOR-based key comparison."""
    key_inputs = [f"keyinput{i}" for i in range(key_size)]
    key_compare = f"SARLock_XNOR = XNOR({', '.join(key_inputs)})"
    
    # Control output using AND gate
    gates.append(key_compare)
    gates.append(f"SARLock_AND = AND(SARLock_XNOR, {gates[-1].split('=')[0].strip()})")
    
    # Replace final output gate with SARLock-protected output
    gates[-1] = f"{gates[-1].split('=')[0].strip()} = SARLock_AND"
    return gates, key_inputs

def write_locked_bench(file_path, inputs, outputs, gates, key_inputs):
    """Writes the modified benchmark file with SARLock logic."""
    with open(file_path, "w") as file:
        for inp in inputs + [f"INPUT({ki})" for ki in key_inputs]:
            file.write(inp + "\n")
        for out in outputs:
            file.write(out + "\n")
        for gate in gates:
            file.write(gate + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bench_path", type=str, help="Path to the original benchmark file")
    parser.add_argument("--keysize", type=int, required=True, help="Size of the key")
    args = parser.parse_args()
    
    inputs, outputs, gates = parse_bench_file(args.bench_path)
    locked_gates, key_inputs = insert_sarlock_logic(gates, args.keysize)
    
    locked_file = args.bench_path.replace(".bench", f"_SARLock_k_{args.keysize}.bench")
    write_locked_bench(locked_file, inputs, outputs, locked_gates, key_inputs)
    
    print(f"SARLock applied! Locked circuit saved as {locked_file}")

if __name__ == "__main__":
    main()