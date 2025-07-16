import os
from pathlib import Path
import json

class Config:
    def __init__(self, config_dir="./config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self._load_config()

    def _load_config(self):
        """Load configuration from file or create default"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                "text_model": {
                    "name": "bigscience/bloom-petals",
                    "enabled": True
                },
                "image_model": {
                    "name": "runwayml/stable-diffusion-v1-5",
                    "enabled": True
                },
                "ipfs": {
                    "api": "/ip4/127.0.0.1/tcp/5001",
                    "enabled": True
                },
                "server": {
                    "host": "0.0.0.0",
                    "port": 8000,
                    "debug": False
                },
                "security": {
                    "require_wallet": True,
                    "allowed_addresses": []
                }
            }
            self._save_config()

    def _save_config(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get(self, key, default=None):
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value
        self._save_config()

    def update(self, updates):
        """Update multiple configuration values"""
        for key, value in updates.items():
            self.set(key, value)

    @property
    def as_dict(self):
        """Get full configuration as dictionary"""
        return self.config.copy()
