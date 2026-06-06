"""Shared test fixtures.

onnxruntime is a heavy GPU/native dependency that isn't installed in the unit
test environment. The src modules import it at module load, so we register a
lightweight fake when the real package is unavailable. The fake exposes just
enough surface for the simulation service's model loading and inference paths.
"""
import sys
import types


def _install_fake_onnxruntime() -> None:
    try:
        import onnxruntime  # noqa: F401
        return
    except ImportError:
        pass

    import numpy as np

    ort = types.ModuleType("onnxruntime")

    class GraphOptimizationLevel:
        ORT_DISABLE_ALL = "ORT_DISABLE_ALL"
        ORT_ENABLE_ALL = "ORT_ENABLE_ALL"

    class SessionOptions:
        def __init__(self):
            self.graph_optimization_level = None
            self.optimized_model_filepath = None

    class InferenceSession:
        def __init__(self, path, sess_options=None, providers=None):
            self.path = path
            self.sess_options = sess_options
            self._providers = providers or ["CPUExecutionProvider"]

        def get_inputs(self):
            return [types.SimpleNamespace(name="input", shape=[1, 3, 384, 384])]

        def get_outputs(self):
            return [types.SimpleNamespace(name="output")]

        def get_providers(self):
            return self._providers

        def run(self, output_names, feed):
            return [np.zeros((1, 1, 384, 384), dtype=np.float32)]

    ort.GraphOptimizationLevel = GraphOptimizationLevel
    ort.SessionOptions = SessionOptions
    ort.InferenceSession = InferenceSession
    ort.get_available_providers = lambda: ["CPUExecutionProvider"]
    sys.modules["onnxruntime"] = ort


_install_fake_onnxruntime()
