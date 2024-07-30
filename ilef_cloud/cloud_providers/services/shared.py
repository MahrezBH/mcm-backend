import sys
import json
import subprocess


import docker
import json
from django.conf import settings


def inspect_image(image, username=settings.NEXUS_REGISTRY_USERNAME, password=settings.NEXUS_REGISTRY_PASSWORD):
    client = docker.from_env()
    print('new change')
    try:
        # Try to get the image locally
        image_info = client.images.get(image).attrs
    except docker.errors.ImageNotFound:
        # If the image is not found, pull it from the remote registry with authentication
        print(f"Image {image} not found locally. Pulling from remote registry...")
        auth_config = {
            'username': username,
            'password': password
        }
        image_info = client.images.pull(image, auth_config=auth_config).attrs
    except Exception as exception:
        # If the image is not found, pull it from the remote registry with authentication
        print(f'[error][inspect_image]: {exception}')
        print(f"Image {image} not found locally. Pulling from your dockerhub registry...")
        auth_config = {
            'username': settings.DOCKER_HUB_USERNAME,
            'password': settings.DOCKER_HUB_PASSWORD
        }
        image_info = client.images.pull(image, auth_config=auth_config).attrs
    ports = image_info.get('Config', {}).get('ExposedPorts', {})
    return [int(port.split('/')[0]) for port in ports]


def get_default_os_image(provider: str) -> dict:
    assert (provider in ('azure', 'aws', 'gcp', 'hetzner'))
    return {
        'gcp': {
            "image_family": "debian-11",
            "image_project": "debian-cloud"
        },
        'azure': {
            "publisher": "Canonical",
            "offer": "0001-com-ubuntu-server-jammy",
            "sku": "22_04-lts",
            "version": "latest"
        },
        'aws': {
            "image_id": "ami-04b70fa74e45c3917"
        },
        'hetzner': "ubuntu-22.04"
    }[provider]
