import os
from typing import Optional, Dict
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from .base_deployer import BaseDeployer

class AzureDeployer(BaseDeployer):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.location = config.get("location", "eastus")
        self.vm_size = config.get("vm_size", "Standard_D2s_v3")
        self.resource_group = config.get("resource_group", "petals-resource-group")
        self.subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        
        if not self.subscription_id:
            raise ValueError("AZURE_SUBSCRIPTION_ID environment variable is required")
        
        self.credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(self.credential, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credential, self.subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, self.subscription_id)

    def _create_resource_group(self):
        """Create or update resource group"""
        self.resource_client.resource_groups.create_or_update(
            self.resource_group,
            {"location": self.location}
        )

    def _create_network(self):
        """Create network resources"""
        # Create VNet
        vnet_name = "petals-vnet"
        self.network_client.virtual_networks.begin_create_or_update(
            self.resource_group,
            vnet_name,
            {
                "location": self.location,
                "address_space": {
                    "address_prefixes": ["10.0.0.0/16"]
                }
            }
        ).result()

        # Create Subnet
        subnet_name = "petals-subnet"
        self.network_client.subnets.begin_create_or_update(
            self.resource_group,
            vnet_name,
            subnet_name,
            {"address_prefix": "10.0.0.0/24"}
        ).result()

        # Create Public IP
        public_ip = self.network_client.public_ip_addresses.begin_create_or_update(
            self.resource_group,
            "petals-ip",
            {
                "location": self.location,
                "sku": {"name": "Standard"},
                "public_ip_allocation_method": "Static",
                "public_ip_address_version": "IPV4"
            }
        ).result()

        # Create NIC
        subnet = self.network_client.subnets.get(
            self.resource_group,
            vnet_name,
            subnet_name
        )
        
        nic = self.network_client.network_interfaces.begin_create_or_update(
            self.resource_group,
            "petals-nic",
            {
                "location": self.location,
                "ip_configurations": [{
                    "name": "ipconfig1",
                    "subnet": {"id": subnet.id},
                    "public_ip_address": {"id": public_ip.id}
                }]
            }
        ).result()

        return nic.id

    def deploy(self) -> Optional[str]:
        """Deploy to Azure"""
        try:
            # Create resource group
            self._create_resource_group()

            # Create network resources
            nic_id = self._create_network()

            # VM configuration
            vm_name = "petals-vm"
            vm_parameters = {
                "location": self.location,
                "hardware_profile": {
                    "vm_size": self.vm_size
                },
                "storage_profile": {
                    "image_reference": {
                        "publisher": "Canonical",
                        "offer": "UbuntuServer",
                        "sku": "20.04-LTS",
                        "version": "latest"
                    },
                    "os_disk": {
                        "name": "petals-disk",
                        "caching": "ReadWrite",
                        "create_option": "FromImage",
                        "managed_disk": {
                            "storage_account_type": "Premium_LRS"
                        }
                    }
                },
                "os_profile": {
                    "computer_name": vm_name,
                    "admin_username": "petalsadmin",
                    "linux_configuration": {
                        "disable_password_authentication": True,
                        "ssh": {
                            "public_keys": [{
                                "path": "/home/petalsadmin/.ssh/authorized_keys",
                                "key_data": self.config.get("ssh_public_key", "")
                            }]
                        }
                    },
                    "custom_data": self._get_init_script()
                },
                "network_profile": {
                    "network_interfaces": [{
                        "id": nic_id
                    }]
                }
            }

            # Create VM
            poller = self.compute_client.virtual_machines.begin_create_or_update(
                self.resource_group,
                vm_name,
                vm_parameters
            )
            vm = poller.result()

            print(f"Azure VM created: {vm.name}")
            return vm.name

        except Exception as e:
            print(f"Error deploying to Azure: {str(e)}")
            return None

    def destroy(self, vm_name: str) -> bool:
        """Destroy Azure resources"""
        try:
            # Delete VM
            self.compute_client.virtual_machines.begin_delete(
                self.resource_group,
                vm_name
            ).result()

            # Delete resource group and all resources
            self.resource_client.resource_groups.begin_delete(
                self.resource_group
            ).result()

            print(f"Azure resources deleted for VM: {vm_name}")
            return True

        except Exception as e:
            print(f"Error destroying Azure resources: {str(e)}")
            return False

    def get_status(self, vm_name: str) -> Dict:
        """Get status of Azure deployment"""
        try:
            vm = self.compute_client.virtual_machines.get(
                self.resource_group,
                vm_name,
                expand='instanceView'
            )

            # Get public IP
            nic = self.network_client.network_interfaces.get(
                self.resource_group,
                "petals-nic"
            )
            public_ip_id = nic.ip_configurations[0].public_ip_address.id
            public_ip_name = public_ip_id.split('/')[-1]
            public_ip = self.network_client.public_ip_addresses.get(
                self.resource_group,
                public_ip_name
            )

            return {
                "status": vm.instance_view.statuses[-1].display_status if vm.instance_view.statuses else "Unknown",
                "public_ip": public_ip.ip_address,
                "location": vm.location,
                "vm_size": vm.hardware_profile.vm_size,
                "resource_group": self.resource_group
            }

        except Exception as e:
            print(f"Error getting Azure status: {str(e)}")
            return {"status": "error", "message": str(e)}

    def validate_config(self) -> bool:
        """Validate Azure configuration"""
        required_fields = ["repo_url", "ssh_public_key"]
        return all(field in self.config for field in required_fields)
