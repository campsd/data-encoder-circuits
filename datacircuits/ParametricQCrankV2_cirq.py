import sys, os
import numpy as np
import cirq
import sympy
from typing import Dict, List, Union

sys.path.append(os.path.abspath("/qcrank_light"))
from datacircuits import qcrank

def marginal_distribution(counts: Dict[str, int], indices: List[int]) -> Dict[str, int]:
    """
    Cirq replacement for qiskit.result.utils.marginal_distribution.
    Marginalizes a counts dictionary to specified qubit indices.
    
    Args:
        counts: Dictionary mapping bitstrings to counts
        indices: List of qubit indices to keep (0-indexed from right, matching Qiskit convention)
    
    Returns:
        Dictionary with marginalized counts
    """
    marginal_counts = {}
    
    for bitstring, count in counts.items():
        # Convert indices to keep the selected qubits
        # Bitstring is indexed from right to left (little-endian)
        marginal_bits = []
        for idx in sorted(indices):
            if idx < len(bitstring):
                # Index from the right of the string
                marginal_bits.append(bitstring[-(idx+1)])
        
        marginal_bitstring = ''.join(reversed(marginal_bits))
        
        if marginal_bitstring in marginal_counts:
            marginal_counts[marginal_bitstring] += count
        else:
            marginal_counts[marginal_bitstring] = count
    
    return marginal_counts

#...!...!....................
class ParametricQCrankV2_cirq():
#...!...!....................
    def __init__(self, nq_addr, nq_data,
                 measure: bool = True,
                 barrier: bool = True,
                 useCZ: bool = False,  # default uses CX gates
                 mockCirc: bool = False,  # Ry arg is left out and Latex version is printed to stdout
                 addressH: bool = True  # applies Hadamard on address qubits
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
                If True, inserts a barrier in the circuit (Note: Cirq doesn't have explicit barriers).
        '''

        # Sanity check: ensure at least one address-data qubit pair exists
        assert nq_addr * nq_data >= 1

        self.nq_addr = nq_addr
        self.nq_data = nq_data
        self.num_addr = 2 ** nq_addr
        self.measure = measure
        self.useCZ = useCZ
        
        # Create qubits
        num_q = nq_addr + nq_data
        self.qubits = cirq.LineQubit.range(num_q)
        self.addr_qubits = self.qubits[:nq_addr]
        self.data_qubits = self.qubits[nq_addr:]
        
        # Create parameter symbols for each data qubit
        self.parV = []
        for i in range(nq_data):
            params = [sympy.Symbol(f'p{i}_{j}') for j in range(2 ** nq_addr)]
            self.parV.append(params)
        
        # Generate circuit
        self.circuit = cirq.Circuit()
        
        if addressH:  # Apply Hadamard gates (diffusion) to all address qubits
            for q in self.addr_qubits:
                self.circuit.append(cirq.H(q))
        
        if useCZ:  # will use CZ entangling gates - apply H to data qubits
            for q in self.data_qubits:
                self.circuit.append(cirq.H(q))
        
        # Add nested and shifted uniform rotations along with controlled gates
        for ja in range(self.num_addr):
            # Add RY rotations
            for jd_idx, q_data in enumerate(self.data_qubits):
                param = self.parV[jd_idx][ja]
                if not mockCirc:
                    self.circuit.append(cirq.ry(param).on(q_data))
                else:
                    # Mock RY - just add identity or label
                    self.circuit.append(cirq.I(q_data))
            
            # Add controlled gates
            for jd_idx, q_data in enumerate(self.data_qubits):
                qctr_idx = qcrank.compute_control(ja, self.nq_addr, shift=jd_idx % nq_addr)
                qctr = self.qubits[qctr_idx]
                
                if useCZ:
                    self.circuit.append(cirq.CZ(qctr, q_data))
                else:
                    self.circuit.append(cirq.CNOT(qctr, q_data))
        
        if useCZ:  # Apply H gates back to data qubits
            for q in self.data_qubits:
                self.circuit.append(cirq.H(q))
        
        if measure:
            # Add measurements - note Cirq uses a single measurement key
            self.circuit.append(cirq.measure(*self.qubits, key='c'))
        
        if mockCirc:
            print("Circuit (mock mode):")
            print(self.circuit)

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
                               f'got {type(data)}')

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
                qcrank.sfwht(self.angles[:, r]), r % self.nq_addr
            )

#...!...!....................
    def instantiate_circuits(self, mult=1.):
        '''Generates the instantiated circuits by assigning the bound parameters.'''
        if not hasattr(self, 'angles_qcrank') or self.angles_qcrank is None:
            raise RuntimeError('Parametrized QCRANKV2 circuit has not been bound to data. '
                               'Run the `bind_data` method first.')
        circs = []
        for j in range(self.angles_qcrank.shape[2]):
            # Create parameter resolver for Cirq
            param_resolver = {}
            for i in range(self.nq_data):
                for k in range(len(self.parV[i])):
                    param_resolver[self.parV[i][k]] = mult * self.angles_qcrank[k, i, j]
            
            # Resolve parameters in the circuit
            resolved_circuit = cirq.resolve_parameters(self.circuit, param_resolver)
            circs.append(resolved_circuit)
        
        return circs

#...!...!....................
    def reco_from_yields(self, countsL):
        return qcrank_reco_from_yields(countsL, self.nq_addr, self.nq_data)


# Helper function to convert Cirq measurements to counts dictionary
def measurements_to_counts(measurements: np.ndarray, key: str = 'c') -> Dict[str, int]:
    """
    Convert Cirq measurement results to counts dictionary.
    
    Args:
        measurements: Array of measurement results from Cirq
        key: Measurement key (not used but kept for compatibility)
    
    Returns:
        Dictionary mapping bitstrings to counts
    """
    counts = {}
    for measurement in measurements:
        # Convert measurement array to bitstring (little-endian to match Qiskit)
        bitstring = ''.join(str(bit) for bit in reversed(measurement))
        counts[bitstring] = counts.get(bitstring, 0) + 1
    return counts


# Assuming this function exists and works with the counts format
def qcrank_reco_from_yields(countsL, nq_addr, nq_data):
    """
    Placeholder for the actual qcrank reconstruction function.
    This should work with the counts list format.
    """
    # Implementation would go here
    # This is assumed to work correctly as per the original code
    pass


def analyze_qcrank_residuals(data_inp, data_rec):
    """
    Placeholder for the residual analysis function.
    This is assumed to work correctly as per the original code.
    """
    # Implementation would go here
    pass
