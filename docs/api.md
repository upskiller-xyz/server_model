# API Documentation

This document describes the REST API endpoints for the Upskiller Model Server.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Server Configuration](#server-configuration)
3. [API Endpoints](#api-endpoints)
   - [GET / - Health Check](#get---health-check)
   - [POST /run - Run Prediction](#post-run---run-prediction)
4. [Error Handling](#error-handling)
5. [Usage Examples](#usage-examples)

---

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run server (development)
python main.py

# Run server (production with gunicorn)
gunicorn main:app --bind 0.0.0.0:8000 --workers 4
```

### Docker

```bash
# Using docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down
```

---

## Server Configuration

**Model Version:** `df_default_2.0.1` 
**Model Format:** `ONNX` 
**Input Size:** `384 × 384` pixels
**Server Name:** `Upskiller Model Server`
**Version:** `2.0.0`
**Default Port:** `8000`

The server automatically downloads the model from:
```
https://daylight-factor.s3.fr-par.scw.cloud/models/df_default_2.0.1.onnx
```

Models are cached locally in: `./checkpoints/df_default_2.0.1.onnx`

---

## API Endpoints

### GET `/` - Health Check

Returns the current status of the server.

**Request:**
```bash
curl http://localhost:8000/
```

**Response (200 OK):**
```json
{
  "name": "Upskiller Model Server",
  "version": "2.0.0",
  "status": "running"
}
```

**Response Fields:**
- `name` (string): Server name
- `version` (string): Server version
- `status` (string): Current server status - `"starting"`, `"running"`, or `"error"`

**Example in Python:**
```python
import requests

response = requests.get("http://localhost:8000/")
data = response.json()

print(f"Server: {data['name']} v{data['version']}")
print(f"Status: {data['status']}")
```

**Example in TypeScript:**
```typescript
const response = await fetch("http://localhost:8000/");
const data = await response.json();

console.log(`Server: ${data.name} v${data.version}`);
console.log(`Status: ${data.status}`);
```

---

### POST `/run` - Run Prediction

Processes an uploaded image and returns model predictions.

**Request:**
- **Method:** POST
- **Content-Type:** `multipart/form-data`
- **Body Parameter:** `file` - Image file to process

**Supported Image Formats:**
- PNG (`.png`)
- JPEG (`.jpg`, `.jpeg`)
- Any format supported by OpenCV

**Image Requirements:**
- Any resolution (automatically resized to 384×384)
- RGB or RGBA

**Request Example (cURL):**
```bash
curl -X POST http://localhost:8000/run \
  -F "file=@/path/to/image.jpg"
```

**Request Example (Python with requests):**
```python
import requests

with open("image.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/run", files=files)

result = response.json()
print(result)
```

**Request Example (Python with multiple images):**
```python
import requests
from pathlib import Path

images = Path("images/").glob("*.jpg")

for image_path in images:
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post("http://localhost:8000/run", files=files)

        if response.status_code == 200:
            result = response.json()
            print(f"✓ {image_path.name}: {result['shape']}")
        else:
            print(f"✗ {image_path.name}: {response.json()['error']}")
```

**Request Example (TypeScript):**
```typescript
const formData = new FormData();
const fileInput = document.getElementById('imageFile') as HTMLInputElement;

if (fileInput.files?.[0]) {
  formData.append('file', fileInput.files[0]);
}

const response = await fetch("http://localhost:8000/run", {
  method: "POST",
  body: formData
});

const result = await response.json();
console.log(result);
```

**Response (200 OK - Success):**
```json
{
  "prediction": [
    [0.123, 0.456, 0.789, ...],
    [0.234, 0.567, 0.890, ...],
    ...
  ],
  "shape": [384, 384],
  "status": "success"
}
```

**Response Fields:**
- `prediction` (array): 2D array of prediction values with shape `[384, 384]`
  - Each value is a float representing the model's prediction for that pixel
  - Range: `[0.0, ~10.0]` (raw model output scaled by 255)
- `shape` (array): Dimensions of the prediction `[height, width]`
- `status` (string): `"success"` for successful predictions


## Additional Resources

- [Input/output format specification](input_output_formats.md)
- [Demo notebook with examples](../example/demo.ipynb)

---
