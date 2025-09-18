# API Documentation

This document describes the main API endpoints for the Model Server.
Example requests are provided in both **Python** (using `requests`) and **TypeScript** (using `fetch`). Use [the playground notebook](../playground.ipynb) for hands-on examples with the API.

---

## `/`
**GET** `/`
Health check endpoint that returns the current server status and information.

### Request
- **Content-Type:** Not required (GET request)
- **Body:** None

### Response
- **200 OK**
  ```json
  {
    "name": "Upskiller Model Server",
    "version": "2.0.0",
    "status": "running"
  }
  ```

### Python Example
```python
import requests

response = requests.get("http://localhost:8000/")
print(response.json())
# Output: {"name": "Upskiller Model Server", "version": "2.0.0", "status": "running"}
```

### TypeScript Example
```typescript
fetch("http://localhost:8000/")
  .then(res => res.json())
  .then(data => console.log(data));
```

---

## `/run`
**POST** `/run`
Runs model inference on an uploaded image and returns prediction results.

### Request
- **Content-Type:** `multipart/form-data`
- **Body:**
  - `file`: The image file (PNG/JPG/JPEG/GIF) to process

### Response
- **200 OK** (Success)
  ```json
  {
    "prediction": [[0.1, 0.2], [0.3, 0.4]],
    "shape": [2, 2],
    "status": "success"
  }
  ```
- **400 Bad Request** (Invalid input)
  ```json
  {
    "error": "No file uploaded"
  }
  ```
  ```json
  {
    "error": "File must be an image"
  }
  ```
- **500 Internal Server Error** (Processing error)
  ```json
  {
    "error": "Prediction failed: <error message>"
  }
  ```

### Response Fields
- `prediction`: 2D array containing the model output values
- `shape`: Dimensions of the prediction array [height, width]
- `status`: "success" for successful predictions

### Python Example
```python
import requests

# Single image prediction
with open("input_image.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/run", files=files)

result = response.json()
if result.get("status") == "success":
    prediction = result["prediction"]
    shape = result["shape"]
    print(f"Prediction shape: {shape}")
    print(f"Prediction values: {prediction[:2]}")  # First 2 rows
else:
    print(f"Error: {result.get('error')}")
```

### Python Example with OpenCV
```python
import cv2
import requests
import numpy as np
from io import BytesIO

# Load and preprocess image
image = cv2.imread("input.jpg")
image = cv2.resize(image, (640, 480))  # Resize to desired input size

# Convert to bytes for upload
_, buffer = cv2.imencode('.jpg', image)
image_bytes = BytesIO(buffer)

# Send prediction request
files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
response = requests.post("http://localhost:8000/run", files=files)

prediction = response.json()
print(f"Model output shape: {prediction.get('shape')}")
print(f"Status: {prediction.get('status')}")
```

### TypeScript Example
```typescript
const formData = new FormData();
const fileInput = document.getElementById('imageFile') as HTMLInputElement;
if (fileInput.files?.[0]) {
  formData.append('file', fileInput.files[0]);
}

fetch("http://localhost:8000/run", {
  method: "POST",
  body: formData
})
  .then(res => res.json())
  .then(data => {
    if (data.status === 'success') {
      console.log('Prediction shape:', data.shape);
      console.log('Prediction data:', data.prediction);
    } else {
      console.error('Error:', data.error);
    }
  })
  .catch(err => console.error('Request failed:', err));
```

### cURL Example
```bash
curl -X POST \
  -F "file=@/path/to/your/image.jpg" \
  http://localhost:8000/run
```

---

## Model Information

### Supported Image Formats
- PNG (.png)
- JPEG (.jpg, .jpeg)
- GIF (.gif)
- Other formats supported by PIL/OpenCV

### Image Processing
- Images are automatically resized and normalized during preprocessing
- No manual preprocessing is required on the client side
- The server handles color space conversion and tensor preparation

### Model Details
- **Architecture**: GLP-based model with encoder-decoder structure
- **Input**: RGB images (automatically preprocessed)
- **Output**: 2D numerical array representing model predictions
- **Batch Size**: Configured for single image inference (batch_size=1)

---

## Error Handling

### Client Errors (4xx)
- **400 Bad Request**: Missing file upload or invalid file format
- **422 Unprocessable Entity**: File processing errors

### Server Errors (5xx)
- **500 Internal Server Error**: Model inference failures, memory issues, or server crashes

### Error Response Format
```json
{
  "error": "Descriptive error message",
  "status": "error"  // May be present
}
```

---

## Usage Notes

- **Server Port**: Default port is 8000 (configurable via `PORT` environment variable)
- **File Upload**: Always use `multipart/form-data` for file uploads
- **Content Types**: Server validates uploaded files are images
- **Model Loading**: Model is loaded on first prediction request (may cause initial delay)
- **Response Format**: All endpoints return JSON responses
- **Logging**: Server provides structured logging for monitoring and debugging

---

## Development & Testing

### Local Development
```bash
# Start the server
python main.py

# Test health check
curl http://localhost:8000/

# Test prediction with sample image
curl -X POST -F "file=@sample.jpg" http://localhost:8000/run
```

### Environment Variables
- `MODEL`: Model checkpoint name (default: "df_default_2.0.0")
- `PORT`: Server port (default: 8000)

---