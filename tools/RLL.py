import argparse
import subprocess
import os
from utils import parse_bench_file, defining_keyinputs, insert_key_gates, write_list_to_file

def run_command(original_circuit, encrypted_circuit, key):
    # command = f"./lcmp {original_circuit} {encrypted_circuit} key={key}"
    command = f"{os.path.dirname(__file__)}/lcmp {original_circuit} {encrypted_circuit} key={key}"

    try:
        subprocess.run(command, shell=True, check=True)
        print(f"Command executed successfully: {command}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {command}\n{e}")

def run(bench_path: str, key: list, save_path: str):
    inputs, outputs, gates, existing_key_inputs = parse_bench_file(bench_path)
    start_num = len(existing_key_inputs)  # Start numbering new keyinputs after existing ones

    new_keyinput_list = defining_keyinputs(key, existing_key_inputs)
    new_keyinput_labels = [ki.split("(")[1].split(")")[0] for ki in new_keyinput_list]
    inputs.extend(new_keyinput_labels)

    insert_key_gates(key, gates, start_num)

    all_gates = [f"INPUT({i})" for i in inputs] + [f"OUTPUT({o})" for o in outputs] + gates
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    write_list_to_file(all_gates, save_path, key)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=str, required=True)
    parser.add_argument("--key", type=str, required=True)
    parser.add_argument("--save_path", type=str, required=True)
    parser.add_argument("--iter", type=int, default=1, help="Number of iterations to run the locking process")
    args = parser.parse_args()
    return args.bench_path, [int(k) for k in args.key], args.save_path, args.iter

def main():
    bench_path, key, save_path_base, iterations = parse_args()

    base_name, extension = save_path_base.rsplit(".", 1)
    key_str = ''.join(str(k) for k in key)

    # for i in range(iterations):
    #     save_path = f"{base_name}_{i}.{extension}"
    for i in range(iterations):
        if iterations == 1:
            save_path = f"{base_name}.{extension}"
        else:
            save_path = f"{base_name}_{i}.{extension}"

        run(bench_path, key, save_path)
        # Run the command after each benchmark file is written
        run_command(bench_path, save_path, key_str)

if __name__ == "__main__":
    main()
