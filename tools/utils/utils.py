import random


def parse_bench_file(file_path):
    inputs, outputs, gates = [], [], []
    existing_key_inputs = []  # To store existing key inputs

    with open(file_path, "r") as file:
        for line in file:
            line = line.strip()

            if line.startswith("INPUT"):
                input_name = line.split("(")[1].split(")")[0]
                inputs.append(input_name)
                if "keyinput" in input_name:
                    existing_key_inputs.append(input_name)
            elif line.startswith("OUTPUT"):
                outputs.append(line.split("(")[1].split(")")[0])
            elif "=" in line:
                gates.append(line)

    return inputs, outputs, gates, existing_key_inputs


def defining_keyinputs(key, inputs):
    existing_key_nums = [
        int(input.replace("keyinput", "")) for input in inputs if "keyinput" in input
    ]
    start_num = max(existing_key_nums) + 1 if existing_key_nums else 0

    keyinput_list = [f"INPUT(keyinput{start_num + i})" for i in range(len(key))]
    return keyinput_list


def insert_key_gates(key, gates, start_num):
    unlocked_gates = [item for item in gates if "lock" not in item]

    if len(unlocked_gates) < len(key):
        raise ValueError("Not enough unlocked gates to insert keys.")

    random_gates = random.sample(unlocked_gates, len(key))

    for i, gate in enumerate(random_gates):
        key_input_index = start_num + i  # Correct keyinput index for new keyinputs
        gate_parts = gate.split(" = ")
        gate_name = gate_parts[0].strip()  # Ensure no trailing spaces on gate name
        gate_expr = gate_parts[1]

        # Modify the original gate to include "_lock" without introducing spaces
        modified_gate_name = f"{gate_name}_lock"
        modified_gate = f"{modified_gate_name} = {gate_expr}"
        gates[gates.index(gate)] = modified_gate

        # Depending on the key bit, decide to use XNOR or XOR
        new_gate_operation = "XNOR" if key[i] == 1 else "XOR"
        # Insert the new gate using the chosen operation with the keyinput and modified gate name
        new_gate = f"{gate_name} = {new_gate_operation}(keyinput{key_input_index}, {modified_gate_name})"
        gates.insert(gates.index(modified_gate) + 1, new_gate)

    return gates


def write_list_to_file(lst, file_path, key):
    # Convert the key list back to a string representation
    key_str = "".join(str(bit) for bit in key)
    key_comment = f"#key={key_str}\n"
    with open(file_path, "w") as file:
        # Write the key comment as the first line
        file.write(key_comment)

        # Then write the rest of the content
        max_length_before_equal = max(
            (item.find("=") for item in lst if "=" in item), default=0
        )
        lines = [
            (
                f"{item.split('=')[0].ljust(max_length_before_equal)}= {item.split('=')[1]}\n"
                if "=" in item
                else f"{item}\n"
            )
            for item in lst
        ]
        file.writelines(lines)

    # max_length_before_equal = max((item.find('=') for item in lst if '=' in item), default=0)
    # with open(file_path, "w") as file:
    #     lines = [
    #         f"{item.split('=')[0].ljust(max_length_before_equal)}= {item.split('=')[1]}\n" if '=' in item else f"{item}\n"
    #         for item in lst]
    #     file.writelines(lines)
