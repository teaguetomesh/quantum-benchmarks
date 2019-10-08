import numpy as np
from matplotlib import pyplot as plt

def qubism_indices(depth):
    def _qubism_indices(depth, prefix):
        if depth == 0:
            return prefix

        return np.block([[
            _qubism_indices(depth-1, prefix+'00'), _qubism_indices(depth-1, prefix+'01')
        ], [
            _qubism_indices(depth-1, prefix+'10'), _qubism_indices(depth-1, prefix+'11')
        ]])

    arr = np.array(_qubism_indices(depth, ''))
    f = np.vectorize(lambda s: int(s, 2))
    
    return f(arr)
    
def qubism_array(vector, verbose=False):
    base4exp = np.math.log(len(vector), 4)
    assert base4exp > 0 and base4exp % 1 == 0., "input has to be vector of length 4^n"
    
    if verbose: print('qubism size: ', 2*base4exp, 'x', 2*base4exp)
    indices = qubism_indices(base4exp)
    shuffled = np.array(vector)[indices]
    
    return np.abs(shuffled)

def qubism_plot(vector, vmax_vec=None, plot=None):
    # bias somewhat so that small numbers show up stronger
    vector_mapped = np.power(vector, .5)
    # take maximum range from own vector by default
    vmax_vec = vector_mapped if not isinstance(vmax_vec, np.ndarray) else np.power(vmax_vec, .5)
    vmax = np.max(np.abs(vmax_vec))
    
    if plot == None:
        fig, plot = plt.subplots(1, 1, figsize=(8,8))
        
    plot.set_xticks([], []) 
    plot.set_yticks([], [])
    plot.imshow(qubism_array(vector_mapped), cmap='viridis', vmin=0, vmax=vmax)

    return fig