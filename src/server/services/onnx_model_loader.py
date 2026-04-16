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
        inputs = session.get_inputs()
        self._has_cond_vec = any(inp.name == 'cond_vec' for inp in inputs)
        self._input_name = next(inp.name for inp in inputs if inp.name != 'cond_vec')
        self._output_name = session.get_outputs()[0].name
        image_input = next(inp for inp in inputs if inp.name == self._input_name)
        self._in_channels = image_input.shape[1]  # (batch, channels, H, W)

    @property
    def has_cond_vec(self) -> bool:
        return self._has_cond_vec

    @property
    def in_channels(self) -> int:
        return self._in_channels

    def __call__(self, input_tensor: np.ndarray, cond_vec: Optional[np.ndarray] = None) -> np.ndarray:
        feed = {self._input_name: input_tensor}
        if self._has_cond_vec and cond_vec is not None:
            feed['cond_vec'] = cond_vec
        return self._session.run([self._output_name], feed)[0]
