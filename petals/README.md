# Petals IPFS Microservice

A decentralized AI service that combines Petals for distributed model inference with IPFS for decentralized storage and wallet-based authentication.

## Features

- Distributed text generation using BLOOM model via Petals
- Image generation using Stable Diffusion
- IPFS integration for decentralized storage
- Wallet-based authentication for training instances
- Configurable deployment using Podman

## Quick Start

1. Install Dependencies:
   - Podman
   - IPFS daemon (running locally)

2. Deploy the Service:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

   Optional parameters:
   - `-p, --port PORT`: Port to expose (default: 8000)
   - `-c, --config DIR`: Config directory (default: ./config)
   - `--cache DIR`: Cache directory (default: ./cache)

3. Register a Wallet:
   ```bash
   curl -X POST http://localhost:8000/wallet/register \
     -H "Content-Type: application/json" \
     -d '{
       "signature": "<your_signature>",
       "message": "<signed_message>",
       "address": "<wallet_address>"
     }'
   ```

4. Use the Service:
   ```bash
   # Generate text with wallet authentication
   curl -X POST http://localhost:8000/generate/text \
     -H "Content-Type: application/json" \
     -H "X-Instance-ID: <your_instance_id>" \
     -d '{
       "prompt": "Once upon a time",
       "max_length": 100,
       "store_on_ipfs": true
     }'
   ```

## Configuration

The service uses a configuration file at `config/config.json`. Example configuration:

```json
{
  "text_model": {
    "name": "bigscience/bloom-petals",
    "enabled": true
  },
  "image_model": {
    "name": "runwayml/stable-diffusion-v1-5",
    "enabled": true
  },
  "ipfs": {
    "api": "/ip4/127.0.0.1/tcp/5001",
    "enabled": true
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8000,
    "debug": false
  },
  "security": {
    "require_wallet": true,
    "allowed_addresses": []
  }
}
```

## API Endpoints

### Wallet Management
- `POST /wallet/register`: Register a new training instance
- `GET /wallet/verify/<instance_id>`: Verify instance status
- `POST /wallet/deactivate/<instance_id>`: Deactivate an instance

### Generation
- `POST /generate/text`: Generate text using BLOOM
- `POST /generate/image`: Generate images using Stable Diffusion

### IPFS
- `POST /ipfs/add`: Add file to IPFS
- `GET /ipfs/get/<hash>`: Retrieve file from IPFS

### Status
- `GET /status`: Get service status
- `GET /peers`: Get connected Petals peers

## Security

The service uses wallet-based authentication for training instances. Each request to protected endpoints must include an `X-Instance-ID` header with a valid instance ID obtained through wallet registration.

## Development

To contribute or modify the service:

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Modify the code as needed
4. Test locally: `python app.py`
5. Build and deploy with podman: `./deploy.sh`

## License

MIT License
