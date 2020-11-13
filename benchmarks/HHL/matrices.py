MATRICES = {
    "2qubit-1ancilla-SQSWAP": {
        "qubits": 2,
        "ancillas": 1,    
        "circuit": [
            ("TY", 1),
            ("RX", 2),
            ("SQSWAP", 1, 2),            
        ],
        "angles": [3.98119, 3.98119, -0.731195],
        "unitary real": [
            [0.46194, 0.0, 0.191342, 0.0],
            [-0.495722, 0.0652631, 0.0652631, 0.495722],
            [0.304381, 0.396677, 0.396677, -0.304381],
            [0.0, -0.191342, 0.0, 0.46194],
        ],
        "unitary imag": [
            [0.0, 0.800103, 0.0, 0.331414],
            [0.495722, 0.0652631, -0.0652631, 0.495722],
            [0.304381, -0.396677, 0.396677, 0.304381],
            [-0.331414, 0.0, 0.800103, 0.0],
        ],
    },
    "2qubit-1ancilla-CZ": {
        "qubits": 2,
        "ancillas": 1,
        "circuit": [("CZ", 1, 2), ("Y", 2), ("RX", 1), ("RY", 2), ("RY", 1), ("CZ", 1, 2), ("TX", 2), ("H", 1)],
        "angles": [4.19379, 4.19379, -0.533589],
        "histogram": [[0.515208, 0.783421], [0.484792, 0.216579]],
    },
    "3qubit-1ancilla-CZ": {
        "qubits": 3,
        "ancillas": 1,           
        "circuit": [
            ("TY", 1),
            ("TY", 2),
            ("Z", 3),
            ("CZ", 1, 2),
            ("TX", 1),
            ("Z", 2),
            ("S", 3),
            ("CZ", 2, 1),
            ("TY", 1),
            ("TY", 2),
            ("TY", 3),
            ("CZ", 1, 2),
        ],
        "angles": [-2.29647, -2.29647, -7.02536],
        "unitary real": [
            [0.426777, 0.176777, 0.0, 0.0, 0.176777, 0.0732233, 0.0, 0.0],
            [0.103553, -0.25, 0.176777, 0.426777, 0.25, -0.603553, 0.0732233, 0.176777],
            [0.0, 0.0, -0.426777, 0.176777, 0.0, 0.0, -0.176777, 0.0732233],
            [-0.176777, 0.426777, 0.25, 0.603553, -0.0732233, 0.176777, -0.103553, -0.25,],
            [-0.603553, -0.25, -0.176777, 0.0732233, 0.25, 0.103553, 0.426777, -0.176777,],
            [-0.0732233, 0.176777, 0.0, 0.0, 0.176777, -0.426777, 0.0, 0.0],
            [0.176777, 0.0732233, 0.25, -0.103553, -0.426777, -0.176777, 0.603553, -0.25,],
            [0.0, 0.0, 0.0732233, 0.176777, 0.0, 0.0, -0.176777, -0.426777],
        ],
        "unitary imag": [
            [0.478553, 0.198223, -0.125, 0.0517767, 0.551777, 0.228553, 0.301777, -0.125,],
            [-0.125, 0.301777, -0.125, -0.301777, -0.0517767, 0.125, -0.0517767, -0.125,],
            [0.125, 0.0517767, -0.728553, 0.301777, -0.301777, -0.125, 0.0517767, -0.0214466,],
            [0.125, -0.301777, -0.125, -0.301777, 0.0517767, -0.125, -0.0517767, -0.125,],
            [-0.125, -0.0517767, -0.125, 0.0517767, 0.301777, 0.125, 0.301777, -0.125],
            [0.228553, -0.551777, 0.125, 0.301777, -0.198223, 0.478553, 0.0517767, 0.125,],
            [0.125, 0.0517767, -0.125, 0.0517767, -0.301777, -0.125, 0.301777, -0.125],
            [-0.125, 0.301777, 0.0214466, 0.0517767, -0.0517767, 0.125, 0.301777, 0.728553,],
        ],
    }
}
