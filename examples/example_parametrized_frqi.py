#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Example script that runs randomly generated 8 pixel images on the simulator.
'''
from datacircuits import frqi

import numpy as np
from qiskit_aer import AerSimulator


# set up example parameter ----------------------------------------------------
n_test = 10
nq_addr = 3
n_pix = 2**nq_addr
max_val = 16
shots = 50_000
keep_last_cx = False
# ------------------------------------------------------------------------------

# generate target data
data = np.random.randint(0, max_val, size=(n_pix, n_test))

# initialize the simulator
simulator = AerSimulator()

# set up experiments
param_frqi = frqi.ParametrizedFRQI(nq_addr)
print('.... PARAMETRIZED CIRCUIT ..............')
print(param_frqi.circuit.draw())

data_frqi = param_frqi(data, max_val=max_val)
data_frqi = data_frqi.configure_output(
    keep_last_cx=keep_last_cx,
    measure=True,
    statevec=False,
    reverse_bits=True
)
data_circs = data_frqi.generate_circuits()
print('.... FIRST INSTANTIATED CIRCUIT ..............')
print(data_circs[0].draw())

# run the simulation
results = [simulator.run(c, shots=shots).result() for c in data_circs]
counts = [r.get_counts(c) for r, c in zip(results, data_circs)]

# decode results
decoder = frqi.QKAtan2DecoderFRQI(data_frqi)
angles_rec = decoder.angles_from_yields(counts)
data_rec = decoder.angles_to_data(angles_rec, max_val=max_val)

print('.... ORIGINAL DATA ..............')
print(data)
print('.... RECONSTRUCTED DATA ..............')
print(data_rec)
print('.... DIFFERENCE ..............')
print(data - data_rec)
