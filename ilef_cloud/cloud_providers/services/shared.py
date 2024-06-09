import sys
import json
import subprocess


def inspect_image(image):
    result = subprocess.run(['docker', 'inspect', image], stdout=subprocess.PIPE)
    image_info = json.loads(result.stdout)
    ports = image_info[0].get('Config', {}).get('ExposedPorts', {})
    return [int(port.split('/')[0]) for port in ports]


def get_default_os_image(provider: str) -> dict:
    assert (provider in ('azure', 'aws', 'gcp', 'hetzner'))
    return {
        'gcp': {
            "image_family": "debian-10",
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
