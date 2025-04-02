from langchain.tools import BaseTool
from langchain.callbacks.manager import AsyncCallbackManagerForToolRun, CallbackManagerForToolRun
import subprocess
import os
import json
from typing import Optional, Type, List, Dict, Any, Union

class TerraformInitTool(BaseTool):
    name = "terraform_init"
    description = "Initialize Terraform working directory"
    
    def _run(self, workspace_dir: str = "./terraform", 
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Run terraform init in the specified directory"""
        try:
            os.chdir(workspace_dir)
            result = subprocess.run(["terraform", "init"], 
                                   capture_output=True, text=True, check=True)
            return f"Terraform initialization complete:\n{result.stdout}"
        except subprocess.CalledProcessError as e:
            return f"Error initializing Terraform: {e.stderr}"
        finally:
            os.chdir("..")

class TerraformPlanTool(BaseTool):
    name = "terraform_plan"
    description = "Generate and show Terraform execution plan"
    
    def _run(self, workspace_dir: str = "./terraform", 
             variables: Optional[Dict[str, Any]] = None,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Run terraform plan with optional variables"""
        try:
            os.chdir(workspace_dir)
            cmd = ["terraform", "plan", "-detailed-exitcode", "-out=tfplan"]
            
            # Add variables if provided
            if variables:
                var_args = []
                for key, value in variables.items():
                    var_args.extend(["-var", f"{key}={value}"])
                cmd.extend(var_args)
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return "Terraform plan shows no changes needed"
            elif result.returncode == 2:
                return f"Terraform plan generated with changes:\n{result.stdout}"
            else:
                return f"Error in Terraform plan: {result.stderr}"
        except Exception as e:
            return f"Error executing Terraform plan: {str(e)}"
        finally:
            os.chdir("..")

class TerraformApplyTool(BaseTool):
    name = "terraform_apply"
    description = "Apply Terraform plan to create/modify infrastructure"
    
    def _run(self, workspace_dir: str = "./terraform", 
             auto_approve: bool = False,
             plan_file: Optional[str] = "tfplan",
             variables: Optional[Dict[str, Any]] = None,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Apply Terraform plan to create infrastructure"""
        try:
            os.chdir(workspace_dir)
            cmd = ["terraform", "apply"]
            
            if auto_approve:
                cmd.append("-auto-approve")
                
            if plan_file:
                cmd.append(plan_file)
            
            # Add variables if provided and no plan file specified
            if variables and not plan_file:
                var_args = []
                for key, value in variables.items():
                    var_args.extend(["-var", f"{key}={value}"])
                cmd.extend(var_args)
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse outputs from Terraform
                outputs_cmd = subprocess.run(["terraform", "output", "-json"], 
                                           capture_output=True, text=True)
                if outputs_cmd.returncode == 0:
                    try:
                        outputs = json.loads(outputs_cmd.stdout)
                        formatted_outputs = json.dumps(outputs, indent=2)
                        return f"Terraform apply successful. Outputs:\n{formatted_outputs}"
                    except json.JSONDecodeError:
                        return f"Terraform apply successful. No outputs or error parsing outputs."
                else:
                    return f"Terraform apply successful, but error fetching outputs: {outputs_cmd.stderr}"
            else:
                return f"Error in Terraform apply: {result.stderr}"
        except Exception as e:
            return f"Error executing Terraform apply: {str(e)}"
        finally:
            os.chdir("..")
            
class TerraformOutputTool(BaseTool):
    name = "terraform_output"
    description = "Get outputs from Terraform state"
    
    def _run(self, workspace_dir: str = "./terraform", 
             output_name: Optional[str] = None,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Get outputs from Terraform state"""
        try:
            os.chdir(workspace_dir)
            cmd = ["terraform", "output", "-json"]
            
            if output_name:
                cmd.append(output_name)
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    outputs = json.loads(result.stdout)
                    return json.dumps(outputs, indent=2)
                except json.JSONDecodeError:
                    return f"Error parsing Terraform outputs: {result.stdout}"
            else:
                return f"Error getting Terraform outputs: {result.stderr}"
        except Exception as e:
            return f"Error executing Terraform output command: {str(e)}"
        finally:
            os.chdir("..")

class TerraformDestroyTool(BaseTool):
    name = "terraform_destroy"
    description = "Destroy Terraform-managed infrastructure"
    
    def _run(self, workspace_dir: str = "./terraform", 
             auto_approve: bool = False,
             variables: Optional[Dict[str, Any]] = None,
             callback_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """Destroy Terraform-managed infrastructure"""
        try:
            os.chdir(workspace_dir)
            cmd = ["terraform", "destroy"]
            
            if auto_approve:
                cmd.append("-auto-approve")
                
            # Add variables if provided
            if variables:
                var_args = []
                for key, value in variables.items():
                    var_args.extend(["-var", f"{key}={value}"])
                cmd.extend(var_args)
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return "Terraform destroy completed successfully"
            else:
                return f"Error in Terraform destroy: {result.stderr}"
        except Exception as e:
            return f"Error executing Terraform destroy: {str(e)}"
        finally:
            os.chdir("..")