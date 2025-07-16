import boto3
from typing import Optional, Dict
from .base_deployer import BaseDeployer

class AWSDeployer(BaseDeployer):
    def __init__(self, config: Dict):
        super().__init__(config)
        self.region = config.get("region", "us-east-1")
        self.instance_type = config.get("instance_type", "t3.large")
        self.ami_id = config.get("ami_id", "ami-0c55b159cbfafe1f0")
        self.ec2 = boto3.client('ec2', region_name=self.region)

    def deploy(self) -> Optional[str]:
        """Deploy to AWS EC2"""
        try:
            # Create security group
            sg_response = self.ec2.create_security_group(
                GroupName='petals-security-group',
                Description='Security group for Petals service'
            )
            sg_id = sg_response['GroupId']
            
            # Add inbound rules
            self.ec2.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 8000,
                        'ToPort': 8000,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            
            # Create user data script
            user_data = self._get_init_script()
            
            # Launch instance
            response = self.ec2.run_instances(
                ImageId=self.ami_id,
                InstanceType=self.instance_type,
                MinCount=1,
                MaxCount=1,
                SecurityGroupIds=[sg_id],
                UserData=user_data
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            print(f"AWS Instance launched: {instance_id}")
            return instance_id
            
        except Exception as e:
            print(f"Error deploying to AWS: {str(e)}")
            return None

    def destroy(self, instance_id: str) -> bool:
        """Destroy AWS resources"""
        try:
            self.ec2.terminate_instances(InstanceIds=[instance_id])
            print(f"AWS Instance terminated: {instance_id}")
            return True
        except Exception as e:
            print(f"Error destroying AWS resources: {str(e)}")
            return False

    def get_status(self, instance_id: str) -> Dict:
        """Get status of AWS deployment"""
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            return {
                "status": instance['State']['Name'],
                "public_ip": instance.get('PublicIpAddress'),
                "launch_time": instance['LaunchTime'].isoformat()
            }
        except Exception as e:
            print(f"Error getting AWS status: {str(e)}")
            return {"status": "error", "message": str(e)}
