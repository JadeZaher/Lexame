from typing import Optional, Dict
from google.cloud import compute_v1
from .base_deployer import BaseDeployer

class GCPDeployer(BaseDeployer):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.project_id = config.get("project_id")
        self.zone = config.get("zone", "us-central1-a")
        self.machine_type = config.get("machine_type", "n1-standard-2")
        self.instance_client = compute_v1.InstancesClient()
        self.operation_client = compute_v1.ZoneOperationsClient()

    def deploy(self) -> Optional[str]:
        """Deploy to Google Cloud Platform"""
        try:
            if not self.project_id:
                raise ValueError("GCP project_id is required")

            # Create instance configuration
            instance = compute_v1.Instance()
            instance.name = "petals-instance"
            instance.machine_type = f"zones/{self.zone}/machineTypes/{self.machine_type}"

            # Configure the boot disk
            disk = compute_v1.AttachedDisk()
            disk.boot = True
            disk.auto_delete = True
            initialize_params = compute_v1.AttachedDiskInitializeParams()
            initialize_params.source_image = "projects/ubuntu-os-cloud/global/images/ubuntu-2004-focal-v20220204"
            disk.initialize_params = initialize_params
            instance.disks = [disk]

            # Configure networking
            network_interface = compute_v1.NetworkInterface()
            network_interface.network = "global/networks/default"
            access_config = compute_v1.AccessConfig()
            access_config.name = "External NAT"
            access_config.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT
            network_interface.access_configs = [access_config]
            instance.network_interfaces = [network_interface]

            # Add startup script
            metadata = compute_v1.Metadata()
            metadata.items = [
                compute_v1.Items(
                    key="startup-script",
                    value=self._get_init_script()
                )
            ]
            instance.metadata = metadata

            # Create the instance
            operation = self.instance_client.insert(
                project=self.project_id,
                zone=self.zone,
                instance_resource=instance
            )

            # Wait for the operation to complete
            self.operation_client.wait(
                project=self.project_id,
                zone=self.zone,
                operation=operation.name
            )

            print(f"GCP Instance created: {instance.name}")
            return instance.name

        except Exception as e:
            print(f"Error deploying to GCP: {str(e)}")
            return None

    def destroy(self, instance_name: str) -> bool:
        """Destroy GCP resources"""
        try:
            operation = self.instance_client.delete(
                project=self.project_id,
                zone=self.zone,
                instance=instance_name
            )

            # Wait for the operation to complete
            self.operation_client.wait(
                project=self.project_id,
                zone=self.zone,
                operation=operation.name
            )

            print(f"GCP Instance deleted: {instance_name}")
            return True

        except Exception as e:
            print(f"Error destroying GCP resources: {str(e)}")
            return False

    def get_status(self, instance_name: str) -> Dict:
        """Get status of GCP deployment"""
        try:
            instance = self.instance_client.get(
                project=self.project_id,
                zone=self.zone,
                instance=instance_name
            )

            network_interface = instance.network_interfaces[0]
            public_ip = network_interface.access_configs[0].nat_ip if network_interface.access_configs else None

            return {
                "status": instance.status,
                "public_ip": public_ip,
                "creation_timestamp": instance.creation_timestamp,
                "machine_type": instance.machine_type,
                "zone": instance.zone
            }

        except Exception as e:
            print(f"Error getting GCP status: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_logs(self, instance_name: str) -> str:
        """Get logs from GCP instance"""
        try:
            # Get serial port output
            output = self.instance_client.get_serial_port_output(
                project=self.project_id,
                zone=self.zone,
                instance=instance_name
            )
            return output.contents

        except Exception as e:
            print(f"Error getting GCP logs: {str(e)}")
            return f"Error retrieving logs: {str(e)}"

    def validate_config(self) -> bool:
        """Validate GCP configuration"""
        required_fields = ["project_id", "repo_url"]
        return all(field in self.config for field in required_fields)
