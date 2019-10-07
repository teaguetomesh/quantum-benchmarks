from libbench.lib import print_hl
from libbench.link import VendorJob, VendorLink


IBM_KNOWN_STATEVECTOR_DEVICES = ["statevector_simulator"]

IBM_KNOWN_MEASURE_LOCAL_DEVICES = ["qasm_simulator"]


class IBMJob(VendorJob):
    pass


class IBMCloudLink(VendorLink):
    def __init__(self):
        super().__init__()

        # load accounts
        from qiskit import IBMQ

        IBMQ.load_account()

        # check whether we have accounts
        providers = IBMQ.providers()
        assert len(providers) == 1, "no account loaded, or multiple accounts found."

        self.IBMQ_cloud = providers[0]

        print_hl("IBMQ cloud account loaded.")

    def get_devices(self):
        return {device.name(): device for device in self.IBMQ_cloud.backends()}


class IBMMeasureLocalLink(VendorLink):
    def __init__(self):
        super().__init__()

        from qiskit import Aer

        self.IBMQ_local = Aer

        print_hl("qiskit Aer loaded.")

    def get_devices(self):
        return {
            device.name(): device
            for device in self.IBMQ_local.backends()
            if device.name() in IBM_KNOWN_MEASURE_LOCAL_DEVICES
        }


class IBMStatevectorLink(VendorLink):
    def __init__(self):
        super().__init__()

        from qiskit import Aer

        self.IBMQ_local = Aer

        print_hl("qiskit Aer loaded.")

    def get_devices(self):
        return {
            device.name(): device
            for device in self.IBMQ_local.backends()
            if device.name() in IBM_KNOWN_STATEVECTOR_DEVICES
        }
