#!/usr/bin/env python3

import argparse
import os
import sys
import random
from pathlib import Path

# Ensure the tools directory is on the import path
# sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
# from tools.utils.utils import (
#     parse_bench_file,
#     defining_keyinputs,
#     insert_key_gates,
#     write_list_to_file,
# )

import os
import argparse
import random

def parseBench(inputFile):
    inputs, outputs, logicGates = [], [], []
    with open(inputFile, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("INPUT"):
                inputs.append(line.split("(")[1].split(")")[0])
            elif line.startswith("OUTPUT"):
                outputs.append(line.split("(")[1].split(")")[0])
            else:
                logicGates.append(line)
    return inputs, outputs, logicGates

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bench_path", type=str, required=True, help="Path of file to be locked")
    parser.add_argument("--keysize", type=int, required=True, help="Size of the key")
    args = parser.parse_args()
    return args.bench_path, args.keysize

def sarLock(inputFile, keysize):
    inputs, outputs, logicGates = parseBench(inputFile)
    outputFile = f"{os.path.splitext(inputFile)[0]}_sarLock_k_{keysize}.bench"

    keyInputs = []

    for i in range(keysize):
        keyInputs.append(f"keyinput{i}")

        
    with open(outputFile, 'w') as f:
        for inp in inputs:
            f.write(f"INPUT({inp})\n")
        for key in keyInputs:
            f.write(f"INPUT({key})\n")
        for out in outputs:
            f.write(f"OUTPUT({out})\n")

        andInp = []
        andPInp = []
        for i in range(keysize):
            xnorOut = f"in{i}_xor0"
            logicGates.append(f"{xnorOut} = XNOR({inputs[i%len(inputs)]}, {keyInputs[i]})")
            andInp.append(xnorOut)

        logic0 = f"logic0"
        logicGates.append(f"{logic0} = XNOR({inputs[i]}, {inputs[i]})")

        logic1 = f"logic1"
        logicGates.append(f"{logic1} = XOR({inputs[i]}, {inputs[i]})")

        for i in range(keysize):
            xnorOut2 = f"in{i}_xor2"
            logicGates.append(f"{xnorOut2} = XNOR({keyInputs[i]}, {random.choice([logic0, logic1])})")
            andPInp.append(xnorOut2)

        
        interInputs = [f"inter{i}_0" for i in range(keysize)]
        interAnd = []
        interCounter = 0
        for i in range(0, keysize, 2):
            interOut = f"inter{interCounter}_0"
            interAnd.append(interOut)
            logicGates.append(f"{interOut} = AND({andInp[i]}, {andInp[i+1]})")
            interCounter += 1

        tree = 1
        while len(interAnd) > 2:
            interAnd2 = []
            for i in range(0, len(interAnd), 2):
                inter2Out = f"inter{interCounter}_0"
                interAnd2.append(inter2Out)
                logicGates.append(f"{inter2Out} = AND({interAnd[i]}, {interAnd[i+1]})")
                interCounter += 1
            interAnd = interAnd2
            tree += 1

        DTL0 = f"DTL_0"
        logicGates.append(f"{DTL0} = AND({interAnd[0]}, {interAnd[1]})")


        interInputs = [f"inter{i}_2" for i in range(keysize)]
        interAnd = []
        interCounter = 0
        for i in range(0, keysize, 2):
            interOut = f"inter{interCounter}_2"
            interAnd.append(interOut)
            logicGates.append(f"{interOut} = AND({andPInp[i]}, {andPInp[i+1]})")
            interCounter += 1

        tree = 1
        while len(interAnd) > 2:
            interAnd2 = []
            for i in range(0, len(interAnd), 2):
                inter2Out = f"inter{interCounter}_2"
                interAnd2.append(inter2Out)
                logicGates.append(f"{inter2Out} = AND({interAnd[i]}, {interAnd[i+1]})")
                interCounter += 1
            interAnd = interAnd2
            tree += 1

        DTL2 = f"DTL_2"
        logicGates.append(f"{DTL2} = AND({interAnd[0]}, {interAnd[1]})")

        flip = f"FLIP"
        logicGates.append(f"{flip} = AND({DTL0}, {DTL2})")

        modifiedGates = []
        encGate = outputs[0]

        for gate in logicGates:
            if gate.startswith(encGate + " "):
                modifiedGate = gate.replace(encGate, encGate + "_enc", )
                modifiedGates.append(modifiedGate)
            else:
                modifiedGates.append(gate)
        
        finalOutput = f"{encGate} = XOR({flip}, {encGate}_enc)"   
        
        modifiedGates.append(finalOutput)


        for gate in modifiedGates:
            f.write(f"{gate}\n")


    print(f"LOCKED FILE SAVED as {outputFile}")

def main():
    bench_path, keysize= parseArgs()
    inputs, outputs, logicGates = parseBench(bench_path)
    sarLock(bench_path, keysize)
    
if __name__ == "__main__":
    main()
