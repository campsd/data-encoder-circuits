'''
This implementation of QCrank
- can choose CX or CZ entangling basis
- uses  EVEN  ( expectation value encoding) for input in range [-1,1]

CX-implementation
     ┌───┐ ░                                                                                              ░ ┌─┐         
q_0: ┤ H ├─░─────────────────────■─────────────────■───────────────────────────■─────────────────■────────░─┤M├─────────
     ├───┤ ░                     │                 │                           │                 │        ░ └╥┘┌─┐      
q_1: ┤ H ├─░────────────────■────┼─────────────────┼────■─────────────────■────┼─────────────────┼────■───░──╫─┤M├──────
     └───┘ ░ ┌───────────┐┌─┴─┐  │  ┌───────────┐┌─┴─┐  │  ┌───────────┐┌─┴─┐  │  ┌───────────┐┌─┴─┐  │   ░  ║ └╥┘┌─┐   
q_2: ──────░─┤ Ry(p0[0]) ├┤ X ├──┼──┤ Ry(p0[1]) ├┤ X ├──┼──┤ Ry(p0[2]) ├┤ X ├──┼──┤ Ry(p0[3]) ├┤ X ├──┼───░──╫──╫─┤M├───
           ░ ├───────────┤└───┘┌─┴─┐├───────────┤└───┘┌─┴─┐├───────────┤└───┘┌─┴─┐├───────────┤└───┘┌─┴─┐ ░  ║  ║ └╥┘┌─┐
q_3: ──────░─┤ Ry(p1[0]) ├─────┤ X ├┤ Ry(p1[1]) ├─────┤ X ├┤ Ry(p1[2]) ├─────┤ X ├┤ Ry(p1[3]) ├─────┤ X ├─░──╫──╫──╫─┤M├
           ░ └───────────┘     └───┘└───────────┘     └───┘└───────────┘     └───┘└───────────┘     └───┘ ░  ║  ║  ║ └╥┘
c: 4/════════════════════════════════════════════════════════════════════════════════════════════════════════╩══╩══╩══╩═
                                                                                                             3  2  1  0 


CZ-implmentation
     ┌───┐ ░                                                                                        ░ ┌─┐         
q_0: ┤ H ├─░───────────────────────■───────────────■─────────────────────■───────────────■──────────░─┤M├─────────
     ├───┤ ░                       │               │                     │               │          ░ └╥┘┌─┐      
q_1: ┤ H ├─░────────────────────■──┼───────────────┼──■───────────────■──┼───────────────┼──■───────░──╫─┤M├──────
     └───┘ ░ ┌───┐┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───────────┐ │  │ ┌───┐ ░  ║ └╥┘┌─┐   
q_2: ──────░─┤ H ├┤ Ry(p0[0]) ├─■──┼─┤ Ry(p0[1]) ├─■──┼─┤ Ry(p0[2]) ├─■──┼─┤ Ry(p0[3]) ├─■──┼─┤ H ├─░──╫──╫─┤M├───
           ░ ├───┤├───────────┤    │ ├───────────┤    │ ├───────────┤    │ ├───────────┤    │ ├───┤ ░  ║  ║ └╥┘┌─┐
q_3: ──────░─┤ H ├┤ Ry(p1[0]) ├────■─┤ Ry(p1[1]) ├────■─┤ Ry(p1[2]) ├────■─┤ Ry(p1[3]) ├────■─┤ H ├─░──╫──╫──╫─┤M├
           ░ └───┘└───────────┘      └───────────┘      └───────────┘      └───────────┘      └───┘ ░  ║  ║  ║ └╥┘
c: 4/══════════════════════════════════════════════════════════════════════════════════════════════════╩══╩══╩══╩═
                                                                                                       3  2  1  0 


'''

