#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"
'''
 generate random large circuit and run it using density matrix simulator which is very slow

'''


from time import time
from pytket import Circuit, OpType
import random


import argparse
def commandline_parser():  # used when runing from command line
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verbosity",type=int, help="increase output verbosity", default=1, dest='verb')

    parser.add_argument('-q','--num_qubit',type=int,default=3, help="qubit count")
    #parser.add_argument('-n','--num_shot',type=int,default=2000, help="shots")
    parser.add_argument( "-R","--addReverse",  action='store_true', default=False, help="add inverted unitary so circuit returns 0^nq state only")
    
    args = parser.parse_args()
    for arg in vars(args):  print( 'myArg:',arg, getattr(args, arg))
    return args

#...!...!....................
def generate_random_circuit(nq=5, addRev=False, depth=3):
    """
    Generates a random quantum circuit on nq qubits.
    
    Parameters:
        nq (int): Number of qubits.
        addRevers (bool): 
            - If False, returns a random circuit with measurements.
            - If True, returns a circuit composed of a random circuit (without measurement),
              its inverse, and then adds measurements on all qubits.
        depth (int): Depth of the random circuit.
        
    Returns:
        QuantumCircuit: The generated quantum circuit.
    """

    circ = Circuit(nq)
    
    single_qubit_gates = [OpType.Rx, OpType.Ry, OpType.Rz, OpType.H]
    two_qubit_gates = [OpType.CX, OpType.CZ]
    
    for _ in range(depth):
        # Add random single-qubit gate
        q = random.randint(0, nq-1)
        gate = random.choice(single_qubit_gates)
        if gate in [OpType.Rx, OpType.Ry, OpType.Rz]:
            angle = random.uniform(0, 2*3.14159)
            circ.add_gate(gate, [angle], [q])
        else:
            circ.add_gate(gate, [q])
        
        # Add random two-qubit gate
        if random.random() < 0.5:
            q1, q2 = random.sample(range(nq), 2)
            gate = random.choice(two_qubit_gates)
            circ.add_gate(gate, [q1, q2])


    if addRev:
        invCirc = circ.dagger()
        circ.add_barrier(range(nq))
        circ.append(invCirc)
        
    circ.measure_all()
    return circ



#=================================
#  M A I N
#=================================
if __name__ == "__main__":
    args=commandline_parser()
   

    nq=args.num_qubit
    qc=generate_random_circuit(nq,args.addReverse)
    if nq<4:
        print('circ commands:\n',qc.get_commands())
        print(qc)

    aaa
    print('job started,  nq=%d  at %s ...'%(qc.num_qubits,backend.name))
    options = SamplerOptions()
    options.default_shots=10000

    qcEL=(qc,)  # quant circ executable list
    sampler = Sampler(mode=backend, options=options)
    T0=time()
    job = sampler.run(qcEL)
    result=job.result()
    elaT=time()-T0
    counts=result[0].data.meas.get_counts()
    print('counts:',counts)
    print('run time %.1f sec'%(elaT))
