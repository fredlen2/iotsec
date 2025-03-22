import os
import json

DATA_FOLDER = "data"

circuits = []
for filename in os.listdir(DATA_FOLDER):
    if filename.endswith(".bench"):
        name = filename.split(".")[0]
        key_sizes = [16, 32] if name.startswith("c") else [128, 256]
        circuits.append({"name": name, "file": filename, "key_sizes": key_sizes})

config = {"circuits": circuits, "iterations": 10}

with open("config/circuits.json", "w") as f:
    json.dump(config, f, indent=4)

print("Configuration file 'config/circuits.json' has been generated!")