import sys,os

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import ParameterVector
from qiskit.result.utils import marginal_distribution

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits import qcrank

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
        self.parV = [   ParameterVector(f'p{i}', 2 ** nq_addr) for i in range(nq_data) ]
        
        # Generate circuit
        num_q=nq_addr + nq_data
        self.circuit = QuantumCircuit(num_q,num_q)

        # Apply Hadamard gates (diffusion) to all address qubits
        for i in range(nq_addr):   self.circuit.h(i)
        if barrier:   self.circuit.barrier()
      
        if useCZ:  # will use CZ entangling gates
            for jd in range(nq_addr,num_q):   self.circuit.h( jd)
                       
        # Add nested and shifted uniform rotations along with controlled-X (CX) gates
        for ja in range(self.num_addr):
           
            for jd in range(nq_addr,num_q):
                pars=self.parV[jd-nq_addr][ja]
                self.circuit.ry(pars, jd)
                        
            for jd in range(nq_addr,num_q):
                qctr = qcrank.compute_control(ja, self.nq_addr, shift=jd % nq_addr)
                if useCZ:
                    self.circuit.cz(qctr, jd)
                else:
                    self.circuit.cx(qctr, jd)

        if useCZ :  # will use CZ entangling gates
            for jd in range(nq_addr,num_q):   self.circuit.h( jd)                

        if measure:
            if barrier: self.circuit.barrier()
            for i in range(num_q):
                j=num_q-1-i  # Reverse qubit order to match Qiskit's little-endian convention
                self.circuit.measure(i,j)
            
            
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
                qcrank.sfwht(self.angles[:, r]),  r % self.nq_addr
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
        return qcrank_reco_from_yields( countsL,self.nq_addr,self.nq_data )


# - - - - - - -  UTILITY function - - - - - - -

#...!...!....................
def qcrank_reco_from_yields( countsL,nq_addr,nq_data):
        '''Reconstructs data from measurement counts.

        Args:
            countsL: list
                List of measurement counts from the instantiated circuits.

        Returns:
            rec_udata: numpy array
                Reconstructed un-normalized data with shape 
                (num_addr, nq_data, number of circuits).
        '''
        addrBitsL = [nq_data + i for i in range(nq_addr)]
        nCirc = len(countsL)
        num_addr=1<<nq_addr
        rec_udata = np.zeros((num_addr, nq_data, nCirc))  # To match input indexing
        rec_udataErr = np.zeros_like(rec_udata)       
        for ic in range(nCirc):
            counts = countsL[ic]
            for jd in range(nq_data):
                ibit = nq_data - 1 - jd
                valV,valErV = marginalize_qcrank_EV(addrBitsL, counts, dataBit=ibit)
                rec_udata[:, jd, ic] = valV
                rec_udataErr[:, jd, ic] = valErV

        return rec_udata,rec_udataErr
    
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
        if m01>0 :
            p=m1/m01
            pErr=np.sqrt( p*(1-p)/m01) if m0*m1>0 else 1/m01
        else:
            p=0; perr=1
        prob[j]=p
        probEr[j]=pErr
        
    return 1-2*prob, 2*probEr
  

#...!...!..................
def analyze_qcrank_residuals(data_inp, data_rec):
    """
    Compute and print per-image residual analysis.
    - Computes per-pixel residuals
    - Computes mean residual and its standard deviation
    - Computes correlation between residuals and input data
    - Accumulates values across images and prints the mean at the end
    """

    n_img = data_inp.shape[-1]
    mean_residuals = []
    std_residuals = []
    correlations = []
    print('  analyze_residuals for %d imges'%n_img)
    
    for i in range(n_img):
        resid = data_inp[..., i] - data_rec[..., i]
        mean_resid = np.mean(resid)
        std_resid = np.std(resid)
        
        # Compute correlation coefficient
        corr_coef = np.corrcoef(data_inp[..., i].ravel(), data_rec[..., i].ravel())[0, 1]

        # Compute angle in degrees
        angle_deg = np.degrees(np.arccos(corr_coef))
        
        # Store results
        mean_residuals.append(mean_resid)
        std_residuals.append(std_resid)
        correlations.append(corr_coef)
        
        # Print values with C-style formatting
        print("img=%d  mean=%6.3f  std=%6.3f  corr=%.2f   tilt angle=%.1f/deg" % (i, mean_resid, std_resid, corr_coef,angle_deg))
    
    # Compute mean of accumulated values
    mean_mean_resid = np.mean(mean_residuals)
    mean_std_resid = np.mean(std_residuals)
    mean_corr = np.mean(correlations)
    
    # Print final averages
    print("Overall \nresiduals: mean=%.3f  std=%.3f  corr=%.3f\n" % (mean_mean_resid, mean_std_resid, mean_corr))
    
    return mean_mean_resid, mean_std_resid, mean_corr
