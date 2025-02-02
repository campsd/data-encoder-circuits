'''
This implementation of QCrank
- can choose CX or CZ entangling basis
- uses  EVEN  ( expectation value encoding) for input in range [-1,1]

'''

import sys,os

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.result.utils import marginal_distribution

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits import qcrank
    
#...!...!....................
def marginalize_qcrank_EV(  addrBitsL, probsB,dataBit):
    #print('MQCEV inp bits:',dataBit,addrBitsL)
    # ... marginal distributions for 2 data qubits, for 1 circuit
    assert dataBit not in addrBitsL
    bitL=[dataBit]+addrBitsL
    #print('MQCEV bitL:',bitL)
    probs=marginal_distribution(probsB,bitL)
    
    #.... comput probabilities for each address
    nq_addr=len(addrBitsL)
    seq_len=1<<nq_addr
    mdata=np.zeros(seq_len)
    fstr='0'+str(nq_addr)+'b' 
    for j in range(seq_len):
        mbit=format(j,fstr)
        mbit0=mbit+'0'; mbit1=mbit+'1'
        m1=probs[mbit1] if mbit1 in probs else 0
        m0=probs[mbit0] if mbit0 in probs else 0
        m01=m0+m1
        #print(j,mbit,'sum=',m01)
        p=m1/m01 if m01>0 else 0
        mdata[j]=p
    return 1-2*mdata
  

#...!...!....................
class ParametricQCrankV2():
#...!...!....................
    def __init__(self, nq_addr, nq_data,
                 measure: bool = True,
                 barrier: bool = True,
                 useCZ: bool =  False  # default uses CX gates
                 ):
        '''Initializes a parametrized QCRANK circuit with nq_addr address qubits and
        nq_data data qubits. The total number of qubits in the circuit is nq_addr + nq_data.

        Args:
            nq_addr: int
                Number of address qubits.
            nq_data: int
                Number of data qubits.
            measure: bool (True)
                If True, adds measurements to all qubits.
            barrier: bool (True)
                If True, inserts a barrier in the circuit.
        '''

        # Sanity check: ensure at least one address-data qubit pair exists
        assert nq_addr * nq_data >= 1

        self.nq_addr = nq_addr
        self.nq_data = nq_data
        self.num_addr = 2 ** nq_addr

        #...!...!....................
        # Generate circuit
        self.circuit = QuantumCircuit(nq_addr + nq_data)

        # Apply Hadamard gates (diffusion) to all address qubits
        for i in range(nq_addr):
            self.circuit.h(i)
        if barrier:
            self.circuit.barrier()

        # Create a parameter vector for each data qubit, each with 2**nq_addr parameters
        self.parV = [
            ParameterVector(f'p{i}', 2 ** nq_addr) for i in range(nq_data)
        ]

        # Add nested and shifted uniform rotations along with controlled-X (CX) gates
        for ja in range(self.num_addr):
            for jd in range(nq_data):
                pars=self.parV[jd][ja]
                qd=nq_addr + jd

                # there are 3 cases
                if useCZ:  # will use CZ entangling gates
                    if  ja==0:
                        self.circuit.ry(pars, qd)
                        self.circuit.h(qd)
                    else:
                        self.circuit.ry(-pars, qd)
                else:  # will use CX entangling gates
                    self.circuit.ry(pars, qd)

            for jd in range(nq_data):
                qctr = qcrank.compute_control(ja, self.nq_addr, shift=jd % self.nq_addr)
                qd=nq_addr + jd
                if useCZ:
                    self.circuit.cz(qctr, qd)
                    if  ja==self.num_addr-1:  self.circuit.h(qd)

                else:
                    self.circuit.cx(qctr, qd)

        # Reverse qubit order to match Qiskit's little-endian convention
        self.circuit = self.circuit.reverse_bits()

        if measure:
            self.circuit.measure_all()
            
            
#...!...!....................
    def bind_data(self, data):
        '''Binds input data to the parametrized QCRANK circuit.

        Args:
            data:
                Numerical data to bind to the parametrized QCRANK circuit. This can be:
                  * A numpy array of shape (2**nq_addr, nq_data)
                  * A list of numpy arrays of shape (2**nq_addr, nq_data)
                  * A numpy array of shape (2**nq_addr, nq_data, k)
        '''
        if not isinstance(data, (np.ndarray, list)):
            raise RuntimeError('data should be either a numpy array or a list of numpy arrays, '
                               f'got {isinstance(data)}')

        if isinstance(data, np.ndarray) and data.ndim == 2:
            data = data[..., np.newaxis]

        # Data must have three dimensions: (num_addr, nq_data, n_img)
        assert data.ndim == 3
        assert np.min(data) >= -1
        assert np.max(data) <= 1
        if data.shape[0] != self.num_addr or data.shape[1] != self.nq_data:
            raise RuntimeError(
                f'Input data has incorrect shape {data.shape}, expecting '
                f'({2 ** self.nq_addr}, {self.nq_data}, ...) '
                '[(2**nq_addr, nq_data, k)]'
            )
        self.data = data
        self.angles = np.arccos(data)
        self.angles_qcrank = np.empty(self.angles.shape)
        for r in range(self.angles.shape[1]):
            self.angles_qcrank[:, r] = qcrank.shifted_gray_permutation(
                qcrank.sfwht(self.angles[:, r]),
                r % self.nq_addr
            )

#...!...!....................
    def instantiate_circuits(self):
        '''Generates the instantiated circuits by assigning the bound parameters.'''
        if self.angles_qcrank is None:
            raise RuntimeError('Parametrized QCRANKV2 circuit has not been bound to data. '
                               'Run the `bind_data` method first.')
        circs = []
        for j in range(self.angles_qcrank.shape[2]):
            my_dict = {}
            for i in range(self.nq_data):
                my_dict[self.parV[i]] = self.angles_qcrank[:, i, j]
            circ = self.circuit.assign_parameters(my_dict)
            circs.append(circ)
        return circs

#...!...!....................
    def reco_from_yields(self, countsL):
        '''Reconstructs data from measurement counts.

        Args:
            countsL: list
                List of measurement counts from the instantiated circuits.

        Returns:
            rec_udata: numpy array
                Reconstructed un-normalized data with shape 
                (num_addr, nq_data, number of circuits).
        '''
        addrBitsL = [self.nq_data + i for i in range(self.nq_addr)]
        nCirc = len(countsL)

        rec_udata = np.zeros((self.num_addr, self.nq_data, nCirc))  # To match input indexing

        for ic in range(nCirc):
            counts = countsL[ic]
            for jd in range(self.nq_data):
                ibit = self.nq_data - 1 - jd
                valV = marginalize_qcrank_EV(addrBitsL, counts, dataBit=ibit)
                rec_udata[:, jd, ic] = valV

        return rec_udata


