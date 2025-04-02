# main.tf

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