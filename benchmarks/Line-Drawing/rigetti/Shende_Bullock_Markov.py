import numpy as np
import pyquil as pq

def normalize_and_remove_phase(v):
    return v / np.linalg.norm(v) / np.exp(1.j * np.angle(v[0]))

def Shende_Bullock_Markov(state, qubits, GRAY_CODE = True, REVERSE_ZS = True):
    assert len(state) == 2**len(qubits)
    assert abs(np.linalg.norm(state) - 1.) < 1e-8

    program = pq.Program()

    n = len(qubits)
    for i in range(n):
        states = [normalize_and_remove_phase(np.array([
            np.exp(1.j * np.mean(np.angle(state[2*j*2**(n-i-1):(2*j+1)*2**(n-i-1)])))
                * np.linalg.norm(state[2*j*2**(n-i-1):(2*j+1)*2**(n-i-1)]),
            np.exp(1.j * np.mean(np.angle(state[(2*j+1)*2**(n-i-1):(2*j+2)*2**(n-i-1)])))
                * np.linalg.norm(state[(2*j+1)*2**(n-i-1):(2*j+2)*2**(n-i-1)]),
        ])) for j in range(2**i)]
        program += prepare_multiplexed(states, qubits[:i], qubits[i], GRAY_CODE = GRAY_CODE, REVERSE_ZS = REVERSE_ZS)
    return program

def prepare_multiplexed(states, control_qubits, target_qubit, GRAY_CODE = True, REVERSE_ZS = True):
    assert len(states) == 2**len(control_qubits)
    assert all(abs(np.linalg.norm(state) - 1.) < 1e-8 for state in states)
    n = len(control_qubits)

    thetas = [2 * np.arccos(state[0].real) / np.pi for state in states]
    phis = [np.angle(state[1]) / np.pi for state in states]

    if GRAY_CODE:
        # Loading Gray code in bs
        bs = [[0]]
        nums = [0]
        for i in range(n):
            bs = [[0] + b for b in bs] + [[1] + b for b in reversed(bs)]
            nums += [x + 2**i for x in reversed(nums)]
    else:
        # Loading regular order of bitstrings in bs
        bs = [tuple(map(int, f'{i:0{n}b}')) for i in range(2**n)]
        nums = list(range(2**n))

    program = pq.Program()

    if REVERSE_ZS:
        # Implement multiplexed Ry
        for b,c in zip(bs[:-1], bs[1:]):
            theta = sum((-1)**sum(x*y for x,y in zip(b,d)) * thetas[j] for j,d in zip(nums,bs)) / 2**n
            # program.append(cirq.Y(target_qubit)**theta)
            program += pq.gates.RY(theta * np.pi, target_qubit)
            # program.append(cirq.CNOT(control_qubits[j], target_qubit) for j,(x,y) in enumerate(zip(b,c)) if x != y)
            for j,(x,y) in enumerate(zip(b,c)):
                if x != y:
                    program += pq.gates.CNOT(control_qubits[j], target_qubit)
        b = bs[-1]
        theta = sum((-1)**sum(x*y for x,y in zip(b,d)) * thetas[j] for j,d in enumerate(bs)) / 2**n
        # program.append(cirq.Y(target_qubit)**theta)
        program += pq.gates.RY(theta * np.pi, target_qubit)

        # Implement reverse of multiplexed Rz
        phi = sum((-1)**sum(x*y for x,y in zip(b,d)) * phis[j] for j,d in zip(nums,bs)) / 2**n
        # program.append(cirq.Z(target_qubit)**phi)
        program += pq.gates.RZ(phi * np.pi, target_qubit)
        for c,b in zip(bs[-1:0:-1], bs[-2::-1]):
            # program.append(cirq.CNOT(control_qubits[j], target_qubit) for j,(x,y) in enumerate(zip(b,c)) if x != y)
            for j,(x,y) in enumerate(zip(b,c)):
                if x != y:
                    program += pq.gates.CNOT(control_qubits[j], target_qubit)
            phi = sum((-1)**sum(x*y for x,y in zip(b,d)) * phis[j] for j,d in zip(nums,bs)) / 2**n
            # program.append(cirq.Z(target_qubit)**phi)
            program += pq.gates.RZ(phi * np.pi, target_qubit)
    else:
        # Implement multiplexed Ry
        for b,c in zip(bs, bs[1:] + [bs[0]]):
            theta = sum((-1)**sum(x*y for x,y in zip(b,d)) * thetas[j] for j,d in zip(nums,bs)) / 2**n
            # program.append(cirq.Y(target_qubit)**theta)
            program += pq.gates.RY(theta * np.pi, target_qubit)
            # program.append(cirq.CNOT(control_qubits[j], target_qubit) for j,(x,y) in enumerate(zip(b,c)) if x != y)
            for j,(x,y) in enumerate(zip(b,c)):
                if x != y:
                    program += pq.gates.CNOT(control_qubits[j], target_qubit)

        # Implement multiplexed Rz
        for b,c in zip(bs, bs[1:] + [bs[0]]):
            phi = sum((-1)**sum(x*y for x,y in zip(b,d)) * phis[j] for j,d in zip(nums,bs)) / 2**n
            # program.append(cirq.Z(target_qubit)**phi)
            program += pq.gates.RZ(phi * np.pi, target_qubit)
            # program.append(cirq.CNOT(control_qubits[j], target_qubit) for j,(x,y) in enumerate(zip(b,c)) if x != y)
            for j,(x,y) in enumerate(zip(b,c)):
                if x != y:
                    program += pq.gates.CNOT(control_qubits[j], target_qubit)

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

    # Set up program
    n = int(np.log2(len(points)))
    qubits = list(range(n))
    program = pq.Program()
    program += Pragma('INITIAL_REWIRING', ['"GREEDY"'])
    program += Shende_Bullock_Markov(points, qubits)
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