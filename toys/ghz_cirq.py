#!/usr/bin/env python3
__author__ = "Jan Balewski"
__email__ = "janstar1122@gmail.com"

'''
 Large GHZ state with many shots
python test_ghz.py --qubits 5 --shots 100000
'''

import cirq
import argparse
import numpy as np

def create_ghz_circuit(n_qubits):
    """Create a GHZ state circuit for n qubits with Z-basis measurements."""
    # Create qubits
    qubits = cirq.LineQubit.range(n_qubits)
    
    # Create circuit
    circuit = cirq.Circuit()
    
    # Create GHZ state: (|00...0⟩ + |11...1⟩)/√2
    # Apply Hadamard to first qubit
    circuit.append(cirq.H(qubits[0]))
    
    # Apply CNOT gates to entangle all qubits
    for i in range(n_qubits - 1):
        circuit.append(cirq.CNOT(qubits[i], qubits[i + 1]))
    
    # Add Z-basis measurements
    circuit.append(cirq.measure(*qubits, key='result'))
    
    return circuit, qubits

def run_simulation(circuit, n_shots):
    """Run the circuit simulation with specified number of shots."""
    # Use ideal simulator (no noise)
    simulator = cirq.Simulator()
    
    # Run the circuit
    result = simulator.run(circuit, repetitions=n_shots)
    
    return result

def calculate_probabilities_and_errors(result, n_qubits, n_shots):
    """Calculate probabilities and statistical errors from measurement results."""
    # Get histogram of results
    counts = result.histogram(key='result')
    
    # Initialize dictionary for all possible states
    all_states = {}
    for i in range(2**n_qubits):
        all_states[i] = counts.get(i, 0)
    
    # Calculate probabilities and errors
    probabilities = {}
    errors = {}
    
    for state, count in all_states.items():
        prob = count / n_shots
        probabilities[state] = prob
        # Statistical error (standard deviation for binomial distribution)
        errors[state] = np.sqrt(prob * (1 - prob) / n_shots)
    
    return probabilities, errors

def print_results(probabilities, errors, n_qubits):
    """Print the results in a formatted way."""
    print("\nMeasurement Results (Z-basis):")
    print("-" * 50)
    print(f"{'State':<15} {'Probability':<15} {'Error':<15}")
    print("-" * 50)
    
    for state in sorted(probabilities.keys()):
        state_str = f"|{state:0{n_qubits}b}⟩"
        prob = probabilities[state]
        err = errors[state]
        if prob > 0.001:  # Only print states with probability > 0.1%
            print(f"{state_str:<15} {prob:.6f} ± {err:.6f}")
    
    # Print expected vs observed for GHZ state
    print("\nGHZ State Analysis:")
    print("-" * 50)
    all_zeros = 0  # |00...0⟩
    all_ones = 2**n_qubits - 1  # |11...1⟩
    
    expected_prob = 0.5
    observed_prob_zeros = probabilities[all_zeros]
    observed_prob_ones = probabilities[all_ones]
    
    print(f"Expected probability for |{'0'*n_qubits}⟩: {expected_prob:.6f}")
    print(f"Observed probability for |{'0'*n_qubits}⟩: {observed_prob_zeros:.6f} ± {errors[all_zeros]:.6f}")
    print(f"Expected probability for |{'1'*n_qubits}⟩: {expected_prob:.6f}")
    print(f"Observed probability for |{'1'*n_qubits}⟩: {observed_prob_ones:.6f} ± {errors[all_ones]:.6f}")
    
    # Calculate total probability for GHZ states
    total_ghz_prob = observed_prob_zeros + observed_prob_ones
    total_ghz_error = np.sqrt(errors[all_zeros]**2 + errors[all_ones]**2)
    print(f"\nTotal GHZ state probability: {total_ghz_prob:.6f} ± {total_ghz_error:.6f}")
    print(f"Expected total: 1.000000")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Measure GHZ state using Cirq')
    parser.add_argument('--shots', type=int, default=1000,
                       help='Number of measurement shots (default: 1000)')
    parser.add_argument('--qubits', type=int, default=3,
                       help='Number of qubits for GHZ state (default: 3)')
    
    args = parser.parse_args()
    
    print(f"Creating {args.qubits}-qubit GHZ state")
    print(f"Running {args.shots} measurement shots")
    print("Using ideal simulator (no noise)")
    
    # Create circuit
    circuit, qubits = create_ghz_circuit(args.qubits)
    
    print("\nCircuit:")
    print(circuit)
    
    # Run simulation
    result = run_simulation(circuit, args.shots)
    
    # Calculate probabilities and errors
    probabilities, errors = calculate_probabilities_and_errors(result, args.qubits, args.shots)
    
    # Print results
    print_results(probabilities, errors, args.qubits)

if __name__ == "__main__":
    main()
