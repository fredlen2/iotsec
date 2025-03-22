# Copyright for Random Logic Locking (RLL) Code

MIT License

Copyright (c) 2023 Saeid Rajabi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

For further inquiries, please contact srajabi@udel.edu.

## COMPATIBILITY

This code is tested on Ubuntu 20.04 LTS and Python 3.11.

## How to Run RLL code

To run Random Logic Locking (RLL) code, the user needs to invoke the terminal and go to the main directory where RLL.py exists.

python RLL.py --bench_path data/original_netlist.bench --key keyinput_string --save_path data/original_netlist_lock.bench --iter number_of_locked_designs[Default=1]

--bench_path --> Denotes the path of unprotected design is present.
--key --> Denotes the key with which the user wants to protect the unprotected design.
--save_path --> Denotes the path of protected design locked with the key.
--iter --> Denotes the number of trials user wants to run RLL code on the same input benchmark with different key gate locations and the same defined key.

**Note:**
**Make sure to define the key so that the number of 0s is equal to 1s.**

E.g. python RLL.py --bench_path data/c432.bench --key 00110011 --save_path data/c432_RLL_k8.bench --iter 2

Above code will create 2 benchmarks from c432.bench, locked with key equals 00110011 and save it in ./data/ directory and their names are c432_RLL_k8_0.bench and c432_RLL_k8_1.bench  

E.g. python RLL.py --bench_path data/b14_C.bench --key 0011001111001010 --save_path data/b14_C_RLL_k16.bench

Above code will create 1 benchmark from b14_C.bench, locked with key equals 0011001111001010 and save it in ./data/ directory and its name is b14_C_RLL_k16_0.bench.

**The locked benchmark has #key= ... in its first line.**

# How To CHECK everything works?

The following command will remove files that include "RLL" in their naming. If you are in the same directory of RLL.py, the listed below command will remove any generated files using the RLL method, and you can run the RLL code at your end.

find ./data/ -type f -name '*RLL*.bench' -exec rm {} +





**NOTE:**
The code is compatible with benchmarks that do NOT have any comments on the top of them.
Remove the comments from the original benchmarks if you want to run this RLL code on other benchmarks. (The benchmark should start with INPUT... from its first line)



If you face a permission error while running lcmp, run the command listed below and try it again.
chmod +x lcmp
