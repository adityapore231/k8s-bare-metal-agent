class K8sPromptTemplates:
    """Prompt templates for the Kubernetes cluster manager agent"""
    
    @staticmethod
    def infrastructure_setup_prompt() -> str:
        """Prompt for infrastructure setup"""
        return """
        I need you to set up the AWS infrastructure for a Kubernetes cluster using Terraform.
        
        First, initialize Terraform in the working directory. Then, create a plan to review the resources 
        that will be created. Finally, apply the configuration to create the infrastructure.
        
        After the infrastructure is created, collect the public and private IP addresses of the master 
        and worker nodes for later use.
        
        Here's what you need to do:
        1. Change to the Terraform directory
        2. Run 'terraform init'
        3. Run 'terraform plan'
        4. Run 'terraform apply'
        5. Collect and return the output information
        
        Please execute these steps and keep track of the resources created.
        """
    
    @staticmethod
    def master_setup_prompt(master_ip: str, ssh_key_path: str) -> str:
        """Prompt for master node setup"""
        return f"""
        Now that the infrastructure is ready, I need you to set up the Kubernetes master node on {master_ip}.
        
        First, generate the common setup script that will be used for all nodes. This script should:
        1. Update the system
        2. Install dependencies
        3. Disable swap
        4. Configure containerd
        5. Install kubelet, kubeadm, and kubectl
        
        Then, generate a master-specific script that will:
        1. Initialize the Kubernetes cluster with kubeadm
        2. Set up the kubeconfig file
        3. Install a network plugin (Calico)
        4. Generate a join command for worker nodes
        
        After generating these scripts, transfer them to the master node and execute them in order.
        
        Here's what you need to do:
        1. Generate the common setup script
        2. Generate the master-specific script
        3. Transfer the scripts to the master node using SCP
        4. Execute the scripts via SSH
        5. Retrieve the join command for worker nodes
        
        Please execute these steps and report back on the status of the master node.
        """
    
    @staticmethod
    def worker_setup_prompt(worker_ip: str, ssh_key_path: str, join_command: str) -> str:
        """Prompt for worker node setup"""
        return f"""
        Now that the master node is set up, I need you to set up the Kubernetes worker node on {worker_ip}.
        
        First, generate the common setup script that will be used for all nodes (if not already done). This script should:
        1. Update the system
        2. Install dependencies
        3. Disable swap
        4. Configure containerd
        5. Install kubelet, kubeadm, and kubectl
        
        Then, generate a worker-specific script that will:
        1. Join the Kubernetes cluster using the join command from the master node
        
        After generating these scripts, transfer them to the worker node and execute them in order.
        
        Here's what you need to do:
        1. Generate the common setup script (if not already done)
        2. Generate the worker-specific script with the join command: {join_command}
        3. Transfer the scripts to the worker node using SCP
        4. Execute the scripts via SSH
        
        Please execute these steps and report back on the status of the worker node.
        """
    
    @staticmethod
    def cluster_verification_prompt(master_ip: str, ssh_key_path: str) -> str:
        """Prompt for cluster verification"""
        return f"""
        Now that both master and worker nodes are set up, I need you to verify that the Kubernetes cluster is functioning correctly.
        
        Connect to the master node via SSH and run the following commands:
        1. kubectl get nodes - to verify that all nodes are in the Ready state
        2. kubectl get pods --all-namespaces - to verify that system pods are running
        3. kubectl version - to verify the Kubernetes version
        
        Here's what you need to do:
        1. SSH into the master node {master_ip}
        2. Run the verification commands
        3. Report back on the status of the cluster
        
        Please execute these steps and confirm that the cluster is functioning correctly.
        """
        
    @staticmethod
    def cluster_destruction_prompt() -> str:
        """Prompt for cluster destruction"""
        return """
        I need you to destroy the Kubernetes cluster infrastructure that was created with Terraform.
        
        Run 'terraform destroy' with the auto-approve flag to remove all AWS resources that were created.
        
        Here's what you need to do:
        1. Change to the Terraform directory
        2. Run 'terraform destroy -auto-approve'
        3. Verify that all resources have been destroyed
        
        Please execute these steps and confirm that all resources have been destroyed.
        """