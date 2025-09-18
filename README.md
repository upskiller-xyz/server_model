<a name="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/upskiller-xyz/model_server">
    <img src="https://github.com/upskiller-xyz/DaylightFactor/blob/main/docs/images/logo_upskiller.png" alt="Logo" height="100" >
  </a>

  <h3 align="center">Model Server</h3>

  <p align="center">
    Deep learning model serving infrastructure with PyTorch and Flask. Provides REST API endpoints for image processing and ML model predictions.
    <br />
    <a href="https://github.com/upskiller-xyz/model_server">View Demo</a>
    ·
    <a href="https://github.com/upskiller-xyz/model_server/issues">Report Bug</a>
    ·
    <a href="https://github.com/upskiller-xyz/model_server/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a>
        <li><a href="#api-endpoints">API Endpoints</a></li>
        <li><a href="#deployment">Deployment</a>
          <li><a href="#locally">Local deployment</a></li>
        </li>
    </li>
    <li><a href="#design">Design</a>
      <li><a href="#architecture">Architecture</a></li>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contribution">Contribution</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#attribution">Attribution</a></li>
    <li><a href="#trademark-notice">Trademark notice</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

The Model Server provides a scalable REST API infrastructure for serving deep learning models built with PyTorch. It implements object-oriented design patterns and provides efficient image processing and prediction capabilities.

**Key Features:**
- **Object-Oriented Architecture**: Clean separation of concerns with dependency injection
- **Model Loading**: Automatic checkpoint downloading and loading with caching
- **Image Processing**: Standardized image preprocessing pipeline
- **Prediction Service**: Efficient batch processing with configurable batch sizes
- **Structured Logging**: Comprehensive logging with different severity levels
- **Flask Integration**: RESTful API endpoints with proper error handling


<p align="right">(<a href="#readme-top">back to top</a>)</p>



### Built With

