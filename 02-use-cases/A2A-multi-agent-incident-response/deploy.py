#!/usr/bin/env python3
"""
Interactive deployment script for A2A Multi-Agent Incident Response System.
This script collects all required parameters and stores them in .a2a.config
"""

import sys
import uuid
import yaml
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional


class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(70)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 70}{Colors.END}\n")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def get_input(prompt: str, default: Optional[str] = None, required: bool = True) -> str:
    """Get user input with optional default value"""
    if default:
        display_prompt = f"{Colors.BLUE}{prompt} [{Colors.GREEN}{default}{Colors.BLUE}]: {Colors.END}"
    else:
        display_prompt = f"{Colors.BLUE}{prompt}: {Colors.END}"

    while True:
        value = input(display_prompt).strip()

        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print_error("This field is required. Please provide a value.")


def get_secret(prompt: str, required: bool = True) -> str:
    """Get sensitive input (like API keys)"""
    import getpass

    display_prompt = f"{Colors.BLUE}{prompt}: {Colors.END}"

    while True:
        value = getpass.getpass(display_prompt).strip()

        if value:
            return value
        elif not required:
            return ""
        else:
            print_error("This field is required. Please provide a value.")


def generate_bucket_name(account_id: str = None) -> str:
    """Generate a unique S3 bucket name"""
    unique_id = str(uuid.uuid4())[:8]
    # Include account ID for better uniqueness if available
    if account_id:
        return f"a2a-smithy-models-{account_id}-{unique_id}"
    return f"a2a-smithy-models-{unique_id}"


def validate_bucket_name(bucket_name: str) -> tuple:
    """Validate S3 bucket name according to AWS rules"""
    if not bucket_name:
        return (False, "Bucket name cannot be empty")

    if len(bucket_name) < 3 or len(bucket_name) > 63:
        return (False, "Bucket name must be between 3 and 63 characters")

    if not bucket_name[0].isalnum() or not bucket_name[-1].isalnum():
        return (False, "Bucket name must begin and end with a letter or number")

    # Check for invalid characters and patterns
    import re

    if not re.match(r"^[a-z0-9][a-z0-9\-]*[a-z0-9]$", bucket_name):
        return (
            False,
            "Bucket name must contain only lowercase letters, numbers, and hyphens",
        )

    if ".." in bucket_name or ".-" in bucket_name or "-." in bucket_name:
        return (
            False,
            "Bucket name cannot contain consecutive periods or period-hyphen combinations",
        )

    return (True, "Valid bucket name")


def check_s3_bucket_exists(bucket_name: str, region: str) -> bool:
    """Check if S3 bucket already exists"""
    success, output = run_command(
        ["aws", "s3api", "head-bucket", "--bucket", bucket_name, "--region", region]
    )
    return success


def validate_stack_name(stack_name: str) -> tuple:
    """Validate CloudFormation stack name"""
    if not stack_name:
        return (False, "Stack name cannot be empty")

    if len(stack_name) > 128:
        return (False, "Stack name must be 128 characters or fewer")

    import re

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9\-]*$", stack_name):
        return (
            False,
            "Stack name must start with a letter and contain only alphanumeric characters and hyphens",
        )

    return (True, "Valid stack name")


def load_existing_config(config_path: Path) -> Dict[str, Any]:
    """Load existing configuration if it exists"""
    if config_path.exists():
        with open(config_path, "r") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(config: Dict[str, Any], config_path: Path):
    """Save configuration to YAML file"""
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    print_success(f"Configuration saved to {config_path}")


def run_command(cmd: list, capture_output: bool = True) -> tuple:
    """Run a shell command and return (success, output)"""
    try:
        result = subprocess.run(
            cmd, capture_output=capture_output, text=True, timeout=10
        )
        return (result.returncode == 0, result.stdout.strip() if capture_output else "")
    except Exception as e:
        return (False, str(e))


