#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''Example script that runs QBART on the simulator.'''
import sys
sys.path.append('../')  # I left the Python path hack here for now
from qpixl import qbart
import numpy as np
from qiskit import Aer
from qiskit.test.mock import FakeLima
from pprint import pprint
from bitstring import BitArray

# set up example parameters ---------------------------------------------------
n_img = 1               # how many images to process
nq_addr = 2             # number of address qubits
nq_data = 5             # number of data qubits (colors)
shots = 400           # number of shots to sample
fake_lima =  False        # T:run on noisy 5q lima simu. or F:noisefree simulator
# ------------------------------------------------------------------------------
# Derived sizes ---------------------------------------------------------------
n_addr = 2**nq_addr           # number of different addresses
max_val = 1<< nq_data          # maximum data value
# ------------------------------------------------------------------------------

# generate random data
data = np.random.randint(0, max_val, size=(n_img,n_addr),dtype=np.int16)  # QBART expects image index 1st
#data=np.array( [[17,  2, 21, 31]])

if fake_lima:
    backend = FakeLima()
    assert nq_addr+nq_data <= 5
else:
    backend = Aer.get_backend('aer_simulator')

# set up experiments
param_qbart = qbart. ParametrizedQBART( nq_addr, nq_data,  measure=True, statevec=False )
print(f'.... PARAMETRIZED CIRCUIT .............. nq_data={nq_data}')
print(param_qbart.circuit.draw(cregbundle=True))


if fake_lima:
    param_qcrank.transpile(backend=backend, optimization_level=3)
    print(f'.... TRANSPILED PARAMETRIZED CIRCUIT ..............')
    print(param_qbart.circuit.draw())

# bind the data
param_qbart.bind_data(data)
# generate the instantiated circuits
data_circs = param_qbart.instantiate_circuits()

im=0 # select image to be printed out
print(f'.... FIRST INSTANTIATED CIRCUIT .............. of {n_img}')
print('input data:', data[im])
print(data_circs[im].draw(cregbundle=True))

# run the simulation for all images
results = [backend.run(c, shots=shots).result() for c in data_circs]
counts = [r.get_counts(c) for r, c in zip(results, data_circs)]

num_res=len(counts[im])
print('measured %d counts'%num_res); pprint(counts[im])
print('input data:', data[im])
assert num_res==n_addr

print('\nunpack recovered results')
#... w/o majority voting so it is not correct for a noisy simulator
for bs in counts[im]:
    mshots=counts[im][bs]
    A=BitArray(bin=bs)        
    iaddr=A[:nq_addr].uint
    ival=A[nq_addr:].uint
    print(bs,mshots,'iaddr:',iaddr, 'rec_val:',ival, 'is correct=%r'%(ival==data[im][iaddr]))
    

print('M:done')
