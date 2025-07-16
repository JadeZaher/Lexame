#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from src.cloud import CloudManager

def parse_args():
    parser = argparse.ArgumentParser(description="Deploy Petals service to cloud providers")
    
    # Main arguments
    parser.add_argument("action", choices=["deploy", "destroy", "status", "logs"],
                       help="Action to perform")
    parser.add_argument("provider", choices=["aws", "gcp", "azure"],
                       help="Cloud provider to use")
    
    # Optional arguments
    parser.add_argument("--resource-id",
                       help="Resource ID for destroy/status/logs actions")
    parser.add_argument("--config", default="./config/cloud.json",
                       help="Path to cloud configuration file")
    parser.add_argument("--config-override",
                       help="JSON string to override configuration")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    try:
        # Initialize cloud manager
        cloud_manager = CloudManager(args.config)
        
        # Parse configuration override if provided
        config_override = None
        if args.config_override:
            try:
                config_override = json.loads(args.config_override)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in config override")
                sys.exit(1)
        
        # Execute requested action
        if args.action == "deploy":
            resource_id = cloud_manager.deploy(args.provider, config_override)
            if resource_id:
                print(f"Successfully deployed to {args.provider}")
                print(f"Resource ID: {resource_id}")
                # Get and display initial status
                status = cloud_manager.get_status(args.provider, resource_id, config_override)
                print("\nInitial Status:")
                print(json.dumps(status, indent=2))
            else:
                print(f"Failed to deploy to {args.provider}")
                sys.exit(1)
                
        elif args.action in ["destroy", "status", "logs"]:
            if not args.resource_id:
                print(f"Error: --resource-id is required for {args.action} action")
                sys.exit(1)
                
            if args.action == "destroy":
                success = cloud_manager.destroy(args.provider, args.resource_id, config_override)
                if success:
                    print(f"Successfully destroyed resources on {args.provider}")
                else:
                    print(f"Failed to destroy resources on {args.provider}")
                    sys.exit(1)
                    
            elif args.action == "status":
                status = cloud_manager.get_status(args.provider, args.resource_id, config_override)
                print(json.dumps(status, indent=2))
                
            elif args.action == "logs":
                logs = cloud_manager.get_logs(args.provider, args.resource_id, config_override)
                print(logs)
                
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
