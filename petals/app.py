from sanic import Sanic
from sanic.response import json, file
import asyncio
import torch
import os
import ipfshttpclient
import io
import base64
from PIL import Image
import aiofiles
import time
from pathlib import Path

from petals.wallet import WalletManager
from petals.config import Config

# Petals for distributed text generation
from petals import AutoDistributedModelForCausalLM
from transformers import AutoTokenizer

# Diffusers for image generation
from diffusers import StableDiffusionPipeline

app = Sanic("PetalsIPFSMicroservice")

# Load configuration
config = Config()

# Configuration variables
TEXT_MODEL_NAME = config.get("text_model.name", "bigscience/bloom-petals")
IMAGE_MODEL_NAME = config.get("image_model.name", "runwayml/stable-diffusion-v1-5")
IPFS_API = config.get("ipfs.api", "/ip4/127.0.0.1/tcp/5001")
CACHE_DIR = "./cache"

# Global variables
text_model = None
text_tokenizer = None
image_model = None
ipfs_client = None

# Wallet manager instance
wallet_manager = WalletManager()

# Create cache directory if it doesn't exist
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

@app.listener('before_server_start')
async def setup_services(app, loop):
    # Start loading models in background
    app.ctx.text_model_loading = asyncio.create_task(load_text_model())
    app.ctx.image_model_loading = asyncio.create_task(load_image_model())
    app.ctx.ipfs_loading = asyncio.create_task(connect_to_ipfs())
    
    # Wait for IPFS to connect (but don't wait for models to fully load)
    await app.ctx.ipfs_loading

async def load_text_model():
    global text_model, text_tokenizer
    try:
        print("Loading BLOOM model via Petals (this may take a minute)...")
        text_tokenizer = AutoTokenizer.from_pretrained(TEXT_MODEL_NAME)
        text_model = AutoDistributedModelForCausalLM.from_pretrained(TEXT_MODEL_NAME)
        print("Text model loaded successfully!")
    except Exception as e:
        print(f"Error loading text model: {e}")

async def load_image_model():
    global image_model
    try:
        print("Loading Stable Diffusion model (this may take a minute)...")
        # Load in fp16 precision to save memory
        image_model = StableDiffusionPipeline.from_pretrained(
            IMAGE_MODEL_NAME,
            torch_dtype=torch.float16,
            revision="fp16"
        )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            image_model = image_model.to("cuda")
        print("Image model loaded successfully!")
    except Exception as e:
        print(f"Error loading image model: {e}")

async def connect_to_ipfs():
    global ipfs_client
    try:
        print("Connecting to IPFS daemon...")
        ipfs_client = ipfshttpclient.connect(IPFS_API)
        print(f"Connected to IPFS daemon: {ipfs_client.id()['ID']}")
    except Exception as e:
        print(f"Error connecting to IPFS: {e}")
        print("IPFS functionality will be disabled")

@app.route("/hello", methods=["GET"])
async def hello(request):
    return json({"message": "Hello from Petals-IPFS Microservice!"})

@app.route("/status", methods=["GET"])
async def status(request):
    return json({
        "text_model": {
            "name": TEXT_MODEL_NAME,
            "loaded": text_model is not None,
            "peers": len(text_model.get_peers_info()) if text_model else 0
        },
        "image_model": {
            "name": IMAGE_MODEL_NAME,
            "loaded": image_model is not None,
            "device": str(image_model.device) if image_model else None
        },
        "ipfs": {
            "connected": ipfs_client is not None,
            "peer_id": ipfs_client.id()["ID"] if ipfs_client else None
        },
        "wallets": {
            "registered_instances": len(wallet_manager.wallets)
        }
    })

