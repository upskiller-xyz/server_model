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
  "prediction": [[0.123, 0.456, ...], ...],
  "shape": [384, 384],
  "status": "success"
}
```

**Error (400/500):**
```json
{
  "prediction": null,
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
| **Shape** | `[1, 3, 384, 384]` |
| **Format** | `[batch, channels, height, width]` |
| **Dtype** | `float32` |
| **Range** | `[-1.0, 1.0]` |
| **Channels** | RGB (Red, Green, Blue) |

### Output Tensor

| Property | Value |
|----------|-------|
| **Shape** | `[1, 1, 384, 384]` |
| **Format** | `[batch, channels, height, width]` |
| **Dtype** | `float32` |
| **Range (raw)** | `[0.0, ~0.04]` (model output) |
| **Range (server)** | `[0.0, ~10.0]` (scaled by 255) |

---

## Preprocessing Pipeline

Images are transformed from raw bytes to model input using this exact sequence:

```python
import numpy as np
import cv2

# 1. Decode image
nparr = np.frombuffer(image_bytes, np.uint8)
img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)

# 2. Extract RGB (drop alpha if present)
img = img[:, :, :3]

# 3. Convert BGR → RGB
img = img[:, :, ::-1].copy()

# 4. Normalize to [-1, 1]
img = img.astype(np.float32)
img = (img / 127.5) - 1.0

# 5. Resize to 384×384
img = cv2.resize(img, (384, 384), interpolation=cv2.INTER_NEAREST)

# 6. Transpose HWC → CHW
img = np.transpose(img, (2, 0, 1))

# 7. Add batch dimension
img = np.expand_dims(img, axis=0)

# Result: shape [1, 3, 384, 384], range [-1, 1]
```

### Key Points
- **Normalization:** `(pixel / 127.5) - 1` maps `[0, 255]` → `[-1, 1]`
- **Resize method:** `cv2.INTER_NEAREST` (preserves sharp edges)
- **Channel order:** RGB (cv2 loads BGR, so we reverse)

---

## Postprocessing

Model output is scaled and converted to JSON response:

```python
# Model returns: [1, 1, 384, 384], range ~[0, 0.04]
output = model(input_tensor)

# Remove batch/channel dimensions and scale to [0, 10]
prediction = output.squeeze() * 255  # Shape: [384, 384], range ~[0, 10]

# Convert to list for JSON
prediction_list = prediction.tolist()

# Response
{
  "prediction": prediction_list,  # Values in range [0, ~10]
  "shape": list(prediction.shape),
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
img_tensor = preprocess(image_bytes)  # Shape: [1, 3, 384, 384]

# Run inference
input_name = session.get_inputs()[0].name
onnx_input = {input_name: img_tensor}
onnx_output = session.run(None, onnx_input)
prediction = onnx_output[0]

# Postprocess: scale to [0, 10] range
result = prediction.squeeze() * 255
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

# Preprocess
nparr = np.frombuffer(image_bytes, np.uint8)
img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
img = img[:, :, :3][:, :, ::-1].copy()
img = (img.astype(np.float32) / 127.5) - 1.0
img = cv2.resize(img, (384, 384), interpolation=cv2.INTER_NEAREST)
img = np.transpose(img, (2, 0, 1))[np.newaxis, ...]

# Inference
session = ort.InferenceSession("df_default_2.0.1.onnx")
input_name = session.get_inputs()[0].name
output = session.run(None, {input_name: img})[0]

# Postprocess
prediction = output.squeeze()
print(f"Shape: {prediction.shape}")
print(f"Range: [{prediction.min():.3f}, {prediction.max():.3f}]")
```

---

## Summary Tables

### Tensor Shapes

| Stage | Shape | Dtype | Range |
|-------|-------|-------|-------|
| Raw image | `[H, W, 3/4]` | `uint8` | `[0, 255]` |
| After normalize | `[H, W, 3]` | `float32` | `[-1, 1]` |
| After resize | `[384, 384, 3]` | `float32` | `[-1, 1]` |
| **Model input** | `[1, 3, 384, 384]` | `float32` | `[-1, 1]` |
| **Model output** | `[1, 1, 384, 384]` | `float32` | Model-specific |
| JSON response | `[384, 384]` | List of floats | Model-specific |

### Preprocessing Steps

| Step | Operation | Details |
|------|-----------|---------|
| 1 | Decode | `cv2.imdecode()` with `IMREAD_UNCHANGED` |
| 2 | RGB extract | Take first 3 channels: `img[:, :, :3]` |
| 3 | BGR→RGB | Reverse channels: `img[:, :, ::-1]` |
| 4 | Normalize | `(img / 127.5) - 1.0` |
| 5 | Resize | `cv2.resize()` with `INTER_NEAREST` to 384×384 |
| 6 | Transpose | HWC→CHW: `np.transpose(img, (2, 0, 1))` |
| 7 | Batch | Add dimension: `np.expand_dims(img, 0)` |

---
