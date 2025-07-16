from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3
import json
import os
from pathlib import Path

class WalletManager:
    def __init__(self, config_path="./config"):
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.wallets_file = self.config_path / "wallets.json"
        self.web3 = Web3()
        self._load_wallets()

    def _load_wallets(self):
        """Load registered wallets from file"""
        if self.wallets_file.exists():
            with open(self.wallets_file, 'r') as f:
                self.wallets = json.load(f)
        else:
            self.wallets = {}
            self._save_wallets()

    def _save_wallets(self):
        """Save wallets to file"""
        with open(self.wallets_file, 'w') as f:
            json.dump(self.wallets, f, indent=2)

    def register_instance(self, signature, message, address):
        """Register a new training instance with a wallet signature"""
        # Verify the signature
        message_hash = encode_defunct(text=message)
        recovered_address = self.web3.eth.account.recover_message(message_hash, signature=signature)
        
        if recovered_address.lower() != address.lower():
            raise ValueError("Invalid signature")

        # Generate instance ID
        instance_id = self.web3.keccak(text=f"{address}-{message}").hex()
        
        # Store instance details
        self.wallets[instance_id] = {
            "address": address,
            "registered_at": self.web3.eth.get_block('latest').timestamp,
            "active": True
        }
        self._save_wallets()
        
        return instance_id

    def verify_instance(self, instance_id):
        """Verify if an instance is registered and active"""
        if instance_id not in self.wallets:
            return False
        return self.wallets[instance_id]["active"]

    def deactivate_instance(self, instance_id, signature, address):
        """Deactivate a training instance"""
        if instance_id not in self.wallets:
            raise ValueError("Instance not found")
            
        if self.wallets[instance_id]["address"].lower() != address.lower():
            raise ValueError("Not authorized")
            
        self.wallets[instance_id]["active"] = False
        self._save_wallets()
        
        return True

    def get_instance_info(self, instance_id):
        """Get information about a registered instance"""
        if instance_id not in self.wallets:
            raise ValueError("Instance not found")
        return self.wallets[instance_id]