@app.route("/generate/text", methods=["POST"])
async def generate_text(request):
    global text_model, text_tokenizer
    
    # Check if model is loaded
    if text_model is None or text_tokenizer is None:
        return json({"error": "Text model is still loading"}, status=503)
    
    # Wallet check if required
    if config.get("security.require_wallet", True):
        instance_id = request.headers.get("X-Instance-ID")
        if not instance_id or not wallet_manager.verify_instance(instance_id):
            return json({"error": "Unauthorized: Invalid or missing instance ID"}, status=401)
    
    # Get the prompt from the request
    data = request.json
    if not data or "prompt" not in data:
        return json({"error": "Please provide a prompt in the request body"}, status=400)
    
    prompt = data["prompt"]
    max_length = data.get("max_length", 100)
    temperature = data.get("temperature", 0.7)
    store_on_ipfs = data.get("store_on_ipfs", False)
    
    try:
        # Generate text using the BLOOM model
        inputs = text_tokenizer(prompt, return_tensors="pt")
        
        # Move inputs to the same device as the model
        inputs = {k: v.to(text_model.device) for k, v in inputs.items()}
        
        # Generate the response
        with torch.no_grad():
            outputs = text_model.generate(
                **inputs,
                max_length=max_length,
                temperature=temperature,
                do_sample=True,
                pad_token_id=text_tokenizer.eos_token_id
            )
        
        # Decode the generated text
        generated_text = text_tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        response = {
            "prompt": prompt,
            "generated_text": generated_text,
            "model": TEXT_MODEL_NAME
        }
        
        # Store on IPFS if requested and IPFS is connected
        if store_on_ipfs and ipfs_client:
            ipfs_hash = ipfs_client.add_str(generated_text)
            response["ipfs_hash"] = ipfs_hash
            response["ipfs_gateway_url"] = f"https://ipfs.io/ipfs/{ipfs_hash}"
        
        return json(response)
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route("/generate/image", methods=["POST"])
async def generate_image(request):
    global image_model
    
    # Check if model is loaded
    if image_model is None:
        return json({"error": "Image model is still loading"}, status=503)
    
    # Wallet check if required
    if config.get("security.require_wallet", True):
        instance_id = request.headers.get("X-Instance-ID")
        if not instance_id or not wallet_manager.verify_instance(instance_id):
            return json({"error": "Unauthorized: Invalid or missing instance ID"}, status=401)
    
    # Get the prompt from the request
    data = request.json
    if not data or "prompt" not in data:
        return json({"error": "Please provide a prompt in the request body"}, status=400)
    
    prompt = data["prompt"]
    negative_prompt = data.get("negative_prompt", "")
    height = data.get("height", 512)
    width = data.get("width", 512)
    num_inference_steps = data.get("num_inference_steps", 50)
    guidance_scale = data.get("guidance_scale", 7.5)
    store_on_ipfs = data.get("store_on_ipfs", False)
    
    try:
        # Generate image using Stable Diffusion
        with torch.autocast("cuda" if torch.cuda.is_available() else "cpu"):
            image = image_model(
                prompt=prompt,
                negative_prompt=negative_prompt,
                height=height,
                width=width,
                num_inference_steps=num_inference_steps,
                guidance_scale=guidance_scale
            ).images[0]
        
        # Save image to a temporary file
        timestamp = int(time.time())
        image_filename = f"{CACHE_DIR}/image_{timestamp}.png"
        image.save(image_filename)
        
        # Convert image to base64 for JSON response
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        response = {
            "prompt": prompt,
            "model": IMAGE_MODEL_NAME,
            "image_base64": img_str,
            "local_path": image_filename
        }
        
        # Store on IPFS if requested and IPFS is connected
        if store_on_ipfs and ipfs_client:
            with open(image_filename, "rb") as f:
                ipfs_result = ipfs_client.add(image_filename)
                ipfs_hash = ipfs_result["Hash"]
                response["ipfs_hash"] = ipfs_hash
                response["ipfs_gateway_url"] = f"https://ipfs.io/ipfs/{ipfs_hash}"
        
        return json(response)
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route("/ipfs/add", methods=["POST"])
async def add_to_ipfs(request):
    # Check if IPFS is connected
    if ipfs_client is None:
        return json({"error": "IPFS is not connected"}, status=503)
    
    # Check if file is in request
    if not request.files:
        return json({"error": "No file provided"}, status=400)
    
    try:
        # Get the file from the request
        file = request.files.get("file")
        if not file:
            return json({"error": "No file provided under 'file' key"}, status=400)
        
        # Save file to temporary location
        file_path = f"{CACHE_DIR}/{file.name}"
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file.body)
        
        # Add file to IPFS
        ipfs_result = ipfs_client.add(file_path)
        ipfs_hash = ipfs_result["Hash"]
        
        return json({
            "filename": file.name,
            "ipfs_hash": ipfs_hash,
            "ipfs_gateway_url": f"https://ipfs.io/ipfs/{ipfs_hash}"
        })
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route("/ipfs/get/<ipfs_hash>", methods=["GET"])
async def get_from_ipfs(request, ipfs_hash):
    # Check if IPFS is connected
    if ipfs_client is None:
        return json({"error": "IPFS is not connected"}, status=503)
    
    try:
        # Get file from IPFS
        content = ipfs_client.cat(ipfs_hash)
        
        # Determine if it's text or binary
        try:
            # Try to decode as text
            text_content = content.decode("utf-8")
            return json({"content": text_content, "type": "text"})
        except UnicodeDecodeError:
            # It's binary data (like an image)
            file_path = f"{CACHE_DIR}/{ipfs_hash}"
            with open(file_path, "wb") as f:
                f.write(content)
            
            return await file(file_path)
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route("/peers", methods=["GET"])
async def get_peers(request):
    if text_model is None:
        return json({"error": "Text model is not loaded yet"}, status=503)
    
    try:
        peers_info = text_model.get_peers_info()
        return json({
            "model_name": TEXT_MODEL_NAME,
            "peers_count": len(peers_info),
            "peers": peers_info
        })
    except Exception as e:
        return json({"error": str(e)}, status=500)

