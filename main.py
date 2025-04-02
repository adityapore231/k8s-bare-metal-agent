import os
import argparse
import json
from typing import Dict, Any

from k8s_manager import K8sClusterManager

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Kubernetes Cluster Manager')
    parser.add_argument('--api-key', required=True, help='OpenAI API Key')
    parser.add_argument('--model', default='gpt-4', help='OpenAI model to use')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--action', choices=['create', 'destroy'], default='create', 
                        help='Action to perform (create or destroy cluster)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    return parser.parse_args()

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Configuration file {config_path} not found. Creating a default configuration.")
        return create_default_config(config_path)
    except json.JSONDecodeError:
        print(f"Error parsing {config_path}. Please ensure it's valid JSON.")
        exit(1)

def create_default_config(config_path: str) -> Dict[str, Any]:
    """Create default configuration file"""
    default_config = {
        "cluster_name": "k8s-cluster",
        "aws_region": "us-east-1",
        "availability_zones": ["us-east-1a", "us-east-1b"],
        "vpc_cidr": "10.0.0.0/16",
        "subnet_count": 2,
        "master_count": 1,
        "worker_count": 2,
        "master_instance_type": "t3.medium",
        "worker_instance_type": "t3.large",
        "master_volume_size": 50,
        "worker_volume_size": 100,
        "ssh_public_key_path": "./.ssh/id_rsa.pub",
        "ssh_private_key_path": "./.ssh/id_rsa",
        "kubernetes_version": "1.28.2",
        "pod_network_cidr": "10.244.0.0/16",
        "service_cidr": "10.96.0.0/12"
    }
    
    # Save default configuration
    with open(config_path, 'w') as f:
        json.dump(default_config, f, indent=2)
        
    print(f"Default configuration saved to {config_path}. Please review and modify as needed.")
    return default_config

def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration parameters"""
    required_fields = [
        "cluster_name", "aws_region", "availability_zones", "vpc_cidr",
        "master_count", "worker_count", "ssh_public_key_path", "ssh_private_key_path"
    ]
    
    missing_fields = [field for field in required_fields if field not in config]
    
    if missing_fields:
        print(f"Missing required configuration fields: {', '.join(missing_fields)}")
        return False
        
    # Validate specific fields
    if config["master_count"] < 1:
        print("At least one master node is required")
        return False
        
    if not os.path.exists(os.path.expanduser(config["ssh_public_key_path"])):
        print(f"SSH public key not found at {config['ssh_public_key_path']}")
        return False
        
    if not os.path.exists(os.path.expanduser(config["ssh_private_key_path"])):
        print(f"SSH private key not found at {config['ssh_private_key_path']}")
        return False
    
    return True

def main():
    """Main function"""
    args = parse_arguments()
    
    # Set OpenAI API key
    os.environ["OPENAI_API_KEY"] = args.api_key
    
    # Load configuration
    config = load_config(args.config)
    
    # Validate configuration
    if not validate_config(config):
        exit(1)
    
    # Initialize K8s cluster manager
    manager = K8sClusterManager(
        api_key=args.api_key,
        model_name=args.model,
        verbose=args.verbose
    )
    
    # Perform action
    if args.action == 'create':
        print(f"Creating Kubernetes cluster with {config['master_count']} master(s) and {config['worker_count']} worker(s)...")
        result = manager.setup_kubernetes_cluster(config)
        if result["success"]:
            print("Kubernetes cluster created successfully!")
            print("\nCluster Information:")
            print(json.dumps(result.get("cluster_info", {}), indent=2))
        else:
            print(f"Failed to create Kubernetes cluster: {result['message']}")
    elif args.action == 'destroy':
        print("Destroying Kubernetes cluster...")
        result = manager.destroy_cluster()
        if result["success"]:
            print("Kubernetes cluster destroyed successfully!")
        else:
            print(f"Failed to destroy Kubernetes cluster: {result['message']}")

if __name__ == "__main__":
    main()