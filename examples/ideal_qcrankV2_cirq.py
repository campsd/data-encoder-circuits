#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' Example script that runs QCRANK on the simulator using Cirq.
Paper:
Quantum-parallel vectorized data encodings and computations on trapped-ion and transmon QPUs
https://www.nature.com/articles/s41598-024-53720-x

V2 QCrank generator, uses mnemonic procedure to generate circuit, can do CX or CZ entangling basis 

Encodes lists of real numbers on na+nd qubits, where
na : number of address qubits
nd: number of data qubits
list length is nd*2^na

Uses Cirq's ideal simulator
'''
import sys, os
sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2_cirq import ParametricQCrankV2_cirq as QCrankV2_cirq, analyze_qcrank_residuals

import numpy as np
import cirq
import sympy
from time import time
import argparse

#...!...!..................
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase debug verbosity", default=1)
    parser.add_argument('-q','--numQubits', default=[2,2], type=int, nargs='+', 
                       help='pair: nq_addr nq_data, space separated')
    parser.add_argument('-i','--numImages', default=10, type=int, 
                       help='num of images packed in to the job')
    parser.add_argument("--useCZ", action='store_true', default=False, 
                       help="change from CX to CZ entanglement")
    parser.add_argument('-n','--numShots', default=8000, type=int, help='num of shots')
    parser.add_argument("-E","--execCircuit", action='store_true', default=False, 
                       help="execute circuit and decode output")
    
    args = parser.parse_args()

    for arg in vars(args):
        print('myArgs:', arg, getattr(args, arg))

    assert len(args.numQubits)==2

    return args


def run_cirq_circuits(circuits, num_shots):
    """Run multiple Cirq circuits and return counts."""
    simulator = cirq.Simulator()
    counts_list = []
    
    for circuit in circuits:
        # Run the circuit
        result = simulator.run(circuit, repetitions=num_shots)
        
        # Convert to counts dictionary
        # Assuming measurement key is 'c' to match original
        measurements = result.measurements['c']
        
        # Convert measurements to counts
        counts = {}
        for measurement in measurements:
            # Convert measurement array to bitstring
            bitstring = ''.join(str(bit) for bit in measurement)
            counts[bitstring] = counts.get(bitstring, 0) + 1
        
        counts_list.append(counts)
    
    return counts_list


def count_cx_gates(circuit):
    """Count CX gates in a Cirq circuit."""
    cx_count = 0
    for moment in circuit:
        for op in moment:
            if isinstance(op.gate, cirq.CXPowGate):
                cx_count += 1
    return cx_count


def print_circuit_info(circuit, nq_addr, nq_data, num_pix):
    """Print circuit information for Cirq circuit."""
    cx_depth = count_cx_gates(circuit)
    print(f'.... PARAMETRIZED CIRCUIT .............. num_pix={num_pix}, cx-depth={cx_depth}')
    
    nq_tot = len(circuit.all_qubits())
    print(f' Total qubits: {nq_tot}')
    
    # Count operations
    gate_counts = {}
    for moment in circuit:
        for op in moment:
            gate_name = type(op.gate).__name__
            gate_counts[gate_name] = gate_counts.get(gate_name, 0) + 1
    
    print(' gates count:', gate_counts)


#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__ == "__main__":
    args = get_parser()         
    np.set_printoptions(precision=3)

    # set up example parameters ---------------------------------------------------
    n_img = args.numImages             
    nq_addr, nq_data = args.numQubits  
    
    # Derived sizes ---------------------------------------------------------------
    num_addr = 2**nq_addr         # number of different addresses
    num_pix = nq_data * num_addr  # total number of pixels
    # ------------------------------------------------------------------------------

    # generate float random data
    data_inp = np.random.uniform(-1, 1., size=(num_addr, nq_data, n_img))
    if args.verb > 2:
        print('input data=', data_inp.shape, repr(data_inp))

    # set up experiments - using Cirq version
    qcrankObj = QCrankV2_cirq(nq_addr, nq_data, useCZ=args.useCZ, measure=True, barrier=True)
    
    qc = qcrankObj.circuit
    print_circuit_info(qc, nq_addr, nq_data, num_pix)

    if args.verb > 2 or nq_addr < 5:
        print('\nParametrized Circuit:')
        print(qc)
   
    # bind the data
    qcrankObj.bind_data(data_inp) 
    
    # generate the instantiated circuits
    qc_list = qcrankObj.instantiate_circuits()
    
    if args.verb > 2 or nq_addr < 5:
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {n_img}')
        print(qc_list[0])

    if not args.execCircuit:
        print('NO evaluation of job output, use -E to execute circuit')
        exit(0)
        
    # run the simulation for all images
    nq_tot = len(qc.all_qubits())
    print('M: job nqTot=%d started ...' % nq_tot)

    T0 = time()
    
    # Run all circuits with Cirq simulator
    counts_list = run_cirq_circuits(qc_list, args.numShots)
    
    ela_t = time() - T0
    print('M: QCrank simu nqTot=%d  shots=%d  nImg=%d  ended elaT=%.1f sec' % 
          (nq_tot, args.numShots, n_img, ela_t))

    # decode results - this should work correctly as per assumption
    data_rec, data_rec_err = qcrankObj.reco_from_yields(counts_list)
   
    if args.verb >= 3:
        for i in range(n_img):
            print(f'\n.... ORIGINAL DATA .............. img={i}')            
            print(f'org img={i}\n', data_inp[..., i].T)            
            print(f'reco img={i}\n', data_rec[..., i].T)
            print(f'diff img={i}\n', (data_inp[..., i] - data_rec[..., i]).T)
            print('stat err img=%d   %d shots/addr\n' % (i, args.numShots/num_addr), 
                  (data_inp[..., i] - data_rec[..., i]).T)
            if i > 2: 
                break

    shpad = args.numShots / num_addr
    print('post processing  shots=%d  nAddr=%d   shots/addr=%.d  relErr=%.3f' % 
          (args.numShots, num_addr, shpad, 1/np.sqrt(shpad)))

    analyze_qcrank_residuals(data_inp, data_rec)
