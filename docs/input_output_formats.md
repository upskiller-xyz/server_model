# Input/Output Format Specification

Technical specification for the Upskiller Model Server data formats.

---

## Server Configuration

| Setting | Value |
|---------|-------|
| Model | `df_default_2.0.1.onnx` |
| Input Size | `384 × 384` |
| Default Port | `8000` |

---

## HTTP API

### Request Format
- **Endpoint:** `POST /run`
- **Content-Type:** `multipart/form-data`
- **Field:** `file` (image file)
- **Supported formats:** PNG, JPEG, GIF, or any OpenCV-compatible format

### Response Format

**Success (200):**
```json
{
  "simulation": [[0.123, 0.456, ...], ...],
  "shape": [384, 384],
  "status": "success"
}
```

**Error (400/500):**
```json
{
  "simulation": null,
  "shape": null,
  "status": "error",
  "error": "Error message"
}
```

---

## Model Interface

### Input Tensor

| Property | Value |
|----------|-------|
| **Shape** | `[1, C, 384, 384]` where `C` is `3` for RGB inputs and `4` for RGBA inputs |
| **Format** | `[batch, channels, height, width]` |
| **Dtype** | `float32` |
| **Range** | `[0.0, 1.0]` |
| **Channels** | RGB or RGBA — the alpha channel, when present, is preserved (it carries input information such as background masks). |

### Output Tensor

| Property | Value |
|----------|-------|
| **Shape** | `[1, 1, 384, 384]` |
| **Format** | `[batch, channels, height, width]` |
| **Dtype** | `float32` |
| **Range** | raw model output, no rescaling. For `df_default_2.0.1` this is approximately `[0.0, ~0.04]`. |

---

## Preprocessing Pipeline

Images are transformed from raw bytes to model input using this exact sequence:

```python
import numpy as np
import cv2

# 1. Decode image (preserves alpha channel when present)
nparr = np.frombuffer(image_bytes, np.uint8)
img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

# 2. Convert cv2's BGR(A) ordering to RGB(A); keep alpha if present
if img.ndim == 3 and img.shape[-1] == 3:
    img = img[:, :, ::-1].copy()                  # BGR  → RGB
elif img.ndim == 3 and img.shape[-1] == 4:
    img = img[:, :, [2, 1, 0, 3]].copy()          # BGRA → RGBA

# 3. Normalize to [0, 1]
img = img.astype(np.float32) / 255.0

# 4. Resize to 384×384
img = cv2.resize(img, (384, 384), interpolation=cv2.INTER_LINEAR)

# 5. Transpose HWC → CHW
img = np.transpose(img, (2, 0, 1))

# 6. Add batch dimension
img = np.expand_dims(img, axis=0)

# Result: shape [1, C, 384, 384] (C = 3 or 4), range [0, 1]
```

### Key Points
- **Alpha:** preserved when present — the model relies on it (e.g. as a background mask).
- **Normalization:** `pixel / 255` maps `[0, 255]` → `[0, 1]`
- **Resize method:** `cv2.INTER_LINEAR` (bilinear, matches `DaylightDataset`)
- **Channel order:** RGB(A); cv2 loads BGR(A), so we reorder.

---

## Postprocessing

Model output is returned as-is (no rescaling) and converted to JSON:

```python
# Model returns: [1, 1, 384, 384], raw model output (e.g. ~[0, 0.04] for df_default_2.0.1)
output = model(input_tensor)

# Remove batch/channel dimensions only — values are NOT rescaled
simulation = output.squeeze()  # Shape: [384, 384], raw model range

# Convert to list for JSON
simulation_list = simulation.tolist()

# Response
{
  "simulation": simulation_list,  # Raw model values (apply × 255 client-side if you need [0, ~10])
  "shape": list(simulation.shape),
  "status": "success"
}
```

---

## ONNX Inference Pattern

The exact pattern used for ONNX model inference:

```python
import onnxruntime as ort

# Load model
session = ort.InferenceSession("model.onnx")

# Preprocess image (see pipeline above)
img_tensor = preprocess(image_bytes)  # Shape: [1, C, 384, 384] (C = 3 or 4)

# Run inference
input_name = session.get_inputs()[0].name
onnx_input = {input_name: img_tensor}
onnx_output = session.run(None, onnx_input)
simulation = onnx_output[0]

# Postprocess: drop batch/channel dims, no rescaling
result = simulation.squeeze()
```

---

## Complete Example

```python
import numpy as np
import cv2
import onnxruntime as ort

# Load image
with open('image.jpg', 'rb') as f:
    image_bytes = f.read()

# Preprocess (preserve alpha when present)
nparr = np.frombuffer(image_bytes, np.uint8)
img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
if img.ndim == 3 and img.shape[-1] == 3:
    img = img[:, :, ::-1].copy()                  # BGR  → RGB
elif img.ndim == 3 and img.shape[-1] == 4:
    img = img[:, :, [2, 1, 0, 3]].copy()          # BGRA → RGBA
img = img.astype(np.float32) / 255.0
img = cv2.resize(img, (384, 384), interpolation=cv2.INTER_LINEAR)
img = np.transpose(img, (2, 0, 1))[np.newaxis, ...]

# Inference
session = ort.InferenceSession("df_default_2.0.1.onnx")
input_name = session.get_inputs()[0].name
output = session.run(None, {input_name: img})[0]

# Postprocess: drop batch/channel dims, no rescaling
simulation = output.squeeze()
print(f"Shape: {simulation.shape}")
print(f"Range: [{simulation.min():.4f}, {simulation.max():.4f}]")
```

---

## Summary Tables

### Tensor Shapes

| Stage | Shape | Dtype | Range |
|-------|-------|-------|-------|
| Raw image | `[H, W]`, `[H, W, 3]`, or `[H, W, 4]` | `uint8` | `[0, 255]` |
| After normalize | `[H, W, C]` (C ∈ {1, 3, 4}) | `float32` | `[0, 1]` |
| After resize | `[384, 384, C]` | `float32` | `[0, 1]` |
| **Model input** | `[1, C, 384, 384]` | `float32` | `[0, 1]` |
| **Model output (raw)** | `[1, 1, 384, 384]` | `float32` | model-dependent (e.g. `[0, ~0.04]` for `df_default_2.0.1`) |
| **Server output** | `[384, 384]` | `float32` | same as model output (no rescaling) |
| JSON response | `[384, 384]` | List of floats | same as model output |

### Preprocessing Steps

| Step | Operation | Details |
|------|-----------|---------|
| 1 | Decode | `cv2.imdecode()` with `IMREAD_UNCHANGED` (preserves alpha) |
| 2 | Channel reorder | `img[:, :, ::-1]` for BGR→RGB, or `img[:, :, [2,1,0,3]]` for BGRA→RGBA |
| 3 | Normalize | `img / 255.0` |
| 4 | Resize | `cv2.resize()` with `INTER_LINEAR` to 384×384 |
| 5 | Transpose | HWC→CHW: `np.transpose(img, (2, 0, 1))` (or add channel dim for grayscale) |
| 6 | Batch | Add dimension: `np.expand_dims(img, 0)` |

---
