# variables.tf

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