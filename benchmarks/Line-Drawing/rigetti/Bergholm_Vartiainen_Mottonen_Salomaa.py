import numpy as np
import pyquil as pq
from .uniformly_controlled_circuits import generate_uniformly_controlled_circuit

def normalize_and_remove_phase(v):
    return v / np.linalg.norm(v) / np.exp(1.j * np.angle(v[0]))

def Bergholm_Vartiainen_Mottonen_Salomaa(state, qubits):
    assert len(state) == 2**len(qubits)
    n = len(qubits)

    # Generate uniformly controlled unitary and nullified state
    nullified_state = np.zeros(2**(n-1), dtype = np.complex_)
    unitaries = []
    for i in range(2**(n-1)):
        s = state[2*i:2*i+2]
        r = np.linalg.norm(s)
        nullified_state[i] = r
        unitaries.append(np.conj(np.array([
            [s[0] / r, -np.conj(s[1] / r)],
            [s[1] / r, np.conj(s[0] / r)]
        ])).T if r > 1e-8 else np.eye(2))

    # Generate uniformly controlled circuit
    UCC,R = generate_uniformly_controlled_circuit(unitaries, qubits[:-1], qubits[-1])

    # Correct for phases
    nullified_state /= R[::2]

    # Merge everything into one circuit
    program = pq.Program()
    if n > 1: program += Bergholm_Vartiainen_Mottonen_Salomaa(nullified_state, qubits[:-1])
    program += UCC.dagger()
    return program

if __name__ == '__main__':
    from pyquil.quil import Pragma
    num_qubits = 2
    N = 2**num_qubits
    # points = np.exp(2.j * np.pi * np.arange(N) / N) / np.sqrt(N)
    points = normalize_and_remove_phase(np.random.rand(N) + 1.j * np.random.rand(N))
    # points = np.array([0,0,0,0.70710678+0.70710678j])
    # points = np.array([0.45621777+0.j, 0.17273829+0.12513561j, 0.59497154+0.22042816j, 0.57531933+0.11311881j])
    np.set_printoptions(linewidth=200)
    print("State to prepare:", points)

    # Set up circuit
    n = int(np.log2(len(points)))
    qubits = list(range(n))
    program = pq.Program()
    program += Pragma('INITIAL_REWIRING', ['"GREEDY"'])
    program += Bergholm_Vartiainen_Mottonen_Salomaa(points, qubits)
    print(program)

    # Simulate
    psi = pq.api.WavefunctionSimulator().wavefunction(program).amplitudes
    result = psi[:2**n] / np.exp(1.j * np.angle(psi[0]))
    corrected_result = np.empty(result.shape, dtype = np.complex_)
    for i,r in enumerate(result):
        corrected_result[int(''.join(reversed(f"{i:0{n}b}")),2)] = r
    print(corrected_result)
    print(np.abs(corrected_result) - np.abs(points))
    print(np.angle(corrected_result) - np.angle(points))

    # Check resulting state
    print("Norm of the resulting vector:", np.linalg.norm(corrected_result))
    print("Maximum absolute error:", np.max(np.abs(corrected_result - points)))
    print("Inner product error:", abs(abs(np.sum(np.conj(corrected_result) * points)) - 1.))
