#!/usr/bin/env python3
# -*- coding: utf-8 -*-
''' Example script that runs QCRANK on the simulator.
Paper:
Quantum-parallel vectorized data encodings and computations on trapped-ion and transmon QPUs
https://www.nature.com/articles/s41598-024-53720-x

Encodes  lists of real numbers on na+nd qubits, where
na : number of address qubits
nd: number of data qubits
list length  is nd*2^na

Ideal simulator  uses Aer
Uses sampler

Dependency : https://github.com/campsd/data-encoder-circuits
mounted as /qcrank_light

'''
import sys,os

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits import qcrank
from datacircuits.ParametricQCrankV2 import  analyze_qcrank_residuals

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

    parser.add_argument('-i','--numImages', default=5, type=int, help='num of images packed in to the job')

    # Qiskit:
    parser.add_argument('-n','--numShots', default=800, type=int, help='num of shots')
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
    n_img = args.numImages               # how many images to process, was 1
    nq_addr, nq_data = args.numQubits  
    max_val = np.pi            # maximum data value
    keep_last_cx = True     # keep the last cnot or remove
    qcrank_opt= True     # T: optimal,  F: not optimal w/ cx-gates being parallele
    # ------------------------------------------------------------------------------
    # Derived sizes ---------------------------------------------------------------
    n_addr = 2**nq_addr         # number of different addresses
    n_pix = nq_data * n_addr    # total number of pixels
    # ------------------------------------------------------------------------------

    # generate float random data
    data_inp = np.random.uniform(0, max_val, size=(n_addr, nq_data, n_img))
    if args.verb>2:
        print('input data=',data_inp.shape,repr(data_inp))
        
    backend = AerSimulator()

    # set up experiments
    qcrankObj = qcrank.ParametrizedQCRANK(
        nq_addr,
        nq_data,
        qcrank.QKAtan2DecoderQCRANK,
        keep_last_cx=keep_last_cx,
        measure=True,
        statevec=False,
        reverse_bits=True,   # to match Qiskit littleEndian
        parallel= qcrank_opt
    )
    qc=qcrankObj.circuit
    cxDepth=qc.depth(filter_function=lambda x: x.operation.name == 'cx')
    print(f'.... PARAMETRIZED CIRCUIT .............. n_pix={n_pix},  qcrank_opt={qcrank_opt}, cx-depth={cxDepth}')
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
    qcrankObj.bind_data(data_inp, max_val=max_val)
    # generate the instantiated circuits
    qcEL = qcrankObj.instantiate_circuits()
    
    if args.verb>2 or nq_addr<4:
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
    counts=[jobRes[i].data.meas.get_counts()  for i in range(n_img)]
    elaT=time()-T0
    print('M: QCrank simu nqTot=%d  shots=%d  nImg=%d  ended elaT=%.1f sec'%(nqTot,args.numShots ,n_img,elaT))


    # decode results
    angles_rec =  qcrankObj.decoder.angles_from_yields(counts)  

    print('\nM: minAngle=%.3f, maxAngle=%.3f  should be in range [0,pi]\n'%(np.min(angles_rec),np.max(angles_rec)))

    data_rec = qcrankObj.decoder.angles_to_fdata(angles_rec, max_val=max_val)

    if args.verb>3:
         for i in range(n_img):
            print(f'\n.... ORIGINAL DATA .............. img={i}')            
            print(f'org img={i}\n', data_inp[..., i].T)            
            print(f'reco img={i}\n', data_rec[..., i].T)
            print(f'diff img={i}\n', (data_inp[..., i] - data_rec[..., i]).T)
            print('stat err img=%d   %d shots/addr\n'%(i,args.numShots/num_addr), (data_inp[..., i] - data_rec[..., i]).T)
            if i>2: break
            
    print('....L2 distance = sqrt( sum (res^2)), shots=%d  ndf=%d '%(args.numShots ,n_addr))
    analyze_qcrank_residuals(data_inp, data_rec)
