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

    def warmup(self, height: int = 384, width: int = 384) -> None:
        """Run one dummy inference to trigger cuDNN autotuning / kernel compilation.

        The first real inference on a fresh CUDA session pays ~hundreds of ms of
        kernel selection (measured: ~790ms first vs ~17ms steady-state). Doing it
        here (at container init / prewarm) means the first real request is fast.
        Shape matches real input ((1, C, H, W)); dynamic dims fall back to H×W.
        """
        img_input = next(i for i in self._session.get_inputs() if i.name == self._input_name)
        dims = img_input.shape  # (batch, C, H, W); dims may be strings for dynamic axes
        c = dims[1] if isinstance(dims[1], int) and dims[1] > 0 else self._in_channels
        h = dims[2] if isinstance(dims[2], int) and dims[2] > 0 else height
        w = dims[3] if isinstance(dims[3], int) and dims[3] > 0 else width

        dummy = np.zeros((1, c, h, w), dtype=np.float32)
        cond = None
        if self._has_cond_vec:
            cv_input = next(i for i in self._session.get_inputs() if i.name == 'cond_vec')
            cshape = [d if isinstance(d, int) and d > 0 else 1 for d in cv_input.shape]
            cond = np.zeros(cshape, dtype=np.float32)

        self(dummy, cond)
