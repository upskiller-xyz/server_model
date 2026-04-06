"""ONNX inference wrapper — mirrors eval.py _run_batch"""
import numpy as np
import onnxruntime as ort
from typing import Optional


class ONNXInferenceWrapper:
    """
    Wraps an ONNX Runtime session.

    Inference follows eval.py _run_batch exactly:
      feed = {'input': image}
      if model has 'cond_vec' input and cond_vec is provided:
          feed['cond_vec'] = cond_vec
      output = session.run(['output'], feed)[0]
    """

    def __init__(self, session: ort.InferenceSession):
        self._session = session
        self._has_cond_vec = any(inp.name == 'cond_vec' for inp in session.get_inputs())

    @property
    def has_cond_vec(self) -> bool:
        return self._has_cond_vec

    def __call__(self, input_tensor: np.ndarray, cond_vec: Optional[np.ndarray] = None) -> np.ndarray:
        feed = {'input': input_tensor}
        if self._has_cond_vec and cond_vec is not None:
            feed['cond_vec'] = cond_vec
        return self._session.run(['output'], feed)[0]
