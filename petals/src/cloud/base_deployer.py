from abc import ABC, abstractmethod
from typing import Optional, Dict

class BaseDeployer(ABC):
    def __init__(self, config: Dict):
        self.config = config

    @abstractmethod
    def deploy(self) -> Optional[str]:
        """Deploy the service to cloud provider"""
        pass

    @abstractmethod
    def destroy(self, resource_id: str) -> bool:
        """Destroy deployed resources"""
        pass

    @abstractmethod
    def get_status(self, resource_id: str) -> Dict:
        """Get status of deployed resources"""
        pass

    def _get_init_script(self) -> str:
        """Get initialization script for cloud instances"""
        return '''#!/bin/bash
# Install system dependencies
apt-get update
apt-get install -y podman git

# Clone repository
git clone {repo_url} /opt/petals
cd /opt/petals

# Setup configuration
mkdir -p config
cat > config/config.json << 'EOF'
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
EOF

# Make deploy script executable and run
chmod +x deploy.sh
./deploy.sh
'''.format(repo_url=self.config.get("repo_url", "https://github.com/yourusername/petals.git"))

    def validate_config(self) -> bool:
        """Validate configuration"""
        required_fields = ["repo_url"]
        return all(field in self.config for field in required_fields)

    def get_logs(self, resource_id: str) -> str:
        """Get logs from deployed service"""
        raise NotImplementedError("Log retrieval not implemented for this provider")

    def restart(self, resource_id: str) -> bool:
        """Restart deployed service"""
        raise NotImplementedError("Restart not implemented for this provider")

    def update(self, resource_id: str) -> bool:
        """Update deployed service"""
        raise NotImplementedError("Update not implemented for this provider")