def check_aws_cli() -> bool:
    """Check if AWS CLI is installed"""
    success, output = run_command(["aws", "--version"])
    if success:
        print_success(f"AWS CLI is installed: {output.split()[0]}")
        return True
    else:
        print_error("AWS CLI is not installed")
        print_info(
            "Install AWS CLI: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        )
        return False


def check_aws_credentials() -> bool:
    """Check if AWS credentials are configured and valid"""
    success, output = run_command(["aws", "sts", "get-caller-identity"])
    if success:
        try:
            identity = json.loads(output)
            print_success("AWS credentials are valid")
            print_info(f"  Account: {identity.get('Account', 'N/A')}")
            print_info(f"  User/Role: {identity.get('Arn', 'N/A').split('/')[-1]}")
            return True
        except json.JSONDecodeError:
            print_error("Failed to parse AWS identity")
            return False
    else:
        print_error("AWS credentials are not configured or invalid")
        print_info("Configure AWS CLI: aws configure")
        return False


def check_aws_region() -> tuple:
    """Check if AWS region is configured and is us-west-2"""
    success, output = run_command(["aws", "configure", "get", "region"])
    if success and output:
        region = output.strip()
        if region == "us-west-2":
            print_success("AWS region is correctly set to us-west-2")
            return (True, region)
        else:
            print_error(f"AWS region is set to '{region}' but must be 'us-west-2'")
            print_info("This solution is only supported in us-west-2")
            print_info("Change region: aws configure set region us-west-2")
            return (False, region)
    else:
        print_error("AWS region is not configured")
        print_info("Configure region: aws configure set region us-west-2")
        return (False, None)


def check_bedrock_model_access() -> bool:
    """Check if Bedrock model access is enabled"""
    print_info("Checking Bedrock model access...")
    success, output = run_command(
        ["aws", "bedrock", "list-foundation-models", "--region", "us-west-2"]
    )
    if success:
        print_success("Bedrock API is accessible")
        return True
    else:
        print_warning(
            "Could not verify Bedrock access (this may be a permissions issue)"
        )
        return True  # Don't fail on this check, just warn


def run_pre_checks() -> tuple:
    """Run all pre-deployment checks and return (success, account_id)"""
    print_header("Pre-Deployment Checks")
    print_info("Verifying prerequisites...\n")

    checks_passed = True
    account_id = None

    # Check AWS CLI
    if not check_aws_cli():
        checks_passed = False

    print()

    # Check AWS credentials and get account ID
    success, output = run_command(["aws", "sts", "get-caller-identity"])
    if success:
        try:
            identity = json.loads(output)
            account_id = identity.get("Account", "N/A")
            print_success("AWS credentials are valid")
            print_info(f"  Account: {account_id}")
            print_info(f"  User/Role: {identity.get('Arn', 'N/A').split('/')[-1]}")
        except json.JSONDecodeError:
            print_error("Failed to parse AWS identity")
            checks_passed = False
    else:
        print_error("AWS credentials are not configured or invalid")
        print_info("Configure AWS CLI: aws configure")
        checks_passed = False

    print()

    # Check AWS region
    region_ok, region = check_aws_region()
    if not region_ok:
        checks_passed = False

    print()

    # Check Bedrock access (warning only)
    check_bedrock_model_access()

    print()

    if not checks_passed:
        print_error(
            "Pre-deployment checks failed. Please fix the issues above before continuing."
        )
        return (False, None)

    print_success("All pre-deployment checks passed!")
    return (True, account_id)


def collect_deployment_parameters(account_id: str = None) -> Dict[str, Any]:
    """Interactively collect all deployment parameters"""

    config_path = Path(".a2a.config")
    existing_config = load_existing_config(config_path)

    print_header("A2A Multi-Agent Incident Response - Deployment Configuration")

    print_info("This script will help you configure all parameters for deployment.")
    print_info("Press Enter to accept default values (shown in green brackets).\n")

    # Check if config exists
    if existing_config:
        print_warning(f"Found existing configuration at {config_path}")
        use_existing = get_input(
            "Do you want to use existing values as defaults? (yes/no)",
            default="yes",
            required=True,
        ).lower() in ["yes", "y"]
        print()
    else:
        use_existing = False

    config = {}

    # AWS Configuration (region is fixed to us-west-2)
    print_header("AWS Configuration")
    config["aws"] = {
        "region": "us-west-2",  # Fixed to us-west-2 as verified in pre-checks
        "bedrock_model_id": get_input(
            "Bedrock Model ID",
            default=(
                existing_config.get("aws", {}).get(
                    "bedrock_model_id", "global.anthropic.claude-sonnet-4-20250514-v1:0"
                )
                if use_existing
                else "global.anthropic.claude-sonnet-4-20250514-v1:0"
            ),
            required=True,
        ),
    }
    print_info("Region is fixed to us-west-2 (verified in pre-checks)")

    # Stack Names with validation
    print_header("CloudFormation Stack Names")
    config["stacks"] = {}

    stack_names = {
        "cognito": ("Cognito Stack Name", "cognito-stack-a2a"),
        "monitoring_agent": ("Monitoring Agent Stack Name", "monitor-agent-a2a"),
        "web_search_agent": ("Web Search Agent Stack Name", "web-search-agent-a2a"),
        "host_agent": ("Host Agent Stack Name", "host-agent-a2a"),
    }

    for key, (prompt, default_name) in stack_names.items():
        while True:
            stack_name = get_input(
                prompt,
                default=(
                    existing_config.get("stacks", {}).get(key, default_name)
                    if use_existing
                    else default_name
                ),
                required=True,
            )
            is_valid, message = validate_stack_name(stack_name)
            if is_valid:
                config["stacks"][key] = stack_name
                break
            else:
                print_error(f"Invalid stack name: {message}")

    # S3 Bucket for Smithy Models with validation
    print_header("S3 Configuration")
    default_bucket = (
        existing_config.get("s3", {}).get("smithy_models_bucket")
        if use_existing
        else generate_bucket_name(account_id)
    )

    while True:
        bucket_name = get_input(
            "S3 Bucket Name for Smithy Models", default=default_bucket, required=True
        )
        is_valid, message = validate_bucket_name(bucket_name)
        if is_valid:
            # Check if bucket already exists
            if check_s3_bucket_exists(bucket_name, "us-west-2"):
                print_warning(
                    f"Bucket '{bucket_name}' already exists. You can use it if you own it."
                )
                use_existing_bucket = get_input(
                    "Use this existing bucket? (yes/no)", default="yes", required=True
                ).lower() in ["yes", "y"]
                if use_existing_bucket:
                    config["s3"] = {"smithy_models_bucket": bucket_name}
                    break
                else:
                    continue
            else:
                config["s3"] = {"smithy_models_bucket": bucket_name}
                break
        else:
            print_error(f"Invalid bucket name: {message}")

    # GitHub Configuration
    print_header("GitHub Configuration")
    config["github"] = {
        "url": get_input(
            "GitHub Repository URL",
            default=(
                existing_config.get("github", {}).get(
                    "url",
                    "https://github.com/awslabs/amazon-bedrock-agentcore-samples.git",
                )
                if use_existing
                else "https://github.com/awslabs/amazon-bedrock-agentcore-samples.git"
            ),
            required=True,
        ),
        # Agent directories are taken from CloudFormation defaults - not configurable
        "monitoring_agent_directory": "monitoring_agent",
        "web_search_agent_directory": "web_search_openai_agents",
        "host_agent_directory": "host_adk_agent",
    }
    print_info(
        "Agent directories will use CloudFormation defaults (monitoring_agent, web_search_openai_agents, host_adk_agent)"
    )

    # API Keys
    print_header("API Keys Configuration")
    print_warning("API keys will be stored in .a2a.config - keep this file secure!")
    print_info("Input is hidden for security. Paste your key and press Enter.\n")

    # Check if we should ask for API keys
    ask_for_keys = True
    if use_existing and existing_config.get("api_keys"):
        print_info("Existing API keys found in configuration.")
        update_keys = get_input(
            "Do you want to update API keys? (yes/no)", default="no", required=True
        ).lower() in ["yes", "y"]
        ask_for_keys = update_keys
        print()

    if ask_for_keys:
        config["api_keys"] = {
            "openai": get_secret("OpenAI API Key", required=True),
            "openai_model": get_input(
                "OpenAI Model ID",
                default=(
                    existing_config.get("api_keys", {}).get(
                        "openai_model", "gpt-4o-2024-08-06"
                    )
                    if use_existing
                    else "gpt-4o-2024-08-06"
                ),
                required=True,
            ),
            "tavily": get_secret("Tavily API Key", required=True),
            "google": get_secret("Google API Key (for ADK)", required=True),
        }
    else:
        config["api_keys"] = existing_config.get("api_keys", {})

    return config


def display_configuration(config: Dict[str, Any]):
    """Display the collected configuration"""
    print_header("Configuration Summary")

    print(f"{Colors.BOLD}AWS Configuration:{Colors.END}")
    print(f"  Region: {config['aws']['region']}")
    print(f"  Bedrock Model ID: {config['aws']['bedrock_model_id']}")

    print(f"\n{Colors.BOLD}CloudFormation Stacks:{Colors.END}")
    print(f"  Cognito: {config['stacks']['cognito']}")
    print(f"  Monitoring Agent: {config['stacks']['monitoring_agent']}")
    print(f"  Web Search Agent: {config['stacks']['web_search_agent']}")
    print(f"  Host Agent: {config['stacks']['host_agent']}")

    print(f"\n{Colors.BOLD}S3 Configuration:{Colors.END}")
    print(f"  Smithy Models Bucket: {config['s3']['smithy_models_bucket']}")

    print(f"\n{Colors.BOLD}GitHub Configuration:{Colors.END}")
    print(f"  Repository URL: {config['github']['url']}")
    print(f"  Monitoring Agent Dir: {config['github']['monitoring_agent_directory']}")
    print(f"  Web Search Agent Dir: {config['github']['web_search_agent_directory']}")
    print(f"  Host Agent Dir: {config['github']['host_agent_directory']}")

    print(f"\n{Colors.BOLD}API Keys:{Colors.END}")
    print(f"  OpenAI API Key: {'*' * 20} (configured)")
    print(f"  OpenAI Model: {config['api_keys']['openai_model']}")
    print(f"  Tavily API Key: {'*' * 20} (configured)")
    print(f"  Google API Key: {'*' * 20} (configured)")

    print()


def wait_for_stack(stack_name: str, region: str, operation: str = "create") -> bool:
    """Wait for CloudFormation stack operation to complete"""
    import time

    print_info(f"Waiting for stack '{stack_name}' to complete {operation}...")

    max_wait_time = 1800  # 30 minutes
    wait_interval = 15  # 15 seconds
    elapsed_time = 0

    while elapsed_time < max_wait_time:
        success, output = run_command(
            [
                "aws",
                "cloudformation",
                "describe-stacks",
                "--stack-name",
                stack_name,
                "--region",
                region,
                "--query",
                "Stacks[0].StackStatus",
                "--output",
                "text",
            ]
        )

        if success:
            status = output.strip()

            # Check for completion statuses
            if operation == "create" and status == "CREATE_COMPLETE":
                print_success(f"Stack '{stack_name}' created successfully!")
                return True
            elif operation == "create" and status == "CREATE_FAILED":
                print_error(f"Stack '{stack_name}' creation failed!")
                return False
            elif operation == "create" and status == "ROLLBACK_COMPLETE":
                print_error(f"Stack '{stack_name}' creation failed and rolled back!")
                return False
            elif operation == "create" and status == "ROLLBACK_IN_PROGRESS":
                print_warning(
                    f"Stack '{stack_name}' is rolling back... Status: {status}"
                )
            else:
                print_info(f"Stack status: {status} (waiting...)")

        time.sleep(wait_interval)
        elapsed_time += wait_interval

    print_error(f"Timeout waiting for stack '{stack_name}' (waited {max_wait_time}s)")
    return False


def create_s3_bucket_and_upload(config: Dict[str, Any]) -> bool:
    """Create S3 bucket and upload Smithy model"""
    print_header("Step 0: Create S3 Bucket and Upload Smithy Model")

    bucket_name = config["s3"]["smithy_models_bucket"]
    region = config["aws"]["region"]

    # Check if bucket already exists
    if check_s3_bucket_exists(bucket_name, region):
        print_info(f"Bucket '{bucket_name}' already exists, skipping creation")
    else:
        print_info(f"Creating S3 bucket: {bucket_name}")
        success, output = run_command(
            ["aws", "s3", "mb", f"s3://{bucket_name}", "--region", region]
        )

        if success:
            print_success(f"S3 bucket '{bucket_name}' created successfully!")
        else:
            print_error(f"Failed to create S3 bucket: {output}")
            return False

    # Upload Smithy model
    smithy_model_path = "cloudformation/smithy-models/monitoring-service.json"
    s3_key = "smithy-models/monitoring-service.json"

    if not Path(smithy_model_path).exists():
        print_error(f"Smithy model file not found: {smithy_model_path}")
        return False

    print_info(f"Uploading Smithy model to s3://{bucket_name}/{s3_key}")
    success, output = run_command(
        [
            "aws",
            "s3",
            "cp",
            smithy_model_path,
            f"s3://{bucket_name}/{s3_key}",
            "--region",
            region,
        ]
    )

    if success:
        print_success("Smithy model uploaded successfully!")
        return True
    else:
        print_error(f"Failed to upload Smithy model: {output}")
        return False


def deploy_cognito_stack(config: Dict[str, Any]) -> bool:
    """Deploy Cognito CloudFormation stack"""
    print_header("Step 1: Deploy Cognito Stack")

    stack_name = config["stacks"]["cognito"]
    region = config["aws"]["region"]

    print_info(f"Creating CloudFormation stack: {stack_name}")
    success, output = run_command(
        [
            "aws",
            "cloudformation",
            "create-stack",
            "--stack-name",
            stack_name,
            "--template-body",
            "file://cloudformation/cognito.yaml",
            "--capabilities",
            "CAPABILITY_IAM",
            "--region",
            region,
        ]
    )

    if success:
        print_success(f"Stack creation initiated: {stack_name}")
        return wait_for_stack(stack_name, region, "create")
    else:
        if "AlreadyExistsException" in output:
            print_warning(f"Stack '{stack_name}' already exists")
            return True
        print_error(f"Failed to create stack: {output}")
        return False


def deploy_monitoring_agent(config: Dict[str, Any]) -> bool:
    """Deploy Monitoring Agent CloudFormation stack"""
    print_header("Step 2: Deploy Monitoring Agent")

    stack_name = config["stacks"]["monitoring_agent"]
    region = config["aws"]["region"]

    print_info(f"Creating CloudFormation stack: {stack_name}")
    success, output = run_command(
        [
            "aws",
            "cloudformation",
            "create-stack",
            "--stack-name",
            stack_name,
            "--template-body",
            "file://cloudformation/monitoring_agent.yaml",
            "--parameters",
            f"ParameterKey=GitHubURL,ParameterValue={config['github']['url']}",
            f"ParameterKey=CognitoStackName,ParameterValue={config['stacks']['cognito']}",
            f"ParameterKey=SmithyModelS3Bucket,ParameterValue={config['s3']['smithy_models_bucket']}",
            f"ParameterKey=BedrockModelId,ParameterValue={config['aws']['bedrock_model_id']}",
            "--capabilities",
            "CAPABILITY_IAM",
            "--region",
            region,
        ]
    )

    if success:
        print_success(f"Stack creation initiated: {stack_name}")
        return wait_for_stack(stack_name, region, "create")
    else:
        if "AlreadyExistsException" in output:
            print_warning(f"Stack '{stack_name}' already exists")
            return True
        print_error(f"Failed to create stack: {output}")
        return False


def deploy_web_search_agent(config: Dict[str, Any]) -> bool:
    """Deploy Web Search Agent CloudFormation stack"""
    print_header("Step 3: Deploy Web Search Agent")

    stack_name = config["stacks"]["web_search_agent"]
    region = config["aws"]["region"]

    print_info(f"Creating CloudFormation stack: {stack_name}")
    success, output = run_command(
        [
            "aws",
            "cloudformation",
            "create-stack",
            "--stack-name",
            stack_name,
            "--template-body",
            "file://cloudformation/web_search_agent.yaml",
            "--parameters",
            f"ParameterKey=OpenAIKey,ParameterValue={config['api_keys']['openai']}",
            f"ParameterKey=OpenAIModelId,ParameterValue={config['api_keys']['openai_model']}",
            f"ParameterKey=TavilyAPIKey,ParameterValue={config['api_keys']['tavily']}",
            f"ParameterKey=GitHubURL,ParameterValue={config['github']['url']}",
            f"ParameterKey=CognitoStackName,ParameterValue={config['stacks']['cognito']}",
            "--capabilities",
            "CAPABILITY_IAM",
            "--region",
            region,
        ]
    )

    if success:
        print_success(f"Stack creation initiated: {stack_name}")
        return wait_for_stack(stack_name, region, "create")
    else:
        if "AlreadyExistsException" in output:
            print_warning(f"Stack '{stack_name}' already exists")
            return True
        print_error(f"Failed to create stack: {output}")
        return False


def deploy_host_agent(config: Dict[str, Any]) -> bool:
    """Deploy Host Agent CloudFormation stack"""
    print_header("Step 4: Deploy Host Agent")

    stack_name = config["stacks"]["host_agent"]
    region = config["aws"]["region"]

    print_info(f"Creating CloudFormation stack: {stack_name}")
    success, output = run_command(
        [
            "aws",
            "cloudformation",
            "create-stack",
            "--stack-name",
            stack_name,
            "--template-body",
            "file://cloudformation/host_agent.yaml",
            "--parameters",
            f"ParameterKey=GoogleApiKey,ParameterValue={config['api_keys']['google']}",
            f"ParameterKey=GitHubURL,ParameterValue={config['github']['url']}",
            f"ParameterKey=CognitoStackName,ParameterValue={config['stacks']['cognito']}",
            "--capabilities",
            "CAPABILITY_IAM",
            "--region",
            region,
        ]
    )

    if success:
        print_success(f"Stack creation initiated: {stack_name}")
        return wait_for_stack(stack_name, region, "create")
    else:
        if "AlreadyExistsException" in output:
            print_warning(f"Stack '{stack_name}' already exists")
            return True
        print_error(f"Failed to create stack: {output}")
        return False


def print_cleanup_instructions():
    """Print instructions to run cleanup after deployment failure"""
    print()
    print_header("Deployment Failed - Cleanup Required")
    print_error("Deployment has failed and may have left partial resources.")
    print_warning(
        "You should clean up any created resources before retrying deployment.\n"
    )

    print_info("To clean up all created resources, run:")
    print(f"  {Colors.GREEN}uv run cleanup.py{Colors.END}\n")

    print_info("After cleanup, you can retry deployment by running:")
    print(f"  {Colors.GREEN}python3 deploy.py{Colors.END}")
    print()


def run_deployment(config: Dict[str, Any]) -> bool:
    """Run all deployment steps"""
    print_header("Starting Deployment")
    print_warning("This will take approximately 10-15 minutes to complete")
    print_info("You can monitor progress in the AWS CloudFormation console\n")

    # Step 0: Create S3 bucket and upload Smithy model
    if not create_s3_bucket_and_upload(config):
        print_error("Failed at Step 0: S3 bucket creation/upload")
        print_cleanup_instructions()
        return False

    print()

    # Step 1: Deploy Cognito stack
    if not deploy_cognito_stack(config):
        print_error("Failed at Step 1: Cognito stack deployment")
        print_cleanup_instructions()
        return False

    print()

    # Step 2: Deploy Monitoring Agent
    if not deploy_monitoring_agent(config):
        print_error("Failed at Step 2: Monitoring Agent deployment")
        print_cleanup_instructions()
        return False

    print()

    # Step 3: Deploy Web Search Agent
    if not deploy_web_search_agent(config):
        print_error("Failed at Step 3: Web Search Agent deployment")
        print_cleanup_instructions()
        return False

    print()

    # Step 4: Deploy Host Agent
    if not deploy_host_agent(config):
        print_error("Failed at Step 4: Host Agent deployment")
        print_cleanup_instructions()
        return False

    print()
    print_header("Deployment Complete!")
    print_success("All stacks have been deployed successfully!")
    print_info("\nNext steps:")
    print_info(
        "1. Test individual agents: uv run test/connect_agent.py --agent <monitor|websearch|host>"
    )
    print_info(
        "2. Run the React frontend: cd frontend && npm install && ./setup-env.sh && npm run dev"
    )
    print_info("3. Use A2A Inspector or ADK Web for debugging")

    return True


def main():
    """Main entry point"""
    try:
        # Run pre-deployment checks
        checks_passed, account_id = run_pre_checks()
        if not checks_passed:
            sys.exit(1)

        # Collect parameters
        config = collect_deployment_parameters(account_id)

        # Display configuration
        display_configuration(config)

        # Confirm and save
        print_header("Save Configuration")
        confirm = get_input(
            "Save this configuration to .a2a.config? (yes/no)",
            default="yes",
            required=True,
        ).lower() in ["yes", "y"]

        if confirm:
            config_path = Path(".a2a.config")
            save_config(config, config_path)

            # Add to .gitignore
            gitignore_path = Path(".gitignore")
            gitignore_content = ""
            if gitignore_path.exists():
                with open(gitignore_path, "r") as f:
                    gitignore_content = f.read()

            if ".a2a.config" not in gitignore_content:
                with open(gitignore_path, "a") as f:
                    f.write("\n# A2A Deployment Configuration\n.a2a.config\n")
                print_success("Added .a2a.config to .gitignore")

            print()
            print_success("Configuration complete!")

            # Ask if user wants to deploy now
            print_header("Deploy Now?")
            deploy_now = get_input(
                "Do you want to start the deployment now? (yes/no)",
                default="yes",
                required=True,
            ).lower() in ["yes", "y"]

            if deploy_now:
                print()
                if run_deployment(config):
                    sys.exit(0)
                else:
                    sys.exit(1)
            else:
                print_info(
                    "\nDeployment skipped. You can run this script again to deploy."
                )
                print_info("Or manually run the AWS CLI commands for each stack.")

        else:
            print_warning("Configuration not saved. Exiting.")
            sys.exit(0)

    except KeyboardInterrupt:
        print_error("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print_error(f"An error occurred: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
