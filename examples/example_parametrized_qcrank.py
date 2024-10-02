#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''Example script that runs QCRANK on the simulator.'''
import sys,os
#sys.path.append('../')  # I left the Python path hack here for now
#from qpixl import qcrank
sys.path.append(os.path.abspath("/daan_qcrank1"))
from datacircuits import qcrank

import numpy as np
from qiskit_aer import AerSimulator

#from qiskit import Aer
#from qiskit.test.mock import FakeLima

# set up example parameters ---------------------------------------------------
n_img = 1               # how many images to process, was 1
nq_addr = 3             # number of address qubits, was 3
nq_data = 6             # number of data qubits (colors), was 6
max_val = 16            # maximum data value
shots = 20_000           # number of shots to sample
keep_last_cx = True     # keep the last cnot or remove
qcrank_opt= True     # T: optimal,  F: not optimal w/ cx-gates being parallele
# ------------------------------------------------------------------------------
# Derived sizes ---------------------------------------------------------------
n_addr = 2**nq_addr         # number of different addresses
n_pix = nq_data * n_addr    # total number of pixels
# ------------------------------------------------------------------------------

# generate float random data
data = np.random.uniform(0, max_val, size=(n_addr, nq_data, n_img))
#data=np.array([[[14.52918225],   [ 8.83357284],   [15.07504015]], [[ 7.7425525 ],  [15.59798243], [15.00905395]], [[ 0.26442301], [ 6.45192356], [11.98487793]], [[11.23864993], [ 4.66508508], [ 8.17337769]]]); assert  n_img ==1; assert nq_addr == 2; assert nq_data == 3 ; assert  max_val == 16   # fixed hardcoded random input
#data=np.array([[[10.06209084]], [[14.74914244]], [[ 7.30859133]], [[ 3.97936363]]]); assert  n_img ==1; assert nq_addr == 2; assert nq_data == 1 ; assert  max_val == 16   # fixed hardcoded random input
print('input data=',data.shape,repr(data))


backend = AerSimulator()

# set up experiments
param_qcrank = qcrank.ParametrizedQCRANK(
    nq_addr,
    nq_data,
    qcrank.QKAtan2DecoderQCRANK,
    keep_last_cx=keep_last_cx,
    measure=True,
    statevec=False,
    reverse_bits=True,   # to match Qiskit littleEndian
    parallel= qcrank_opt
)
qc=param_qcrank.circuit
cxDepth=qc.depth(filter_function=lambda x: x.operation.name == 'cx')
print(f'.... PARAMETRIZED CIRCUIT .............. n_pix={n_pix},  qcrank_opt={qcrank_opt}, cx-depth={cxDepth}')
print(' gates count:', qc.count_ops())

print(param_qcrank.circuit.draw())


# bind the data
param_qcrank.bind_data(data, max_val=max_val)
# generate the instantiated circuits
data_circs = param_qcrank.instantiate_circuits()
print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {n_img}')
print(data_circs[0].draw())

# run the simulation for all images
results = [backend.run(c, shots=shots).result() for c in data_circs]
counts = [r.get_counts(c) for r, c in zip(results, data_circs)]

# decode results
angles_rec =  param_qcrank.decoder.angles_from_yields(counts)  

print('\nM: minAngle=%.3f, maxAngle=%.3f  should be in range [0,pi]\n'%(np.min(angles_rec),np.max(angles_rec)))

data_rec = param_qcrank.decoder.angles_to_fdata(angles_rec, max_val=max_val)

print(f'.... ORIGINAL DATA .............. n_img={n_img}')
for i in range(n_img):
    print(f'org img={i}\n', data[..., i])
print(f'.... RECONSTRUCTED DATA ..........  n_img={n_img}')
for i in range(n_img):
    print(f'reco img={i}\n', data_rec[..., i])
    #print(f'reco img={i}\n', angles_rec[..., i]/np.pi*max_val)
print('.... DIFFERENCE ..............')
for i in range(n_img):
    print(f'diff img={i}\n', data[..., i] - data_rec[..., i])
    
print('....L2 distance = sqrt( sum (res^2)), shots=%d  ndf=%d '%(shots,n_addr))
for i in range(n_img):
    print('img=%d L2=%.2g'%(i, np.linalg.norm(data[..., i] - data_rec[..., i])))
