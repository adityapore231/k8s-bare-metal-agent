from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.callbacks.base import BaseCallbackHandler
from langchain_community.chat_models import ChatOpenAI
from langchain.schema import SystemMessage
from langchain.tools import BaseTool
from typing import List, Dict, Any, Optional, Tuple
import os
import json
import time

# Import our custom tools
from terraform_tools import (
    TerraformInitTool, 
    TerraformPlanTool, 
    TerraformApplyTool, 
    TerraformOutputTool,
    TerraformDestroyTool
)
from ssh_tools import (
    SSHConnectionTool,
    SCPTransferTool,
    ScriptGeneratorTool
)

class K8sClusterManager:
    def __init__(self, 
                 api_key: str,
                 model_name: str = "gpt-4",
                 temperature: float = 0.0,
                 verbose: bool = True):
        """Initialize the Kubernetes Cluster Manager Agent"""
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.verbose = verbose
        
        # Set up model
        self.llm = ChatOpenAI(
            openai_api_key=api_key, 
            model=model_name, 
            temperature=temperature
        )
        
        # Initialize tools
        self.tools = self._setup_tools()
        
        # Set up agent
        self.agent = self._setup_agent()
        
        # Working directory for artifacts
        self.working_dir = "./k8s_setup"
        os.makedirs(self.working_dir, exist_ok=True)
        os.makedirs(f"{self.working_dir}/terraform", exist_ok=True)
        os.makedirs(f"{self.working_dir}/scripts", exist_ok=True)
        
    def _setup_tools(self) -> List[BaseTool]:
        """Set up tools for the agent"""
        return [
            TerraformInitTool(),
            TerraformPlanTool(),
            TerraformApplyTool(),
            TerraformOutputTool(),
            TerraformDestroyTool(),
            SSHConnectionTool(),
            SCPTransferTool(),
            ScriptGeneratorTool()
        ]
        
    def _setup_agent(self) -> AgentExecutor:
        """Set up LangChain agent"""
        system_message = SystemMessage(
            content="""
            You are a DevOps expert that specializes in setting up Kubernetes clusters on AWS using Terraform.
            You need to help users create a bare metal Kubernetes cluster by:
            1. Creating the necessary infrastructure using Terraform
            2. Configuring the instances to run Kubernetes
            3. Setting up the Kubernetes cluster with master and worker nodes
            
            Use the available tools to:
            - Run Terraform commands to set up EC2 instances
            - Generate scripts for installing Kubernetes components
            - Use SSH to execute commands on the remote servers
            - Transfer files using SCP
            
            Always think step by step and explain your reasoning.
            """
        )
        
        agent = create_openai_tools_agent(
            self.llm,
            self.tools,
            system_message
        )
        
        return AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=15
        )
        
    def create_terraform_files(self, config: Dict[str, Any]) -> None:
        """Create Terraform files based on user config"""
        # Create main.tf
        with open(os.path.join(self.working_dir, "terraform", "main.tf"), "w") as f:
            f.write(self._generate_main_tf())
            
        # Create variables.tf
        with open(os.path.join(self.working_dir, "terraform", "variables.tf"), "w") as f:
            f.write(self._generate_variables_tf())
            
        # Create terraform.tfvars
        with open(os.path.join(self.working_dir, "terraform", "terraform.tfvars"), "w") as f:
            f.write(self._generate_tfvars(config))
    
    def _generate_main_tf(self) -> str:
        """Generate main.tf content"""
        # This would be the content of your main.tf file
        # You can read this from a template file or generate it dynamically
        return """
# Provider configuration
provider "aws" {
  region = var.aws_region
}

# VPC for the Kubernetes cluster
resource "aws_vpc" "k8s_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "${var.cluster_name}-vpc"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "k8s_igw" {
  vpc_id = aws_vpc.k8s_vpc.id

  tags = {
    Name = "${var.cluster_name}-igw"
  }
}

# Public subnet
resource "aws_subnet" "k8s_public_subnet" {
  count                   = var.subnet_count
  vpc_id                  = aws_vpc.k8s_vpc.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = element(var.availability_zones, count.index)
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-public-subnet-${count.index + 1}"
  }
}

# Route table for public subnet
resource "aws_route_table" "k8s_public_rt" {
  vpc_id = aws_vpc.k8s_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.k8s_igw.id
  }

  tags = {
    Name = "${var.cluster_name}-public-rt"
  }
}

# Route table association with public subnets
resource "aws_route_table_association" "k8s_public_rta" {
  count          = var.subnet_count
  subnet_id      = aws_subnet.k8s_public_subnet[count.index].id
  route_table_id = aws_route_table.k8s_public_rt.id
}

# Security group for Kubernetes nodes
resource "aws_security_group" "k8s_sg" {
  name        = "${var.cluster_name}-sg"
  description = "Security group for Kubernetes cluster nodes"
  vpc_id      = aws_vpc.k8s_vpc.id

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Kubernetes API server
  ingress {
    from_port   = 6443
    to_port     = 6443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow all internal traffic within the security group
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  # Allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-sg"
  }
}

# Key pair for SSH access
resource "aws_key_pair" "k8s_key_pair" {
  key_name   = "${var.cluster_name}-key"
  public_key = file(var.ssh_public_key_path)
}

# Master nodes
resource "aws_instance" "k8s_master" {
  count                  = var.master_count
  ami                    = var.ami_id
  instance_type          = var.master_instance_type
  key_name               = aws_key_pair.k8s_key_pair.key_name
  vpc_security_group_ids = [aws_security_group.k8s_sg.id]
  subnet_id              = aws_subnet.k8s_public_subnet[count.index % var.subnet_count].id
  root_block_device {
    volume_size = var.master_volume_size
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.cluster_name}-master-${count.index + 1}"
    Role = "master"
  }
}

# Worker nodes
resource "aws_instance" "k8s_worker" {
  count                  = var.worker_count
  ami                    = var.ami_id
  instance_type          = var.worker_instance_type
  key_name               = aws_key_pair.k8s_key_pair.key_name
  vpc_security_group_ids = [aws_security_group.k8s_sg.id]
  subnet_id              = aws_subnet.k8s_public_subnet[count.index % var.subnet_count].id
  root_block_device {
    volume_size = var.worker_volume_size
    volume_type = "gp3"
  }

  tags = {
    Name = "${var.cluster_name}-worker-${count.index + 1}"
    Role = "worker"
  }
}

# Outputs
output "master_public_ips" {
  value = aws_instance.k8s_master[*].public_ip
}

output "worker_public_ips" {
  value = aws_instance.k8s_worker[*].public_ip
}

output "master_private_ips" {
  value = aws_instance.k8s_master[*].private_ip
}

output "worker_private_ips" {
  value = aws_instance.k8s_worker[*].private_ip
}

output "kubernetes_api_endpoint" {
  value = "https://${aws_instance.k8s_master[0].public_ip}:6443"
}
"""
    
    def _generate_variables_tf(self) -> str:
        """Generate variables.tf content"""
        return """
variable "aws_region" {
  description = "AWS region where the Kubernetes cluster will be provisioned"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the Kubernetes cluster"
  type        = string
  default     = "k8s-cluster"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_count" {
  description = "Number of subnets to create"
  type        = number
  default     = 2
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "ami_id" {
  description = "AMI ID for the EC2 instances (Ubuntu Server 22.04 LTS)"
  type        = string
  default     = "ami-0c7217cdde317cfec" # Ubuntu Server 22.04 LTS in us-east-1
}

variable "master_count" {
  description = "Number of Kubernetes master nodes"
  type        = number
  default     = 1
}

variable "worker_count" {
  description = "Number of Kubernetes worker nodes"
  type        = number
  default     = 2
}

variable "master_instance_type" {
  description = "Instance type for Kubernetes master nodes"
  type        = string
  default     = "t3.medium"
}

variable "worker_instance_type" {
  description = "Instance type for Kubernetes worker nodes"
  type        = string
  default     = "t3.large"
}

variable "master_volume_size" {
  description = "Root volume size for master nodes in GB"
  type        = number
  default     = 50
}

variable "worker_volume_size" {
  description = "Root volume size for worker nodes in GB"
  type        = number
  default     = 100
}

variable "ssh_public_key_path" {
  description = "Path to the public SSH key for EC2 instance access"
  type        = string
  default     = "~/.ssh/id_rsa.pub"
}

variable "kubernetes_version" {
  description = "Kubernetes version to install"
  type        = string
  default     = "1.28.2"
}

variable "pod_network_cidr" {
  description = "CIDR for pod network"
  type        = string
  default     = "10.244.0.0/16"
}

variable "service_cidr" {
  description = "CIDR for Kubernetes services"
  type        = string
  default     = "10.96.0.0/12"
}
"""
    
    def _generate_tfvars(self, config: Dict[str, Any]) -> str:
        """Generate terraform.tfvars content based on user config"""
        tfvars = ""
        
        # Add user configuration values to tfvars
        for key, value in config.items():
            if isinstance(value, str):
                tfvars += f'{key} = "{value}"\n'
            elif isinstance(value, list):
                if all(isinstance(item, str) for item in value):
                    formatted_list = '", "'.join(value)
                    tfvars += f'{key} = ["{formatted_list}"]\n'
                else:
                    formatted_list = ', '.join(map(str, value))
                    tfvars += f'{key} = [{formatted_list}]\n'
            else:
                tfvars += f'{key} = {value}\n'
                
        return tfvars
        
    def setup_kubernetes_cluster(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up Kubernetes cluster based on user configuration
        
        Args:
            config: Dictionary containing configuration parameters such as:
                - master_count: Number of master nodes
                - worker_count: Number of worker nodes
                - aws_region: AWS region
                - ssh_private_key_path: Path to SSH private key
                - other Terraform variables
                
        Returns:
            Dictionary containing cluster information
        """
        try:
            # Create Terraform files
            self.create_terraform_files(config)
            
            # Execute agent to set up cluster
            result = self.agent.invoke({
                "input": f"""
                I want to set up a Kubernetes cluster with {config.get('master_count', 1)} master nodes 
                and {config.get('worker_count', 2)} worker nodes in AWS region {config.get('aws_region', 'us-east-1')}.
                
                I have already created the Terraform files in {self.working_dir}/terraform.
                
                Please perform the following steps:
                1. Initialize Terraform
                2. Create an execution plan
                3. Apply the Terraform configuration to create the infrastructure
                4. Generate the necessary scripts for setting up the Kubernetes cluster
                5. Configure the master node(s)
                6. Configure the worker nodes
                7. Verify the cluster is properly set up
                
                I'll be using the SSH key at {config.get('ssh_private_key_path', '~/.ssh/id_rsa')} for accessing the instances.
                """
            })
            
            return {
                "success": True,
                "message": "Kubernetes cluster setup completed successfully",
                "agent_output": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error setting up Kubernetes cluster: {str(e)}",
                "error": str(e)
            }
    
    def destroy_cluster(self) -> Dict[str, Any]:
        """Destroy the Kubernetes cluster"""
        try:
            result = self.agent.invoke({
                "input": f"""
                Please destroy the Kubernetes cluster that was created.
                Run terraform destroy with auto-approve to remove all resources.
                """
            })
            
            return {
                "success": True,
                "message": "Kubernetes cluster destroyed successfully",
                "agent_output": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error destroying Kubernetes cluster: {str(e)}",
                "error": str(e)
            }