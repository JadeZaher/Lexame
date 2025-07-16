import requests
import json
import time
import base64
from PIL import Image
import io
import os

# Configuration
BASE_URL = "http://localhost:8000"
CACHE_DIR = "./test_results"

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)

def check_service_status():
    """Check if the service is running and what components are available"""
    response = requests.get(f"{BASE_URL}/status")
    if response.status_code == 200:
        status = response.json()
        print("\n=== Service Status ===")
        print(f"Text Model: {status['text_model']['name']}")
        print(f"  - Loaded: {status['text_model']['loaded']}")
        print(f"  - Connected Peers: {status['text_model']['peers']}")
        print(f"Image Model: {status['image_model']['name']}")
        print(f"  - Loaded: {status['image_model']['loaded']}")
        print(f"  - Device: {status['image_model']['device']}")
        print(f"IPFS Connected: {status['ipfs']['connected']}")
        if status['ipfs']['connected']:
            print(f"  - Peer ID: {status['ipfs']['peer_id']}")
        return status
    else:
        print(f"Error checking status: {response.status_code}")
        print(response.text)
        return None

def generate_text(prompt, max_length=100, temperature=0.7, store_on_ipfs=True):
    """Generate text using the Petals distributed model"""
    print(f"\n=== Generating Text ===")
    print(f"Prompt: {prompt}")
    
    payload = {
        "prompt": prompt,
        "max_length": max_length,
        "temperature": temperature,
        "store_on_ipfs": store_on_ipfs
    }
    
    response = requests.post(f"{BASE_URL}/generate/text", json=payload)
    if response.status_code == 200:
        result = response.json()
        print("\nGenerated Text:")
        print(result["generated_text"])
        
        if "ipfs_hash" in result:
            print(f"\nStored on IPFS:")
            print(f"  - Hash: {result['ipfs_hash']}")
            print(f"  - Gateway URL: {result['ipfs_gateway_url']}")
        
        return result
    else:
        print(f"Error generating text: {response.status_code}")
        print(response.text)
        return None

def generate_image(prompt, negative_prompt="", width=512, height=512, 
                  steps=30, guidance_scale=7.5, store_on_ipfs=True):
    """Generate an image using Stable Diffusion"""
    print(f"\n=== Generating Image ===")
    print(f"Prompt: {prompt}")
    
    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "num_inference_steps": steps,
        "guidance_scale": guidance_scale,
        "store_on_ipfs": store_on_ipfs
    }
    
    response = requests.post(f"{BASE_URL}/generate/image", json=payload)
    if response.status_code == 200:
        result = response.json()
        
        # Save the image
        image_data = base64.b64decode(result["image_base64"])
        image = Image.open(io.BytesIO(image_data))
        
        # Create a filename based on the prompt
        safe_prompt = "".join(x for x in prompt[:30] if x.isalnum() or x in " _-").strip()
        safe_prompt = safe_prompt.replace(" ", "_")
        filename = f"{CACHE_DIR}/{safe_prompt}_{int(time.time())}.png"
        image.save(filename)
        
        print(f"Image saved to: {filename}")
        
        if "ipfs_hash" in result:
            print(f"\nStored on IPFS:")
            print(f"  - Hash: {result['ipfs_hash']}")
            print(f"  - Gateway URL: {result['ipfs_gateway_url']}")
        
        return result, filename
    else:
        print(f"Error generating image: {response.status_code}")
        print(response.text)
        return None, None

def get_from_ipfs(ipfs_hash):
    """Retrieve content from IPFS"""
    print(f"\n=== Retrieving from IPFS ===")
    print(f"IPFS Hash: {ipfs_hash}")
    
    response = requests.get(f"{BASE_URL}/ipfs/get/{ipfs_hash}")
    if response.status_code == 200:
        # Check if it's JSON (text) or binary (image)
        content_type = response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            result = response.json()
            print(f"Retrieved text content:")
            print(result["content"])
            return result
        else:
            # It's binary data (likely an image)
            filename = f"{CACHE_DIR}/retrieved_{ipfs_hash}.png"
            with open(filename, "wb") as f:
                f.write(response.content)
            print(f"Retrieved binary content saved to: {filename}")
            return filename
    else:
        print(f"Error retrieving from IPFS: {response.status_code}")
        print(response.text)
        return None

def get_peers_info():
    """Get information about connected Petals peers"""
    print(f"\n=== Petals Network Peers ===")
    
    response = requests.get(f"{BASE_URL}/peers")
    if response.status_code == 200:
        result = response.json()
        print(f"Connected to {result['peers_count']} peers for {result['model_name']}")
        for i, peer in enumerate(result['peers']):
            print(f"Peer {i+1}: {peer}")
        return result
    else:
        print(f"Error getting peers info: {response.status_code}")
        print(response.text)
        return None

def main():
    """Run a demonstration of the Petals-IPFS service"""
    print("=== Petals-IPFS Service Demo ===")
    
    # Check service status
    status = check_service_status()
    if not status:
        print("Service is not available. Make sure it's running.")
        return
    
    # Wait for models to load if needed
    if not status["text_model"]["loaded"] or not status["image_model"]["loaded"]:
        print("\nWaiting for models to load (this may take a few minutes)...")
        for _ in range(10):
            time.sleep(30)  # Check every 30 seconds
            status = check_service_status()
            if status["text_model"]["loaded"] and status["image_model"]["loaded"]:
                print("All models loaded!")
                break
    
    # Get information about Petals peers
    peers_info = get_peers_info()
    
    # Generate text with Petals
    text_result = generate_text(
        prompt="The future of artificial intelligence is",
        max_length=150,
        temperature=0.8,
        store_on_ipfs=True
    )
    
    # Generate an image with Stable Diffusion
    image_result, image_path = generate_image(
        prompt="A futuristic city with flying cars and holographic displays",
        negative_prompt="blurry, low quality",
        width=512,
        height=512,
        steps=30,
        store_on_ipfs=True
    )
    
    # Retrieve content from IPFS
    if text_result and "ipfs_hash" in text_result:
        retrieved_text = get_from_ipfs(text_result["ipfs_hash"])
    
    if image_result and "ipfs_hash" in image_result:
        retrieved_image = get_from_ipfs(image_result["ipfs_hash"])
    
    print("\n=== Demo Complete ===")
    print("You've successfully tested the Petals-IPFS service!")

if __name__ == "__main__":
    main()
