from typing import Dict, Optional
from .base_deployer import BaseDeployer
from .aws_deployer import AWSDeployer
from .gcp_deployer import GCPDeployer
from .azure_deployer import AzureDeployer

class CloudDeployerFactory:
    """Factory class for creating cloud deployers"""
    
    @staticmethod
    def create_deployer(provider: str, config: Dict) -> Optional[BaseDeployer]:
        """
        Create a cloud deployer instance based on the provider
        
        Args:
            provider: Cloud provider name ('aws', 'gcp', or 'azure')
            config: Configuration dictionary for the deployer
            
        Returns:
            BaseDeployer instance or None if provider is not supported
        """
        deployers = {
            'aws': AWSDeployer,
            'gcp': GCPDeployer,
            'azure': AzureDeployer
        }
        
        deployer_class = deployers.get(provider.lower())
        if not deployer_class:
            raise ValueError(f"Unsupported cloud provider: {provider}")
            
        deployer = deployer_class(config)
        if not deployer.validate_config():
            raise ValueError(f"Invalid configuration for {provider}")
            
        return deployer

class CloudManager:
    """Main interface for cloud deployment operations"""
    
    def __init__(self, config_path: str = "./config/cloud.json"):
        """
        Initialize CloudManager
        
        Args:
            config_path: Path to cloud configuration file
        """
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file"""
        import json
        from pathlib import Path
        
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {}
        
    def deploy(self, provider: str, config_override: Dict = None) -> Optional[str]:
        """
        Deploy service to specified cloud provider
        
        Args:
            provider: Cloud provider name
            config_override: Optional configuration override
            
        Returns:
            Resource ID if successful, None otherwise
        """
        # Merge configuration
        config = self.config.get(provider, {})
        if config_override:
            config.update(config_override)
            
        # Create and validate deployer
        deployer = CloudDeployerFactory.create_deployer(provider, config)
        
        # Deploy
        return deployer.deploy()
        
    def destroy(self, provider: str, resource_id: str, config_override: Dict = None) -> bool:
        """
        Destroy deployed resources
        
        Args:
            provider: Cloud provider name
            resource_id: ID of the resource to destroy
            config_override: Optional configuration override
            
        Returns:
            True if successful, False otherwise
        """
        config = self.config.get(provider, {})
        if config_override:
            config.update(config_override)
            
        deployer = CloudDeployerFactory.create_deployer(provider, config)
        return deployer.destroy(resource_id)
        
    def get_status(self, provider: str, resource_id: str, config_override: Dict = None) -> Dict:
        """
        Get status of deployed resources
        
        Args:
            provider: Cloud provider name
            resource_id: ID of the resource to check
            config_override: Optional configuration override
            
        Returns:
            Dictionary containing status information
        """
        config = self.config.get(provider, {})
        if config_override:
            config.update(config_override)
            
        deployer = CloudDeployerFactory.create_deployer(provider, config)
        return deployer.get_status(resource_id)
        
    def get_logs(self, provider: str, resource_id: str, config_override: Dict = None) -> str:
        """
        Get logs from deployed service
        
        Args:
            provider: Cloud provider name
            resource_id: ID of the resource
            config_override: Optional configuration override
            
        Returns:
            Log content as string
        """
        config = self.config.get(provider, {})
        if config_override:
            config.update(config_override)
            
        deployer = CloudDeployerFactory.create_deployer(provider, config)
        return deployer.get_logs(resource_id)
