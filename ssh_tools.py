from langchain.tools import BaseTool
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
import paramiko
import os
from typing import Optional, Type, List, Dict, Any, Union

class SSHConnectionTool(BaseTool):
    name = "ssh_execute"
    description = "Execute commands on remote servers via SSH"
    
    def _run(self, host: str, 
             username: str = "ubuntu", 
             key_path: str = "~/.ssh/id_rsa",
             port: int = 22,
             command: str = "echo 'Hello World'",
             timeout: int = 30,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Execute commands on remote servers via SSH"""
        try:
            # Expand key path if it uses ~
            key_path = os.path.expanduser(key_path)
            
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server
            client.connect(
                hostname=host,
                username=username,
                key_filename=key_path,
                port=port,
                timeout=timeout
            )
            
            # Execute command
            stdin, stdout, stderr = client.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            
            # Get command output
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            
            # Close connection
            client.close()
            
            if exit_status == 0:
                return f"Command executed successfully:\n{output}"
            else:
                return f"Command failed with exit status {exit_status}:\n{error}"
        except Exception as e:
            return f"SSH error: {str(e)}"

class SCPTransferTool(BaseTool):
    name = "scp_transfer"
    description = "Transfer files to/from remote servers via SCP"
    
    def _run(self, host: str, 
             username: str = "ubuntu", 
             key_path: str = "~/.ssh/id_rsa",
             port: int = 22,
             local_path: str = "",
             remote_path: str = "",
             upload: bool = True,
             recursive: bool = False,
             timeout: int = 30,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Transfer files to/from remote servers via SCP"""
        try:
            # Expand key path if it uses ~
            key_path = os.path.expanduser(key_path)
            
            # Create SSH client
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect to server
            client.connect(
                hostname=host,
                username=username,
                key_filename=key_path,
                port=port,
                timeout=timeout
            )
            
            # Create SFTP client
            sftp = client.open_sftp()
            
            if upload:
                if recursive and os.path.isdir(local_path):
                    # Create remote directory if it doesn't exist
                    try:
                        sftp.stat(remote_path)
                    except FileNotFoundError:
                        sftp.mkdir(remote_path)
                    
                    # Upload directory recursively
                    for root, dirs, files in os.walk(local_path):
                        for dir_name in dirs:
                            local_dir = os.path.join(root, dir_name)
                            rel_path = os.path.relpath(local_dir, local_path)
                            remote_dir = os.path.join(remote_path, rel_path)
                            try:
                                sftp.stat(remote_dir)
                            except FileNotFoundError:
                                sftp.mkdir(remote_dir)
                        
                        for file_name in files:
                            local_file = os.path.join(root, file_name)
                            rel_path = os.path.relpath(local_file, local_path)
                            remote_file = os.path.join(remote_path, rel_path)
                            sftp.put(local_file, remote_file)
                    
                    result = f"Directory {local_path} uploaded to {remote_path} on {host}"
                else:
                    # Upload single file
                    sftp.put(local_path, remote_path)
                    result = f"File {local_path} uploaded to {remote_path} on {host}"
            else:
                if recursive and sftp_is_dir(sftp, remote_path):
                    # Create local directory if it doesn't exist
                    if not os.path.exists(local_path):
                        os.makedirs(local_path)
                    
                    # Download directory recursively
                    download_dir_recursive(sftp, remote_path, local_path)
                    result = f"Directory {remote_path} downloaded to {local_path} from {host}"
                else:
                    # Download single file
                    sftp.get(remote_path, local_path)
                    result = f"File {remote_path} downloaded to {local_path} from {host}"
            
            # Close connections
            sftp.close()
            client.close()
            
            return result
        except Exception as e:
            return f"SCP error: {str(e)}"

class ScriptGeneratorTool(BaseTool):
    name = "generate_script"
    description = "Generate shell scripts for server configuration"
    
    def _run(self, script_type: str,
             output_path: str,
             parameters: Optional[Dict[str, Any]] = None,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Generate shell scripts for server configuration"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            script_content = ""
            
            if script_type == "k8s_master":
                script_content = self._generate_k8s_master_script(parameters)
            elif script_type == "k8s_worker":
                script_content = self._generate_k8s_worker_script(parameters)
            elif script_type == "common":
                script_content = self._generate_common_script(parameters)
            else:
                return f"Unknown script type: {script_type}"
                
            # Write script to file
            with open(output_path, 'w') as f:
                f.write(script_content)
                
            # Make script executable
            os.chmod(output_path, 0o755)
                
            return f"Script generated at {output_path}"
        except Exception as e:
            return f"Script generation error: {str(e)}"
            
    def _generate_common_script(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate common setup script for all nodes"""
        kubernetes_version = parameters.get("kubernetes_version", "1.28.2")
        containerd_version = parameters.get("containerd_version", "1.7.2")
        
        script = f"""#!/bin/bash
set -e

# Common setup script for Kubernetes nodes

# Update system and install dependencies
apt-get update
apt-get upgrade -y
apt-get install -y apt-transport-https ca-certificates curl software-properties-common gnupg

# Disable swap
swapoff -a
sed -i '/swap/d' /etc/fstab

# Load kernel modules
cat <<EOF | tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

modprobe overlay
modprobe br_netfilter

# Set up required sysctl params
cat <<EOF | tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sysctl --system

# Install containerd
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y containerd.io

# Configure containerd to use systemd as cgroup driver
mkdir -p /etc/containerd
containerd config default | tee /etc/containerd/config.toml
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
systemctl restart containerd
systemctl enable containerd

# Install Kubernetes components
curl -fsSL https://pkgs.k8s.io/core:/stable:/v{kubernetes_version}/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v{kubernetes_version}/deb/ /" | tee /etc/apt/sources.list.d/kubernetes.list
apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

echo "Common node setup completed!"
"""
        return script
        
    def _generate_k8s_master_script(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate master node setup script"""
        pod_network_cidr = parameters.get("pod_network_cidr", "10.244.0.0/16")
        service_cidr = parameters.get("service_cidr", "10.96.0.0/12")
        
        script = f"""#!/bin/bash
set -e

# Master node setup script

# Initialize Kubernetes cluster
kubeadm init --pod-network-cidr={pod_network_cidr} --service-cidr={service_cidr}

# Set up kubeconfig for the user
mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

# Install Calico network plugin
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/master/manifests/tigera-operator.yaml
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/master/manifests/custom-resources.yaml

# Generate join command for worker nodes
JOIN_COMMAND=$(kubeadm token create --print-join-command)
echo "$JOIN_COMMAND" > /root/k8s_join_command.sh

# Output cluster info
kubectl cluster-info
kubectl get nodes

echo "Master node setup completed!"
"""
        return script
        
    def _generate_k8s_worker_script(self, parameters: Optional[Dict[str, Any]] = None) -> str:
        """Generate worker node setup script"""
        join_command = parameters.get("join_command", "")
        
        script = f"""#!/bin/bash
set -e

# Worker node setup script

# Join the cluster
{join_command}

echo "Worker node joined the cluster!"
"""
        return script

# Helper functions for SCP
def sftp_is_dir(sftp, path):
    try:
        return sftp.stat(path).st_mode & 0o170000 == 0o040000
    except:
        return False

def download_dir_recursive(sftp, remote_dir, local_dir):
    for item in sftp.listdir(remote_dir):
        remote_path = os.path.join(remote_dir, item)
        local_path = os.path.join(local_dir, item)
        
        if sftp_is_dir(sftp, remote_path):
            if not os.path.exists(local_path):
                os.makedirs(local_path)
            download_dir_recursive(sftp, remote_path, local_path)
        else:
            sftp.get(remote_path, local_path)