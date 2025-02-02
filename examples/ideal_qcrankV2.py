#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' Example script that runs QCRANK on the simulator.
Paper:
Quantum-parallel vectorized data encodings and computations on trapped-ion and transmon QPUs
https://www.nature.com/articles/s41598-024-53720-x

V2 QCrank generator, uses mnemonic procedure to generate circuit, can do CZ or CZ entangling basis 

Encodes  lists of real numbers on na+nd qubits, where
na : number of address qubits
nd: number of data qubits
list length  is nd*2^na

Ideal simulator  uses Aer
Uses sampler

Dependency : https://github.com/campsd/data-encoder-circuits

'''
import sys,os
sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits.ParametricQCrankV2 import ParametricQCrankV2 as QCrankV2

import numpy as np
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
from qiskit_ibm_runtime.options.sampler_options import SamplerOptions

from time import time

import argparse
#...!...!..................
def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v","--verb",type=int, help="increase debug verbosity", default=1)

    parser.add_argument('-q','--numQubits', default=[2,2], type=int,  nargs='+', help='pair: nq_addr nq_data, space separated ')

    parser.add_argument('-i','--numImages', default=2, type=int, help='num of images packed in to the job')

    parser.add_argument("--useCZ", action='store_true', default=False, help="change from CX to CZ entangelemnt")
    # Qiskit:
    parser.add_argument('-n','--numShots', default=8000, type=int, help='num of shots')
    parser.add_argument( "-E","--execDecoding", action='store_true', default=False, help="do not decode job output")
    parser.add_argument( "-e1","--exportQPY", action='store_true', default=False, help="exprort parametrized circuit as QPY file")
    parser.add_argument( "-e2","--exportQASM", action='store_true', default=False, help="exprort parametrized circuit as QASM file")
 

 
  
    args = parser.parse_args()

    for arg in vars(args):
        print( 'myArgs:',arg, getattr(args, arg))

    assert len(args.numQubits)==2

    return args

#=================================
#=================================
#  M A I N 
#=================================
#=================================
if __name__ == "__main__":
    args=get_parser() 
    
    # set up example parameters ---------------------------------------------------
    n_img = args.numImages             
    nq_addr, nq_data = args.numQubits  
    # Derived sizes ---------------------------------------------------------------
    num_addr = 2**nq_addr         # number of different addresses
    num_pix = nq_data * num_addr    # total number of pixels
    # ------------------------------------------------------------------------------

    # generate float random data
    data_inp = np.random.uniform(-1, 1., size=(num_addr, nq_data, n_img))
    if args.verb>2:
        print('input data=',data_inp.shape,repr(data_inp))
        
    backend = AerSimulator()

    # set up experiments
    qcrankObj = QCrankV2( nq_addr, nq_data, useCZ=args.useCZ,measure=True )
    
    qc=qcrankObj.circuit
    cxDepth=qc.depth(filter_function=lambda x: x.operation.name == 'cx')
    print(f'.... PARAMETRIZED CIRCUIT .............. num_pix={num_pix}, cx-depth={cxDepth}')
    nqTot=qc.num_qubits
    print(' gates count:', qc.count_ops())

    if args.verb>2 or nq_addr<4:
        print(qcrankObj.circuit.draw())
   
    if args.exportQPY:
        from qiskit import qpy
        circF='./qcrank_nqa%d_nqd%d.qpy'%(nq_addr,nq_data)
        with open(circF, 'wb') as fd:
            qpy.dump(qc, fd)
        print('\nSaved circ1:',circF)
        exit(0)
        
    if args.exportQASM:
        import qiskit.qasm3
        circF='./qcrank_nqa%d_nqd%d.qasm'%(nq_addr,nq_data)
        with open(circF, 'w') as fd:
            qiskit.qasm3.dump(qc, fd)
        print('\nSaved circ1:',circF)
        exit(0)
        
    # bind the data
    qcrankObj.bind_data(data_inp) 
    
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    
    if args.verb>2 or nq_addr<5:
        print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {n_img}')
        print(qcEL[0].draw())

    options = SamplerOptions()
    options.default_shots=args.numShots 

    sampler = Sampler(mode=backend, options=options)
    if not args.execDecoding:
        print('NO evaluation of job output, use -E to execute decoding')
        exit(0)
        
    # run the simulation for all images
    print('M: job nqTot=%d started ...'%nqTot)

    T0=time()
    job = sampler.run(tuple(qcEL))
    jobRes=job.result()
    
    print('num Circ:%d'%n_img )
    countsL=[jobRes[i].data.meas.get_counts()  for i in range(n_img)]
    elaT=time()-T0
    print('M: QCrank simu nqTot=%d  shots=%d  nImg=%d  ended elaT=%.1f sec'%(nqTot,args.numShots ,n_img,elaT))

    #print('M:counts',countsL)
    # decode results
    data_rec =  qcrankObj.reco_from_yields(countsL)
    #print('inp data;',data_inp.T)
    #print('rec data;',data_rec.T)
   
    if args.verb>=3:
        print(f'.... ORIGINAL DATA .............. n_img={n_img}')
        for i in range(n_img):
            print(f'org img={i}\n', data_inp[..., i])
        print(f'.... RECONSTRUCTED DATA ..........  n_img={n_img}')
        for i in range(n_img):
            print(f'reco img={i}\n', data_rec[..., i])
        print('.... DIFFERENCE ..............')
        for i in range(n_img):
            print(f'diff img={i}\n', data_inp[..., i] - data_rec[..., i])

    print('....L2 distance = sqrt( sum (res^2)), shots=%d  ndf=%d '%(args.numShots ,num_addr))
    for i in range(n_img):
        print('img=%d L2=%.2g'%(i, np.linalg.norm(data_inp[..., i] - data_rec[..., i])))
