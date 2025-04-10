# Petals-IPFS Microservice

A Python microservice that combines the power of distributed AI (Petals) with decentralized storage (IPFS) to provide text generation, image generation, and content storage capabilities.

## Features

- **Distributed Text Generation**: Connect to the BLOOM peer-to-peer network via Petals to generate text
- **Image Generation**: Generate images using Stable Diffusion
- **IPFS Integration**: Store and retrieve content on the IPFS network
- **RESTful API**: Simple API for interacting with all services

## Prerequisites

- Python 3.8+
- IPFS daemon running locally (or accessible via API)
- GPU recommended for faster image generation

## Installation

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install and run IPFS daemon:
   - Follow the [official IPFS installation guide](https://docs.ipfs.tech/install/command-line/)
   - Start the daemon with `ipfs daemon`

## Running the Service

Start the service with:

```bash
python app.py
```

The service will run on `http://localhost:8000` by default.

## API Endpoints

### Status

- `GET /status` - Get the status of all services (text model, image model, IPFS)
- `GET /peers` - Get information about connected Petals peers

### Text Generation

- `POST /generate/text` - Generate text using the BLOOM model via Petals
  - Parameters:
    - `prompt` (required): The text prompt
    - `max_length` (optional): Maximum length of generated text (default: 100)
    - `temperature` (optional): Sampling temperature (default: 0.7)
    - `store_on_ipfs` (optional): Whether to store the result on IPFS (default: false)

### Image Generation

- `POST /generate/image` - Generate an image using Stable Diffusion
  - Parameters:
    - `prompt` (required): The text prompt
    - `negative_prompt` (optional): Negative prompt for things to avoid
    - `height` (optional): Image height (default: 512)
    - `width` (optional): Image width (default: 512)
    - `num_inference_steps` (optional): Number of diffusion steps (default: 50)
    - `guidance_scale` (optional): Guidance scale (default: 7.5)
    - `store_on_ipfs` (optional): Whether to store the result on IPFS (default: false)

### IPFS Operations

- `POST /ipfs/add` - Add a file to IPFS
  - Parameters:
    - `file` (required): The file to upload
  
- `GET /ipfs/get/<ipfs_hash>` - Retrieve content from IPFS by its hash

## Example Usage

A test script is provided to demonstrate the service's capabilities:

```bash
python test_petals_ipfs.py
```

This script will:
1. Check the service status
2. Generate text using Petals
3. Generate an image using Stable Diffusion
4. Store and retrieve content from IPFS

## How It Works

### Petals Integration

This service connects to the BLOOM peer-to-peer network using Petals, allowing you to run large language models in a distributed fashion. When you send a text generation request:

1. The request is processed by the local Petals client
2. The computation is distributed across multiple peers in the network
3. Results are aggregated and returned to you

This approach allows running models that would be too large for a single consumer device.

### IPFS Integration

All generated content can optionally be stored on IPFS, providing:

1. Content-addressed storage (files are identified by their content, not location)
2. Decentralized storage (content is stored across the IPFS network)
3. Persistent links (IPFS hashes remain valid as long as the content is pinned somewhere)

## Customization

You can customize the service by modifying the following variables in `app.py`:

- `TEXT_MODEL_NAME`: The Petals model to use (default: "bigscience/bloom-petals")
- `IMAGE_MODEL_NAME`: The diffusion model to use (default: "runwayml/stable-diffusion-v1-5")
- `IPFS_API`: The IPFS API endpoint (default: "/ip4/127.0.0.1/tcp/5001")
- `CACHE_DIR`: Directory for temporary files (default: "./cache")

## Limitations

- The first request may take some time as models need to be loaded
- Image generation requires significant GPU resources for reasonable speed
- IPFS functionality requires a running IPFS daemon
- Petals requires active peers in the network for the model you're using

## License

MIT
