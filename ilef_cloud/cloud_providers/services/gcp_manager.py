import yaml
import os
from google.cloud import container_v1
import datetime
import sys
from typing import Any
from django.utils.crypto import get_random_string
from google.cloud import billing_v1
from google.oauth2 import service_account
from google.cloud import compute_v1, storage
from google.api_core.extended_operation import ExtendedOperation
from django.conf import settings
import logging
import time
from google.cloud import container_v1
import subprocess
from cloud_providers.services.base import BaseCloudManager, logger
from cloud_providers.services.shared import inspect_image


class GCPManager(BaseCloudManager):
    def __init__(self, os_username='ubuntu'):
        super().__init__(os_username)
        self.credentials = service_account.Credentials.from_service_account_file(settings.GCP_SERVICE_ACCOUNT_FILE)
        self.compute_client = compute_v1.InstancesClient(credentials=self.credentials)
        self.zone_operations_client = compute_v1.ZoneOperationsClient(credentials=self.credentials)
        self.project = settings.GCP_PROJECT_ID
        self.zone = settings.GCP_ZONE
        self.billing_client = billing_v1.CloudBillingClient(credentials=self.credentials)
        self.billing_account_id = settings.GCP_BILLING_ACCOUNT_ID
        self.os_username = os_username
        self.cluster_client = container_v1.ClusterManagerClient(credentials=self.credentials)
        self.location = f"projects/{self.project}/locations/{self.zone}"

    def list_instances(self):
        request = compute_v1.ListInstancesRequest(project=self.project, zone=self.zone)
        response = self.compute_client.list(request=request)
        return [instance for instance in response]

    def create_instance(self, name, machine_type, source_image, ssh_key):
        try:
            with open(ssh_key, 'r') as key_file:
                ssh_key = key_file.read().strip()
        except:
            logger.info("{} is not a path like file".format(ssh_key))

        instance = compute_v1.Instance(
            name=name,
            machine_type=f"zones/{self.zone}/machineTypes/{machine_type}",
            disks=[compute_v1.AttachedDisk(
                initialize_params=compute_v1.AttachedDiskInitializeParams(source_image=source_image),
                auto_delete=True,
                boot=True,
                type_="PERSISTENT"
            )],
            network_interfaces=[compute_v1.NetworkInterface(
                name="global/networks/default",
                access_configs=[compute_v1.AccessConfig(name="External NAT", type_="ONE_TO_ONE_NAT")]
            )],
            metadata={'items': [{'key': 'ssh-keys', 'value': f'{self.os_username}:{ssh_key}'}]}
        )

        insert_request = compute_v1.InsertInstanceRequest(project=self.project, zone=self.zone, instance_resource=instance)
        operation = self.compute_client.insert(request=insert_request)
        self._wait_for_operation(operation)

        logger.info("Instance created successfully")

        instance = self._wait_for_network_interfaces(name)
        return instance

    def manage_instance(self, action, instance_name):
        method = getattr(self.compute_client, action)
        operation = method(project=self.project, zone=self.zone, instance=instance_name)
        operation.result()
        return {"status": action}

    def terminate_instance(self, instance_name):
        return self.manage_instance('delete', instance_name)

    def list_buckets(self):
        storage_client = storage.Client(credentials=self.credentials, project=self.project)
        buckets = list(storage_client.list_buckets())
        return buckets

    def manage_bucket(self, action, bucket_name, location='US'):
        storage_client = storage.Client(credentials=self.credentials, project=self.project)
        if action == 'create_bucket':
            method = getattr(storage_client, action)
            bucket = storage_client.bucket(bucket_name)
            new_bucket = method(bucket, location=location)
            return new_bucket
        if action == 'delete_bucket':
            bucket = storage_client.bucket(bucket_name)
            bucket.delete()
            return {"status": "deleted"}

    def manage_file(self, action, file_path, bucket_name, object_name=None):
        storage_client = storage.Client(credentials=self.credentials, project=self.project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name or file_path)
        if action == 'upload_from_filename':
            blob.upload_from_filename(file_path)
            return {"status": "uploaded"}
        if action == 'download_to_filename':
            blob.download_to_filename(file_path)
            return {"status": "downloaded"}

    def list_objects(self, bucket_name):
        storage_client = storage.Client(credentials=self.credentials, project=self.project)
        blobs = list(storage_client.list_blobs(bucket_name))
        return blobs

    def delete_object(self, bucket_name, object_name):
        storage_client = storage.Client(credentials=self.credentials, project=self.project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.delete()
        return {"status": "deleted"}

    def generate_presigned_url(self, bucket_name, object_name, expiration=3600):
        storage_client = storage.Client(credentials=self.credentials, project=self.project)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        # Calculate the expiration time
        expiration_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=expiration)

        # Generate the signed URL
        url = blob.generate_signed_url(expiration=expiration_time, version='v4')
        return url

    def create_docker_image_server(self, name, machine_type, image, source_image, ssh_key_path=settings.SSH_PUBLIC_KEY, ssh_private_key_path=settings.SSH_PRIVATE_KEY):
        # Create the instance
        instance = self.create_instance(name, machine_type, source_image, ssh_key_path)

        # Get the public IP address of the instance
        ip_address = instance.network_interfaces[0].access_configs[0].nat_i_p

        # Wait for SSH to be available and install Docker on the instance
        self.wait_for_ssh(ip_address, ssh_private_key_path)
        self.install_docker(ip_address, ssh_private_key_path)

        # Inspect the image to get the necessary ports
        ports = inspect_image(image)

        # Create a firewall rule to allow traffic on the necessary ports
        network = instance.network_interfaces[0].network
        self.create_firewall_rule(f"firewall-{name}-{get_random_string(4).lower()}", network, list(map(str, ports)) + ["22", "80"])

        # Run the Docker container
        container_name = f"{name}_container"
        port_mappings = ' '.join([f'-p 80:{port}' for port in ports])
        run_container_command = f'sudo docker run -d --name {container_name} {port_mappings} {image}'
        output, error = self.run_ssh_command(ip_address, run_container_command, ssh_private_key_path)

        if error:
            logger.error(f"Failed to start Docker container {container_name}: {error}")
            list_containers_command = 'docker ps --format "{{.Names}}"'
            output, error = self.run_ssh_command(ip_address, list_containers_command, ssh_private_key_path)
            if container_name in output.strip():
                logger.info(f"Docker container {container_name} is running despite the error.")
            else:
                return {"error": f"Failed to start Docker container {container_name}"}
        return {"server_name": name, "ip_address": ip_address, "container_name": container_name}

    def create_firewall_rule(self, firewall_rule_name: str, network: str, ports) -> compute_v1.Firewall:
        firewall_rule = compute_v1.Firewall()
        firewall_rule.name = firewall_rule_name
        firewall_rule.direction = "INGRESS"

        allowed_ports = compute_v1.Allowed()
        allowed_ports.I_p_protocol = "tcp"
        allowed_ports.ports = ports

        firewall_rule.allowed = [allowed_ports]
        firewall_rule.source_ranges = ["0.0.0.0/0"]
        firewall_rule.network = network
        firewall_rule.description = f"Allowing TCP traffic on ports {ports} from Internet."

        firewall_client = compute_v1.FirewallsClient()
        operation = firewall_client.insert(
            project=self.project, firewall_resource=firewall_rule
        )

        self.wait_for_extended_operation(operation, "firewall rule creation")
        return firewall_client.get(project=self.project, firewall=firewall_rule_name)

    def _wait_for_operation(self, operation, verbose_name="operation"):
        while not operation.done:
            logger.info(f"Waiting for {verbose_name}...")
            time.sleep(1)
            operation = self.zone_operations_client.get(project=self.project, zone=self.zone, operation=operation.name)
        if operation.error:
            logger.error(f"Failed to complete {verbose_name}: {operation.error}")
            raise Exception(f"Failed to complete {verbose_name}: {operation.error}")

    def _wait_for_network_interfaces(self, name):
        for _ in range(10):
            instance = self.compute_client.get(project=self.project, zone=self.zone, instance=name)
            if instance.network_interfaces[0].network_i_p:
                return instance
            logger.info("Waiting for network interfaces to be ready...")
            time.sleep(5)
        raise Exception("Network interfaces not available after retries")

    def get_cost_and_usage(self, start_date, end_date):
        request = billing_v1.QueryUsageRequest(
            billing_account_name=f'billingAccounts/{self.billing_account_id}',
            filter={
                "start_time": start_date.isoformat() + 'Z',
                "end_time": end_date.isoformat() + 'Z',
                "granularity": "DAILY",
                "metrics": ["COST"]
            }
        )
        response = self.billing_client.query_usage(request=request)
        return response.usage

    def get_cost_by_service(self, start_date, end_date):
        request = billing_v1.QueryUsageRequest(
            billing_account_name=f'billingAccounts/{self.billing_account_id}',
            filter={
                "start_time": start_date.isoformat() + 'Z',
                "end_time": end_date.isoformat() + 'Z',
                "granularity": "DAILY",
                "metrics": ["COST"],
                "group_by": ["SERVICE"]
            }
        )
        response = self.billing_client.query_usage(request=request)
        return response.usage

    def wait_for_extended_operation(
            self, operation: ExtendedOperation, verbose_name: str = "operation", timeout: int = 300) -> Any:
        result = operation.result(timeout=timeout)

        if operation.error_code:
            print(
                f"Error during {verbose_name}: [Code: {operation.error_code}]: {operation.error_message}",
                file=sys.stderr,
                flush=True,
            )
            print(f"Operation ID: {operation.name}", file=sys.stderr, flush=True)
            raise operation.exception() or RuntimeError(operation.error_message)

        if operation.warnings:
            print(f"Warnings during {verbose_name}:\n", file=sys.stderr, flush=True)
            for warning in operation.warnings:
                print(f" - {warning.code}: {warning.message}", file=sys.stderr, flush=True)

        return result

    def create_gke_cluster(self, cluster_name, node_count=3, machine_type='n1-standard-1', disk_size_gb=20):
        cluster = {
            "name": cluster_name,
            "initial_node_count": node_count,
            "node_config": {
                "machine_type": machine_type,
                "disk_size_gb": disk_size_gb,
                "oauth_scopes": [
                    "https://www.googleapis.com/auth/devstorage.read_only",
                    "https://www.googleapis.com/auth/logging.write",
                    "https://www.googleapis.com/auth/monitoring",
                    "https://www.googleapis.com/auth/service.management.readonly",
                    "https://www.googleapis.com/auth/servicecontrol",
                    "https://www.googleapis.com/auth/trace.append"
                ]
            }
        }
        response = self.cluster_client.create_cluster(parent=self.location, cluster=cluster)
        return response

    def wait_for_cluster(self, cluster_name):
        cluster_location = f"projects/{self.project}/locations/{self.zone}/clusters/{cluster_name}"
        request = container_v1.GetClusterRequest(name=cluster_location)
        while True:
            cluster = self.cluster_client.get_cluster(request=request)
            if cluster.status == container_v1.Cluster.Status.RUNNING:
                break
            print(f"Waiting for cluster {cluster_name} to be ready...")
            time.sleep(30)
        print(f"Cluster {cluster_name} is ready.")

    def get_gke_credentials(self, cluster_name):
        self.wait_for_cluster(cluster_name)
        kubeconfig_path = os.path.expanduser("~/.kube/config")
        cmd = [
            'gcloud', 'container', 'clusters', 'get-credentials',
            cluster_name, '--zone', self.zone, '--project', self.project
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            print("Kubeconfig retrieved successfully.")
            return kubeconfig_path
        else:
            print(f"Failed to get GKE credentials: {result.stderr.decode('utf-8')}")
            raise Exception("Failed to get GKE credentials")

    def check_cluster_connectivity(self, kubeconfig_path):
        cmd = ['kubectl', '--kubeconfig', kubeconfig_path, 'cluster-info']
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            print("Successfully connected to the cluster.")
        else:
            print(f"Failed to connect to the cluster: {result.stderr.decode('utf-8')}")
            raise Exception("Cluster connectivity check failed.")

    def generate_deployment_yaml(self, image_name, deployment_name='myapp-deployment', container_port=5000):
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {'name': deployment_name},
            'spec': {
                'replicas': 3,
                'selector': {'matchLabels': {'app': deployment_name}},
                'template': {
                    'metadata': {'labels': {'app': deployment_name}},
                    'spec': {
                        'containers': [{
                            'name': deployment_name,
                            'image': image_name,
                            'ports': [{'containerPort': container_port}]
                        }]
                    }
                }
            }
        }
        return yaml.dump(deployment)

    def generate_service_yaml(self, service_name='myapp-service', deployment_name='myapp-deployment', service_port=80, container_port=5000):
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {'name': service_name},
            'spec': {
                'selector': {'app': deployment_name},
                'ports': [{'protocol': 'TCP', 'port': service_port, 'targetPort': container_port}],
                'type': 'LoadBalancer'
            }
        }
        return yaml.dump(service)

    def apply_yaml(self, kubeconfig_path, yaml_content, retries=5, delay=30):
        for attempt in range(retries):
            process = subprocess.Popen(['kubectl', '--kubeconfig', kubeconfig_path, 'apply', '-f', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate(input=yaml_content.encode())
            if process.returncode == 0:
                print(f"YAML applied successfully: {stdout.decode('utf-8')}")
                return
            print(f"Error applying YAML: {stderr.decode('utf-8')}")
            if 'Unable to connect to the server' in stderr.decode('utf-8'):
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception(f"Failed to apply YAML: {stderr.decode('utf-8')}")
        raise Exception(f"Failed to apply YAML after {retries} attempts: {stderr.decode('utf-8')}")

    def deploy_and_create_cluster(self, cluster_name, image_name, service_name, node_count=3, machine_type='n1-standard-1', container_port=5000):
        # Create GKE cluster
        self.create_gke_cluster(cluster_name, node_count=node_count, machine_type=machine_type, disk_size_gb=20)
        kubeconfig_path = self.get_gke_credentials(cluster_name)

        # Check cluster connectivity
        self.check_cluster_connectivity(kubeconfig_path)

        # Generate and apply deployment YAML
        deployment_yaml_content = self.generate_deployment_yaml(image_name, container_port=container_port)
        print(f"Applying deployment YAML: {deployment_yaml_content}")
        self.apply_yaml(kubeconfig_path, deployment_yaml_content)

        # Generate and apply service YAML
        service_yaml_content = self.generate_service_yaml(service_name=service_name, container_port=container_port)
        print(f"Applying service YAML: {service_yaml_content}")
        self.apply_yaml(kubeconfig_path, service_yaml_content)
        return {"cluster_name": cluster_name, "kubeconfig_path": kubeconfig_path}

    def delete_gke_cluster(self, cluster_name):
        cluster_location = f"projects/{self.project}/locations/{self.zone}/clusters/{cluster_name}"
        response = self.cluster_client.delete_cluster(name=cluster_location)
        return response
