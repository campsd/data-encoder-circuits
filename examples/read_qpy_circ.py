#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

from qiskit import qpy

inpF='out/qcrank_nqa2_nqd2.qpy'

with open(inpF, 'rb') as fd:
    qcL = qpy.load(fd)

print('Loaded %d circuits from %s'%(len(qcL),inpF))
for i,qc in enumerate(qcL):
    n2q=qc.num_nonlocal_gates()
    depth=qc.depth(filter_function=lambda x: x.operation.num_qubits == 2 )
    print('\nCircuit %d:  2q-gates=%d  depth=%d'%(i,n2q,depth))
    print(qc.draw('text', idle_wires=False))
    
