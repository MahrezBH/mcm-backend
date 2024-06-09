from io import StringIO
from django.conf import settings
import paramiko
import logging
import time

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class BaseCloudManager:
    def __init__(self, os_username):
        self.os_username = os_username

    def run_ssh_command(self, ip_address, command, ssh_private_key_path):
        try:
            if '/' not in ssh_private_key_path:
                key = paramiko.RSAKey.from_private_key(StringIO.StringIO(ssh_private_key_path))
            else:
                key = paramiko.RSAKey.from_private_key_file()
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip_address, username=self.os_username, pkey=key)
            stdin, stdout, stderr = client.exec_command(command)
            stdout.channel.recv_exit_status()
            output = stdout.read().decode()
            error = stderr.read().decode()
            client.close()
            return output, error
        except Exception as e:
            logger.error(f"SSH command execution failed: {str(e)}")
            raise

    def wait_for_ssh(self, ip_address, ssh_private_key_path, retries=10, delay=10):
        for i in range(retries):
            try:
                logger.info(f"Checking SSH availability on {ip_address}, attempt {i + 1}/{retries}")
                self.run_ssh_command(ip_address, "echo SSH is available", ssh_private_key_path)
                logger.info("SSH is available")
                return
            except Exception as e:
                logger.info(f"SSH not available yet: {str(e)}")
                time.sleep(delay)
        raise Exception(f"SSH not available on {ip_address} after {retries * delay} seconds")

    def install_docker(self, ip_address, ssh_private_key_path):
        commands = [
            'sudo apt-get update -y',
            'sudo apt-get install -y docker.io',
            'sudo systemctl start docker',
            f'sudo usermod -a -G docker {self.os_username}'
        ]
        for command in commands:
            output, error = self.run_ssh_command(ip_address, command, ssh_private_key_path)
            if error:
                logger.error(f"Error installing Docker: {error}")
            else:
                logger.info(f"Docker installation output: {output}")

        # Configure Docker to use the insecure registry
        configure_docker_cmd = (
            f'sudo mkdir -p /etc/docker && '
            f'echo \'{{"insecure-registries":["{settings.NEXUS_REGISTRY_URL}:{settings.NEXUS_REGISTRY_DOCKER_PORT}"]}}\' '
            f'| sudo tee /etc/docker/daemon.json && sudo systemctl restart docker'
        )
        self.run_ssh_command(ip_address, configure_docker_cmd, ssh_private_key_path)

        docker_login_cmd = (
            f'echo {settings.NEXUS_REGISTRY_PASSWORD} | '
            f'sudo docker login -u {settings.NEXUS_REGISTRY_USERNAME} --password-stdin '
            f'{settings.NEXUS_REGISTRY_URL}:{settings.NEXUS_REGISTRY_DOCKER_PORT}'
        )
        self.run_ssh_command(ip_address, docker_login_cmd, ssh_private_key_path)

    def manage_instance(self, action, *args, **kwargs):
        raise NotImplementedError("This method should be overridden in the subclass.")

    def manage_key_pair(self, action, *args, **kwargs):
        raise NotImplementedError("This method should be overridden in the subclass.")

    def manage_bucket(self, action, *args, **kwargs):
        raise NotImplementedError("This method should be overridden in the subclass.")

    def manage_file(self, action, *args, **kwargs):
        raise NotImplementedError("This method should be overridden in the subclass.")