* [Python](https://www.python.org/)
* [PyTorch](https://pytorch.org/)
* [Flask](https://flask.palletsprojects.com/)
* [Poetry](https://python-poetry.org/)
* [OpenCV](https://opencv.org/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

* [Python 3.13+](https://www.python.org/downloads/)
* [Poetry](https://python-poetry.org/docs/#installation)
* CUDA-capable GPU (optional, for GPU acceleration)

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/upskiller-xyz/model_server.git
   cd model_server
   ```

2. Install dependencies using Poetry:
   ```sh
   poetry install
   ```

3. Activate the virtual environment:
   ```sh
   poetry shell
   ```

4. Set environment variables (optional):
   ```sh
   export MODEL=df_default_2.0.0  # Model name
   export PORT=8000               # Server port
   ```

5. Run the server:
   ```sh
   python main.py
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- USAGE EXAMPLES -->
## Usage

### 🎯 Interactive Demo with PyTorch Models

**Start here!** For hands-on examples with PyTorch model loading and feature extraction, see the **[Playground Notebook](example/demo.ipynb)**:

```bash
# Install Jupyter and start the demo
poetry run jupyter notebook example/demo.ipynb
```

### 🔧 API Endpoints

The server provides REST API endpoints for model predictions:

#### Health Check
Check if the server is running and model is loaded:

```python
import requests

response = requests.get("http://localhost:8000/")
print(response.json())
# Output: {"status": "ready", "model_loaded": true, "timestamp": "2024-01-01T00:00:00Z"}
```

#### Image Prediction
Submit an image for model prediction:

```python
import requests

# Send image file for prediction
with open("input_image.jpg", "rb") as f:
    files = {"file": f}
    response = requests.post("http://localhost:8000/run", files=files)

result = response.json()
print(f"Prediction result: {result}")
```

#### Example with OpenCV preprocessing:

```python
import cv2
import requests
import numpy as np
from io import BytesIO

# Load and preprocess image
image = cv2.imread("input.jpg")
image = cv2.resize(image, (480, 640))  # Resize to model input size

# Convert to bytes
_, buffer = cv2.imencode('.jpg', image)
image_bytes = BytesIO(buffer)

# Send prediction request
files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
response = requests.post("http://localhost:8000/run", files=files)

prediction = response.json()
print(f"Model output shape: {prediction.get('output_shape')}")
print(f"Processing time: {prediction.get('processing_time_ms')}ms")
```

### Deployment

#### Environment Configuration
Create a `.env` file with required configurations:
```sh
MODEL=df_default_2.0.0
PORT=8000
GCP_REGION=us-central1
SERVER_NAME=model-server
REPO_NAME=model_server
IMAGE_NAME=model-server

SCW_REGISTRY_NAMESPACE=nsp
SCW_PROJECT_ID=project-id
SCW_SERVER=serve-container
SCW_IMAGE=model_server
```

#### Docker Deployment
Build and run using Docker:
```sh
docker build -t model-server .
docker run -p 8000:8000 model-server
```

#### Cloud Deployment
Deploy to Google Cloud Platform:
```sh
gcloud auth login
bash build.sh
```

or Scaleway:
```sh
bash build_scw.sh
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

#### Locally

Set up the Model Server locally for development and testing:

1. **Clone the Repository**
   ```bash
   git clone <your-repo-url>
   cd model_server
   ```

2. **Install Dependencies with Poetry**
   ```bash
   poetry install
   ```

3. **Activate Virtual Environment**
   ```bash
   poetry shell
   ```

4. **Set Environment Variables (Optional)**
   ```bash
   export MODEL=df_default_2.0.0
   export PORT=8000
   ```

5. **Run the Server**
   ```bash
   python main.py
   ```
   The server will start on `http://localhost:8000` by default.

6. **Run Tests**
   ```bash
   poetry run pytest
   ```

7. **Code Quality Checks**
   ```bash
   poetry run ruff check .
   poetry run mypy .
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- DESIGN -->
## Design

### Architecture

The Model Server follows object-oriented design principles with clean separation of concerns:

```
ModelServerApplication
├── ModelServerController (handles requests)
├── PredictionService (manages predictions)
├── ModelLoader (loads and manages models)
├── ImageProcessor (preprocesses images)
├── DownloadStrategy (handles model downloads)
└── StructuredLogger (logging system)
```

**Key Components:**
- **Dependency Injection**: All services are injected through constructors
- **Factory Patterns**: Services are created using factory classes
- **Strategy Pattern**: Different loading and processing strategies
- **Single Responsibility**: Each class has one clear purpose
- **Abstract Base Classes**: Define contracts for implementations

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/upskiller-xyz/model_server/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTION -->
## Contribution

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

**Development Guidelines:**

* Follow Object-Oriented Programming principles and design patterns
* Use [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/)
* Follow [semantic versioning](https://semver.org/)
* Add type hints and documentation
* Write tests for new functionality
* Run `poetry run ruff check` and `poetry run mypy` before committing

See [CLAUDE.md](CLAUDE.md) for detailed development instructions.

### Top contributors:

<a href="https://github.com/upskiller-xyz/model_server/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=upskiller-xyz/model_server" alt="Top Contributors" />
</a>

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- LICENSE -->
## License

See [License](./docs/LICENSE) for more details - or [read a summary](https://choosealicense.com/licenses/gpl-3.0/).

In short:

Strong copyleft. You **can** use, distribute and modify this code in both academic and commercial contexts. At the same time you **have to** keep the code open-source under the same license (`GPL-3.0`) and give the appropriate [attribution](#attribution) to the authors.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


## Attribution

📖 **Academic/Industry Use**: Please cite this work as described in [CITATION.cff](docs/citation/CITATION.cff), [CITE.txt](docs/citation/CITE.txt) or [ATTRIBUTION.md](docs/citation/ATTRIBUTION.md). Alternatively you can download the BibTeX file [here](docs/citation/model-server.bib) by adding it to `.tex` files by

```tex
\bibliography{model-server}
```
<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Trademark Notice

- **"Upskiller"** is an informal collaborative name used by contributors affiliated with BIMTech Innovations AB.
- BIMTech Innovations AB owns all legal rights to the **Model Server** project.
- The GPL-3.0 license applies to code, not branding. Commercial use of the names requires permission.

Contact: [Upskiller](mailto:info@upskiller.xyz)

## Contact

Stanislava Fedorova - [e-mail](mailto:stasya.fedorova@gmail.com)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* [README template](https://github.com/othneildrew/Best-README-Template)
* [PyTorch](https://pytorch.org/) - Deep learning framework
* [Flask](https://flask.palletsprojects.com/) - Web framework
* Alberto Floris - [e-mail](mailto:alberto.floris@arkion.co)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/upskiller-xyz/model_server.svg?style=for-the-badge
[contributors-url]: https://github.com/upskiller-xyz/model_server/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/upskiller-xyz/model_server.svg?style=for-the-badge
[forks-url]: https://github.com/upskiller-xyz/model_server/network/members
[stars-shield]: https://img.shields.io/github/stars/upskiller-xyz/model_server.svg?style=for-the-badge
[stars-url]: https://github.com/upskiller-xyz/model_server/stargazers
[issues-shield]: https://img.shields.io/github/issues/upskiller-xyz/model_server.svg?style=for-the-badge
[issues-url]: https://github.com/upskiller-xyz/model_server/issues
[license-shield]: https://img.shields.io/github/license/upskiller-xyz/model_server.svg?style=for-the-badge
[license-url]: https://github.com/upskiller-xyz/model_server/blob/master/docs/LICENSE.txt