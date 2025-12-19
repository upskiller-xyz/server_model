# Upskiller Model Server

Production-ready Flask server for PyTorch model inference supporting multiple formats: **ONNX** and **TorchScript**.

## 🎯 Overview

This server provides REST API endpoints for running inference on PyTorch models in multiple formats. It's designed for production deployment with:

- **Multiple model formats**:
  - **ONNX** - Cross-platform inference with ONNX Runtime
  - **TorchScript** - Native PyTorch optimized format

## 🚀 Quick Start

### Local Development

```bash
# 1. Set up environment
eval "$(micromamba shell hook --shell bash)"
micromamba activate upskiller
pip install -r requirements.txt

# 2. Set model configuration - Optional
export MODEL=df_default_2.0.1 

# 3. Run server
python main.py
```

Server runs on `http://localhost:8000`

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# Or with specific model
MODEL=your_model docker-compose up -d

# With GPU support
docker-compose --profile gpu up -d
```

## 📡 API Endpoints

### Health Check
```bash
GET /
```

**Response:**
```json
{
  "status": "ready",
  "model_status": "READY"
}
```

### Run Prediction
```bash
POST /run
Content-Type: multipart/form-data
```

**Request:**
```bash
curl -X POST http://localhost:8000/run \
  -F "file=@image.jpg"
```

**Response:**
```json
{
  "simulation": [[...]],
  "shape": [384, 384],
  "status": "success"
}
```

## 🏗️ Architecture

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL` | `df_default_2.0.1` | Model name to load |
| `MODEL_FORMAT` | `onnx` | Model format: `onnx`, `torchscript`|
| `PORT` | `8000` | Server port |

### Model Configuration

Models are automatically downloaded from Scaleway:
```
https://daylight-factor.s3.fr-par.scw.cloud/models/{MODEL}.{extension}
```

Local cache: `./checkpoints/{MODEL}.{extension}`

Supported formats:
- **ONNX** (`.onnx`) 
- **TorchScript** (`.pt`) 

### Image Processing

- **Input size**: 384x384 
- **Normalization**: ImageNet standard
  - Mean: `[0.485, 0.456, 0.406]`
  - Std: `[0.229, 0.224, 0.225]`

## 🐳 Docker

### Build Image

```bash
docker build -t upskiller-model-server .
```

### Run Container

```bash
docker run -p 8000:8000 \
  -e MODEL=df_default_2.0.1 \
  -v $(pwd)/checkpoints:/app/checkpoints \
  upskiller-model-server
```

### Docker Compose

```bash
# Start server
docker-compose up -d

# View logs
docker-compose logs -f

# Stop server
docker-compose down
```
