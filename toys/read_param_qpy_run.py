#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

from qiskit import qpy
import numpy as np
import re
from collections import defaultdict

def load_and_analyze_circuit(filepath):
    """
    Loads the first circuit from a QPY file and prints its properties.
    """
    print(f"Loading circuits from: {filepath}")
    with open(filepath, 'rb') as fd:
        circuits = qpy.load(fd)

    print(f"M: loaded {len(circuits)} circuits.")
    
    # Select the first circuit for analysis
    qc = circuits[0]
    circuit_index = 0

    n2q = qc.num_nonlocal_gates()
    depth = qc.depth()
    depth2q = qc.depth(filter_function=lambda x: x.operation.num_qubits == 2)

    print(f'\nAnalyzing Circuit {circuit_index}:')
    print(f'  - 2q-gates: {n2q}')
    print(f'  - Total depth: {depth}')
    print(f'  - 2q-depth: {depth2q}')
    
    print("\nInitial parametrized circuit diagram:")
    print(qc.draw('text', idle_wires=False))
    
    return qc

def get_circuit_parameters(qc):
    """
    Identifies and prints information about the parameters in a quantum circuit,
    grouping indexed parameters into vectors.
    """
    # Group parameters by base name (e.g., 'P0' for 'P0[0]', 'P0[1]', etc.)
    grouped_params = defaultdict(list)
    for p in qc.parameters:
        match = re.match(r'(\w+)', p.name)
        if match:
            base_name = match.group(1)
            grouped_params[base_name].append(p)

    if not grouped_params:
        print("\nCircuit has no free parameters.")
        return {}

    print(f"\nFound {len(qc.parameters)} total parameters, grouped into {len(grouped_params)} objects:")
    # Sort by base name for deterministic output
    sorted_grouped_params = {k: grouped_params[k] for k in sorted(grouped_params)}
    
    for base_name, params_list in sorted_grouped_params.items():
        dimension = len(params_list)
        print(f"  - Name: {base_name}, Dimension: {dimension}")

    return sorted_grouped_params

def assign_random_parameters(qc, grouped_params):
    """
    Generates random values, binds them to the circuit's parameters,
    and returns both the bound circuit and a dictionary of the values.
    """
    if not grouped_params:
        return qc, {}

    print("\nGenerating random values in range [-1, 1]:")
    parameter_bindings = {}
    param_values_dict = {}

    for base_name, params_list in grouped_params.items():
        dimension = len(params_list)
        if dimension == 1:
            # It's a scalar parameter
            random_value = np.random.uniform(-1, 1)
            parameter_bindings[params_list[0]] = random_value
            param_values_dict[base_name] = np.array([random_value])
            print(f"  - Assigning to '{base_name}': {random_value:.4f}")
        else:
            # It's a vector parameter
            random_vector = np.random.uniform(-1, 1, size=dimension)
            param_values_dict[base_name] = random_vector
            print(f"  - Assigning to '{base_name}': {np.array2string(random_vector, precision=4, floatmode='fixed')}")
            
            def get_index(p):
                match = re.search(r'\[(\d+)\]', p.name)
                return int(match.group(1)) if match else -1

            sorted_params = sorted(params_list, key=get_index)
            
            for i, p in enumerate(sorted_params):
                parameter_bindings[p] = random_vector[i]

    print("\nBinding parameters to create new circuit...")
    qc_bound = qc.assign_parameters(parameter_bindings)
    return qc_bound, param_values_dict

def main():
    """
    Main execution function.
    """
    inpF = 'out/qcrank_nqa2_nqd2.qpy'
    inpF='out/exp_9519b3_circ.qpy'
    
    # 1. Load and analyze the circuit from file
    qc = load_and_analyze_circuit(inpF)
    
    # 2. Extract parameter names and their dimensions
    circuit_params_grouped = get_circuit_parameters(qc)

    # 3. Assign random values to the parameters
    if circuit_params_grouped:
        bound_qc, param_values = assign_random_parameters(qc, circuit_params_grouped)
        
        print("\nFinal circuit with parameters bound:")
        print(bound_qc.draw('text', idle_wires=False))
        
        print("\nGenerated parameter values dictionary:")
        for name, value_array in param_values.items():
            print(f"  '{name}': {value_array}")

if __name__ == "__main__":
    main() 
