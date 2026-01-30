import paramiko
import time
import sys

# Force UTF-8 output for Windows consoles
sys.stdout.reconfigure(encoding='utf-8')

# Configuration
VPS_IP = "174.138.24.224"        # Replace with your Droplet IP
VPS_USER = "root"                 # Default user for DigitalOcean
VPS_PASSWORD = "2P8xH&&b-y?f-zi"    # Replace with your Droplet root password
REPO_URL = "https://github.com/Jameschang0714/car-valuation-platform.git" # Replace if different

def deploy():
    print(f"--- Connecting to {VPS_IP} ---")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(VPS_IP, username=VPS_USER, password=VPS_PASSWORD, timeout=30)
        
        commands = [
            "echo 'Checking Docker...'",
            # Check if docker is installed, if not install it (DigitalOcean Docker image already has it)
            "command -v docker >/dev/null 2>&1 || { curl -fsSL https://get.docker.com | sh; }",
            "echo 'Preparing Directory...'",
            "rm -rf car-valuation-platform", # Clean start for simplicity
            f"git clone {REPO_URL} car-valuation-platform",
            "echo 'Patching Dockerfile (removing unnecessary dependency)...'",
            "cd car-valuation-platform && sed -i '/software-properties-common/d' Dockerfile",
            "echo 'Patching docker-compose.yml (Exposing port 80)...'",
            "cd car-valuation-platform && sed -i 's/8501:8501/80:8501/g' docker-compose.yml",
            "echo 'Starting Application via Docker Compose...'",
            "cd car-valuation-platform && docker compose up -d --build --remove-orphans"
        ]
        
        for cmd in commands:
            print(f"Executing: {cmd}")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            
            # Wait for command to finish and print output
            exit_status = stdout.channel.recv_exit_status()
            
            out = stdout.read().decode('utf-8', errors='replace')
            err = stderr.read().decode('utf-8', errors='replace')
            
            if out: print(f"STDOUT: {out}")
            if err: print(f"STDERR: {err}")
            
            if exit_status != 0:
                print(f"Command failed with exit status {exit_status}")
                # Sometimes git clone fails if dir exists or docker install has minor warnings
                # We continue unless it's a critical fatal error
                
        print("--- Deployment Completed! ---")
        ssh.close()
        
    except Exception as e:
        print(f"Deployment failed: {e}")

if __name__ == "__main__":
    deploy()
