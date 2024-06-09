import requests
import logging
from django.conf import settings

from cloud_providers.services.shared import inspect_image
from cloud_providers.services.base import *

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class HetznerManager(BaseCloudManager):
    def __init__(self, os_username="root"):
        super().__init__(os_username)
        self.api_url = 'https://api.hetzner.cloud/v1'
        self.headers = {'Authorization': f'Bearer {settings.HETZNER_API_TOKEN}'}

    def serialize_instance(self, instance):
        return {
            "id": instance['id'],
            "name": instance['name'],
            "status": instance['status'],
            "creation_timestamp": instance['created'],
            "zone": instance['datacenter']['name'],
            "machine_type": instance['server_type']['name'],
            "network_ip": instance['private_net'][0]['ip'] if instance['private_net'] else None,
            "external_ip": instance['public_net']['ipv4']['ip'] if instance['public_net'] else None,
        }

    def list_instances(self):
        response = requests.get(f'{self.api_url}/servers', headers=self.headers)
        response.raise_for_status()
        serialized_instances = [self.serialize_instance(instance) for instance in response.json()['servers']]
        return serialized_instances

    def create_instance(self, name, server_type, os_image, ssh_key_id=None):
        data = {"name": name, "server_type": server_type, "image": os_image}
        if ssh_key_id:
            data["ssh_keys"] = [ssh_key_id]
        logger.info(f"Creating instance with data: {data}")
        response = requests.post(f'{self.api_url}/servers', headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def manage_instance(self, action, instance_id):
        response = requests.post(f'{self.api_url}/servers/{instance_id}/actions/{action}', headers=self.headers)
        response.raise_for_status()
        return response.json()

    def delete_instance(self, instance_id):
        response = requests.delete(f'{self.api_url}/servers/{instance_id}', headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_key_pairs(self):
        response = requests.get(f'{self.api_url}/ssh_keys', headers=self.headers)
        response.raise_for_status()
        return response.json()['ssh_keys']

    def manage_key_pair(self, action, key_id=None, data=None):
        url = f'{self.api_url}/ssh_keys'
        if action == 'create':
            response = requests.post(url, headers=self.headers, json=data)
        else:
            url = f'{url}/{key_id}'
            response = requests.delete(url, headers=self.headers) if action == 'delete' else requests.get(url, headers=self.headers)
        response.raise_for_status()
        if response.content:
            return response.json()
        return key_id

    def open_ports(self, server_id, ports):
        firewall_rules = [{"direction": "in", "source_ips": ["0.0.0.0/0", "::/0"], "port": "22", "protocol": "tcp"}]
        firewall_rules += [{"direction": "in", "source_ips": ["0.0.0.0/0", "::/0"], "port": str(port), "protocol": "tcp"} for port in ports]
        firewall_data = {"name": f"firewall-{server_id}", "apply_to": [{"type": "server", "server": {"id": server_id}}], "rules": firewall_rules}
        response = requests.post(f'{self.api_url}/firewalls', headers=self.headers, json=firewall_data)
        response.raise_for_status()
        return response.json()

    def create_docker_image_server(self, name, server_type, image, os_image, ssh_key_id, ssh_private_key_path=settings.SSH_PRIVATE_KEY):
        logger.info("Starting server creation process")
        server_info = self.create_instance(name, server_type, os_image, ssh_key_id)
        server_id = server_info['server']['id']
        ip_address = server_info['server']['public_net']['ipv4']['ip']
        root_password = server_info['root_password']

        logger.info("Waiting for SSH to become available")
        self.wait_for_ssh(ip_address, ssh_private_key_path)

        logger.info("Installing Docker on the server")
        self.install_docker(ip_address, ssh_private_key_path)

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

        logger.info(f"Inspecting Docker image {image}")
        ports = inspect_image(image)

        logger.info(f"Opening ports: {ports}")
        self.open_ports(server_id, ports + [80])

        logger.info(f"Running Docker container with image {image}")
        container_name = f"{image}-container".replace('/', '-').replace(':', '-').replace(' ', '')
        port_mappings = ' '.join([f'-p 80:{port}' for port in ports])
        run_container_command = f'docker run -d --name {container_name} {port_mappings} {image}'
        output, error = self.run_ssh_command(ip_address, run_container_command, ssh_private_key_path)
        if error:
            logger.error(f"Failed to start Docker container {container_name}: {error}")
            list_containers_command = 'docker ps --format "{{.Names}}"'
            output, error = self.run_ssh_command(ip_address, list_containers_command, ssh_private_key_path)
            if container_name in output:
                logger.info(f"Docker container {container_name} is running despite the error.")
            else:
                return {"error": f"Failed to start Docker container {container_name}"}
        return {"server_id": server_id, "ip_address": ip_address}

    # Placeholder methods for future implementations
    def list_buckets(self):
        pass

    def create_bucket(self, bucket_name, region):
        pass

    def delete_bucket(self, bucket_name):
        pass

    def upload_file(self, file_path, bucket_name, object_name):
        pass

    def download_file(self, bucket_name, object_name, file_path):
        pass

    def list_objects(self, bucket_name):
        pass

    def delete_object(self, bucket_name, object_name):
        pass

    def generate_presigned_url(self, bucket_name, object_name, expiration):
        pass