@app.route("/wallet/register", methods=["POST"])
async def register_wallet(request):
    """
    Register a new training instance with wallet signature verification.
    Expected JSON body:
    {
        "signature": "<signature>",
        "message": "<message>",
        "address": "<wallet_address>"
    }
    """
    data = request.json
    if not data:
        return json({"error": "Missing JSON body"}, status=400)
    
    signature = data.get("signature")
    message = data.get("message")
    address = data.get("address")
    
    if not signature or not message or not address:
        return json({"error": "Missing required fields"}, status=400)
    
    try:
        instance_id = wallet_manager.register_instance(signature, message, address)
        return json({"instance_id": instance_id, "message": "Wallet registered successfully"})
    except Exception as e:
        return json({"error": str(e)}, status=400)

@app.route("/wallet/verify/<instance_id>", methods=["GET"])
async def verify_wallet(request, instance_id):
    """Verify if a training instance is registered and active"""
    try:
        active = wallet_manager.verify_instance(instance_id)
        return json({"instance_id": instance_id, "active": active})
    except Exception as e:
        return json({"error": str(e)}, status=400)

@app.route("/wallet/deactivate/<instance_id>", methods=["POST"])
async def deactivate_wallet(request, instance_id):
    """
    Deactivate a training instance.
    Expected JSON body:
    {
        "signature": "<signature>",
        "address": "<wallet_address>"
    }
    """
    data = request.json
    if not data:
        return json({"error": "Missing JSON body"}, status=400)
    
    signature = data.get("signature")
    address = data.get("address")
    
    if not signature or not address:
        return json({"error": "Missing required fields"}, status=400)
    
    try:
        result = wallet_manager.deactivate_instance(instance_id, signature, address)
        return json({"instance_id": instance_id, "deactivated": result})
    except Exception as e:
        return json({"error": str(e)}, status=400)

if __name__ == "__main__":
    app.run(host=config.get("server.host", "0.0.0.0"), port=config.get("server.port", 8000), debug=config.get("server.debug", False))
