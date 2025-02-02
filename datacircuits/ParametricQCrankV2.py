'''
This implementation of QCrank
- can choose CX or CZ entangling basis
- uses  EVEN  ( expectation value encoding) for input in range [-1,1]

CX-implementation
              ░ ┌───────────┐     ┌───┐┌───────────┐     ┌───┐┌───────────┐     ┌───┐┌───────────┐     ┌───┐ ░ ┌─┐         
   q_0: ──────░─┤ Ry(p1[0]) ├─────┤ X ├┤ Ry(p1[1]) ├─────┤ X ├┤ Ry(p1[2]) ├─────┤ X ├┤ Ry(p1[3]) ├─────┤ X ├─░─┤M├─────────
              ░ ├───────────┤┌───┐└─┬─┘├───────────┤┌───┐└─┬─┘├───────────┤┌───┐└─┬─┘├───────────┤┌───┐└─┬─┘ ░ └╥┘┌─┐      
   q_1: ──────░─┤ Ry(p0[0]) ├┤ X ├──┼──┤ Ry(p0[1]) ├┤ X ├──┼──┤ Ry(p0[2]) ├┤ X ├──┼──┤ Ry(p0[3]) ├┤ X ├──┼───░──╫─┤M├──────
        ┌───┐ ░ └───────────┘└─┬─┘  │  └───────────┘└─┬─┘  │  └───────────┘└─┬─┘  │  └───────────┘└─┬─┘  │   ░  ║ └╥┘┌─┐   
   q_2: ┤ H ├─░────────────────■────┼─────────────────┼────■─────────────────■────┼─────────────────┼────■───░──╫──╫─┤M├───
        ├───┤ ░                     │                 │                           │                 │        ░  ║  ║ └╥┘┌─┐
   q_3: ┤ H ├─░─────────────────────■─────────────────■───────────────────────────■─────────────────■────────░──╫──╫──╫─┤M├
        └───┘ ░                                                                                              ░  ║  ║  ║ └╥┘
meas: 4/════════════════════════════════════════════════════════════════════════════════════════════════════════╩══╩══╩══╩═
                                                                                                                0  1  2  3 



CZ-implmentation
              ░ ┌───┐┌────────────┐     ┌───┐┌────────────┐     ┌───┐┌────────────┐     ┌───┐┌────────────┐     ┌───┐┌───┐ ░ ┌─┐         
   q_0: ──────░─┤ H ├┤ Ry(-p1[0]) ├─────┤ X ├┤ Ry(-p1[1]) ├─────┤ X ├┤ Ry(-p1[2]) ├─────┤ X ├┤ Ry(-p1[3]) ├─────┤ X ├┤ H ├─░─┤M├─────────
              ░ ├───┤├────────────┤┌───┐└─┬─┘├────────────┤┌───┐└─┬─┘├────────────┤┌───┐└─┬─┘├────────────┤┌───┐└─┬─┘├───┤ ░ └╥┘┌─┐      
   q_1: ──────░─┤ H ├┤ Ry(-p0[0]) ├┤ X ├──┼──┤ Ry(-p0[1]) ├┤ X ├──┼──┤ Ry(-p0[2]) ├┤ X ├──┼──┤ Ry(-p0[3]) ├┤ X ├──┼──┤ H ├─░──╫─┤M├──────
        ┌───┐ ░ └───┘└────────────┘└─┬─┘  │  └────────────┘└─┬─┘  │  └────────────┘└─┬─┘  │  └────────────┘└─┬─┘  │  └───┘ ░  ║ └╥┘┌─┐   
   q_2: ┤ H ├─░──────────────────────■────┼──────────────────┼────■──────────────────■────┼──────────────────┼────■────────░──╫──╫─┤M├───
        ├───┤ ░                           │                  │                            │                  │             ░  ║  ║ └╥┘┌─┐
   q_3: ┤ H ├─░───────────────────────────■──────────────────■────────────────────────────■──────────────────■─────────────░──╫──╫──╫─┤M├
        └───┘ ░                                                                                                            ░  ║  ║  ║ └╥┘
meas: 4/══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╩══╩══╩══╩═
                                                                                                                              0  1  2  3 


'''

import sys,os

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.result.utils import marginal_distribution

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits import qcrank
    
#...!...!....................
def marginalize_qcrank_EV(  addrBitsL, probsB, dataBit):
    #print('MQCEV inp bits:',dataBit,addrBitsL)
    # ... marginal distributions for 2 data qubits, for 1 circuit
    assert dataBit not in addrBitsL
    bitL=[dataBit]+addrBitsL
    #print('MQCEV bitL:',bitL)
    probs=marginal_distribution(probsB,bitL)
    
    #.... for each address comput probabilities,stat error, EV, EV_err 
    nq_addr=len(addrBitsL)
    seq_len=1<<nq_addr
    prob=np.zeros(seq_len)
    probEr=np.zeros(seq_len)
    fstr='0'+str(nq_addr)+'b' 
    for j in range(seq_len):
        mbit=format(j,fstr)
        mbit0=mbit+'0'; mbit1=mbit+'1'
        m1=probs[mbit1] if mbit1 in probs else 0
        m0=probs[mbit0] if mbit0 in probs else 0
        m01=m0+m1
        #print(j,mbit,'sum=',m01)
        p=m1/m01 if m01>0 else 0
        pErr=np.sqrt( p*(1-p)/m01) if m0*m1>0 else 1/m01
        prob[j]=p
        probEr[j]=pErr
        
    return 1-2*prob, 2*probEr
  

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

        # Create a parameter vector for each data qubit, each with 2**nq_addr parameters
        self.parV = [
            ParameterVector(f'p{i}', 2 ** nq_addr) for i in range(nq_data)
        ]
        
        # Generate circuit
        self.circuit = QuantumCircuit(nq_addr + nq_data)

        # Apply Hadamard gates (diffusion) to all address qubits
        for i in range(nq_addr):
            self.circuit.h(i)
        if barrier:
            self.circuit.barrier()

        qdl=nq_addr; qdr=nq_addr+nq_data  # precompute range of address qubits
        
        if useCZ:  # will use CZ entangling gates
            for jd in range(qdl,qdr):
                self.circuit.h( jd)
                       
        # Add nested and shifted uniform rotations along with controlled-X (CX) gates
        for ja in range(self.num_addr):
           
            for jd in range(qdl,qdr):
                pars=self.parV[jd-nq_addr][ja]
                if useCZ: pars=-pars
                self.circuit.ry(pars, jd)
                        
            for jd in range(qdl,qdr):
                qctr = qcrank.compute_control(ja, self.nq_addr, shift=jd % nq_addr)
                self.circuit.cx(qctr, jd)

        if useCZ:  # will use CZ entangling gates
            for jd in range(qdl,qdr):
                self.circuit.h( jd)
  
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
        rec_udataErr = np.zeros_like(rec_udata)
    
        for ic in range(nCirc):
            counts = countsL[ic]
            for jd in range(self.nq_data):
                ibit = self.nq_data - 1 - jd
                valV,valErV = marginalize_qcrank_EV(addrBitsL, counts, dataBit=ibit)
                rec_udata[:, jd, ic] = valV
                rec_udataErr[:, jd, ic] = valErV

        return rec_udata,rec_udataErr


