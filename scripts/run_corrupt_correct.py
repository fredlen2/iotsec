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

def insert_corrupt_and_correct_logic(gates, key_size):
    """Inserts Corrupt-and-Correct logic by adding controlled XOR corruption."""
    key_inputs = [f"keyinput{i}" for i in range(key_size)]
    
    # Corruption logic: XOR incorrect key inputs with circuit outputs
    corrupted_output = f"Corrupt_XOR = XOR({', '.join(key_inputs[:key_size//2])}, {gates[-1].split('=')[0].strip()})"
    correction_logic = f"Correct_AND = AND(NAND({', '.join(key_inputs[key_size//2:])}), Corrupt_XOR)"
    
    gates.append(corrupted_output)
    gates.append(correction_logic)
    gates[-1] = f"{gates[-1].split('=')[0].strip()} = Correct_AND"
    return gates, key_inputs

def write_locked_bench(file_path, inputs, outputs, gates, key_inputs):
    """Writes the modified benchmark file with Corrupt-and-Correct logic."""
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
    locked_gates, key_inputs = insert_corrupt_and_correct_logic(gates, args.keysize)
    
    locked_file = args.bench_path.replace(".bench", f"_CorruptCorrect_k_{args.keysize}.bench")
    write_locked_bench(locked_file, inputs, outputs, locked_gates, key_inputs)
    
    print(f"Corrupt-and-Correct applied! Locked circuit saved as {locked_file}")

if __name__ == "__main__":
    main()
