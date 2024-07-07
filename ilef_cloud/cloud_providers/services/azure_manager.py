from kubernetes import client, config
import logging
from azure.mgmt.compute.models import InstanceViewTypes
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import NetworkInterfaceIPConfiguration
from azure.mgmt.storage.models import StorageAccountCreateParameters, Sku, Kind
from azure.mgmt.compute.models import OSProfile, LinuxConfiguration, SshConfiguration, SshPublicKey
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import requests
import time
import yaml
import paramiko
from django.conf import settings
from .base import BaseCloudManager, logger
from cloud_providers.services.shared import inspect_image
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.containerservice.models import ManagedCluster, ManagedClusterAgentPoolProfile, ContainerServiceNetworkProfile
from azure.mgmt.containerservice.models import ManagedCluster, ManagedClusterAgentPoolProfile, ManagedClusterServicePrincipalProfile, ContainerServiceNetworkProfile
import subprocess
import os

AZURE_STATUS_MAP = {
    'Provisioning': 'pending',
    'Running': 'running',
    'Succeeded': 'running',
    'Stopped': 'stopped',
    'Stopping': 'stopped',
    'Deallocating': 'stopped',
    'Deallocated': 'stopped'
}


class AzureManager(BaseCloudManager):
    def __init__(self, os_username='ubuntu'):
        self.os_username = os_username
        self.credentials = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET
        )
        self.subscription_id = settings.AZURE_SUBSCRIPTION_ID
        self.compute_client = ComputeManagementClient(self.credentials, self.subscription_id)
        self.storage_client = StorageManagementClient(self.credentials, self.subscription_id)
        self.resource_client = ResourceManagementClient(self.credentials, self.subscription_id)
        self.network_client = NetworkManagementClient(self.credentials, self.subscription_id)
        self.container_service_client = ContainerServiceClient(self.credentials, self.subscription_id)
        self.resource_group = settings.AZURE_RESOURCE_GROUP
        self.location = settings.AZURE_LOCATION
        self.credential = DefaultAzureCredential()
        self.cost_management_url = f"https://management.azure.com/subscriptions/{self.subscription_id}/providers/Microsoft.CostManagement/query?api-version=2021-10-01"

    def create_aks_cluster(self, cluster_name, node_count=3, vm_size='Standard_DS2_v2'):
        cluster = self.container_service_client.managed_clusters.begin_create_or_update(
            self.resource_group,
            cluster_name,
            ManagedCluster(
                location=self.location,
                dns_prefix=cluster_name,
                agent_pool_profiles=[
                    ManagedClusterAgentPoolProfile(
                        name='nodepool1',
                        count=node_count,
                        vm_size=vm_size,
                        os_type='Linux',
                        type='VirtualMachineScaleSets',
                        mode='System'
                    )
                ],
                enable_rbac=True,
                network_profile=ContainerServiceNetworkProfile(
                    network_plugin='azure',
                    load_balancer_sku='Standard'
                ),
                service_principal_profile=ManagedClusterServicePrincipalProfile(
                    client_id=settings.AZURE_CLIENT_ID,
                    secret=settings.AZURE_CLIENT_SECRET
                )
            )
        ).result()

        return cluster

    def get_aks_credentials(self, resource_group, cluster_name):
        retries = 5
        delay = 10
        kubeconfig_path = os.path.expanduser("~/.kube/config")
        for attempt in range(retries):
            try:
                cmd = [
                    'az', 'aks', 'get-credentials',
                    '--resource-group', resource_group,
                    '--name', cluster_name,
                    '--overwrite-existing'
                ]
                subprocess.run(cmd, check=True)
                print("Kubeconfig retrieved successfully.")
                return kubeconfig_path
            except subprocess.CalledProcessError as e:
                print(f"Error getting AKS credentials: {e}")
                if attempt < retries - 1:
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    raise Exception("Failed to get AKS credentials after multiple attempts.")

    def get_cluster_nodes(self, k8s_client):
        nodes = k8s_client.list_node()
        return [{
            "name": node.metadata.name,
            "status": node.status.conditions[-1].type,
            "addresses": [{
                "type": addr.type,
                "address": addr.address
            } for addr in node.status.addresses]
        } for node in nodes.items]

    def get_cluster_pods(self, k8s_client):
        pods = k8s_client.list_pod_for_all_namespaces(watch=False)
        return [{
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "node_name": pod.spec.node_name,
            "status": pod.status.phase
        } for pod in pods.items]

    def get_k8s_client(self, kubeconfig_path):
        config.load_kube_config(config_file=kubeconfig_path)
        return client.CoreV1Api()

    def generate_deployment_yaml(self, image_name, deployment_name='myapp-deployment', container_port=5000, image_pull_secret='my-registry-secret'):
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
                            'ports': [{'containerPort': int(container_port)}]  # Ensure containerPort is an integer
                        }],
                        'imagePullSecrets': [{'name': image_pull_secret}]
                    }
                }
            }
        }
        return yaml.dump(deployment)

    # def generate_deployment_yaml(self, image_name, deployment_name='myapp-deployment', container_port=5000):
    #     deployment = {
    #         'apiVersion': 'apps/v1',
    #         'kind': 'Deployment',
    #         'metadata': {'name': deployment_name},
    #         'spec': {
    #             'replicas': 3,
    #             'selector': {'matchLabels': {'app': deployment_name}},
    #             'template': {
    #                 'metadata': {'labels': {'app': deployment_name}},
    #                 'spec': {
    #                     'containers': [{
    #                         'name': deployment_name,
    #                         'image': image_name,
    #                         'ports': [{'containerPort': container_port}]
    #                     }]
    #                 }
    #             }
    #         }
    #     }
    #     return yaml.dump(deployment)

    def generate_service_yaml(self, service_name='myapp-service', deployment_name='myapp-deployment', service_port=80, container_port=5000):
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {'name': service_name},
            'spec': {
                'selector': {'app': deployment_name},
                'ports': [{'protocol': 'TCP', 'port': int(service_port), 'targetPort': int(container_port)}],  # Ensure targetPort is an integer
                'type': 'LoadBalancer'
            }
        }
        return yaml.dump(service)

    def apply_yaml(self, kubeconfig_path, yaml_content):
        process = subprocess.Popen(['kubectl', '--kubeconfig', kubeconfig_path, 'apply', '-f', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=yaml_content.encode())
        if process.returncode != 0:
            print(f"Error applying YAML: {stderr.decode('utf-8')}")
            raise Exception(f"Error applying YAML: {stderr.decode('utf-8')}")
        print(f"YAML applied successfully: {stdout.decode('utf-8')}")

    def deploy_and_create_cluster(self, cluster_name, image_name, service_name, node_count=3, vm_size='Standard_DS2_v2', container_port=5000, insecure_registry=None):
        # Create AKS cluster
        cluster = self.create_aks_cluster(cluster_name, node_count=node_count, vm_size=vm_size)
        kubeconfig_path = self.get_aks_credentials(self.resource_group, cluster_name)

        if insecure_registry:
            # Apply DaemonSet for insecure registries
            daemonset_yaml_content = self.generate_docker_config_daemonset_yaml(insecure_registry)
            print(f"Applying DaemonSet YAML: {daemonset_yaml_content}")
            self.apply_yaml(kubeconfig_path, daemonset_yaml_content)

        # Generate and apply deployment YAML
        deployment_yaml_content = self.generate_deployment_yaml(image_name, container_port=container_port)
        print(f"Applying deployment YAML: {deployment_yaml_content}")
        self.apply_yaml(kubeconfig_path, deployment_yaml_content)

        # Generate and apply service YAML
        service_yaml_content = self.generate_service_yaml(service_name=service_name, container_port=container_port)
        print(f"Applying service YAML: {service_yaml_content}")
        self.apply_yaml(kubeconfig_path, service_yaml_content)
        return {"cluster": cluster, "kubeconfig_path": kubeconfig_path}

    def generate_docker_config_daemonset_yaml(self, insecure_registry):
        daemonset_yaml = f"""
        apiVersion: apps/v1
        kind: DaemonSet
        metadata:
        name: docker-config
        namespace: kube-system
        spec:
        selector:
            matchLabels:
            name: docker-config
        template:
            metadata:
            labels:
                name: docker-config
        spec:
            containers:
            - name: docker-config
            image: busybox
            command:
            - sh
            - -c
            - |
                cp /tmp/daemon.json /etc/docker/daemon.json
                systemctl restart docker
            volumeMounts:
            - name: docker-config-volume
                mountPath: /tmp/daemon.json
                subPath: daemon.json
            securityContext:
                privileged: true
            hostNetwork: true
            hostPID: true
            volumes:
            - name: docker-config-volume
            configMap:
                name: docker-config
        ---
        apiVersion: v1
        kind: ConfigMap
        metadata:
        name: docker-config
        namespace: kube-system
        data:
        daemon.json: |
            {{
            "insecure-registries": ["{insecure_registry}"]
            }}
        """
        return daemonset_yaml

    def cordon_node(self, cluster_name, node_name):
        self.get_aks_credentials(self.resource_group, cluster_name)
        cmd = ['kubectl', 'cordon', node_name]
        subprocess.run(cmd, check=True)

    def drain_node(self, cluster_name, node_name):
        self.get_aks_credentials(self.resource_group, cluster_name)
        cmd = ['kubectl', 'drain', node_name, '--ignore-daemonsets', '--delete-local-data']
        subprocess.run(cmd, check=True)

    def uncordon_node(self, cluster_name, node_name):
        self.get_aks_credentials(self.resource_group, cluster_name)
        cmd = ['kubectl', 'uncordon', node_name]
        subprocess.run(cmd, check=True)

    def scale_down_node_pool(self, resource_group, cluster_name, nodepool_name, new_node_count):
        cmd = [
            'az', 'aks', 'nodepool', 'scale',
            '--resource-group', resource_group,
            '--cluster-name', cluster_name,
            '--name', nodepool_name,
            '--node-count', str(new_node_count)
        ]
        subprocess.run(cmd, check=True)

    # Additional methods to manage clusters
    def get_cluster(self, cluster_name):
        cluster = self.container_service_client.managed_clusters.get(
            self.resource_group,
            cluster_name
        )
        return self.get_cluster_details(cluster.name)

    def delete_cluster(self, cluster_name):
        delete_operation = self.container_service_client.managed_clusters.begin_delete(
            self.resource_group,
            cluster_name
        )
        return delete_operation.result()

    def get_service_external_ip(self, kubeconfig_path, namespace='default'):
        # Find the service with type LoadBalancer
        cmd = [
            'kubectl', '--kubeconfig', kubeconfig_path, 'get', 'svc', '-n', namespace, '-o', 'json'
        ]
        services = subprocess.check_output(cmd).decode('utf-8')
        services = yaml.safe_load(services)

        for service in services['items']:
            if service['spec']['type'] == 'LoadBalancer':
                if 'status' in service and 'loadBalancer' in service['status'] and 'ingress' in service['status']['loadBalancer']:
                    return service['status']['loadBalancer']['ingress'][0]['ip']

        return None

    def get_cluster_details(self, cluster_name):
        cluster = self.container_service_client.managed_clusters.get(self.resource_group, cluster_name)
        cluster_info = cluster.as_dict()

        # Get kubeconfig and service external IP
        kubeconfig_path = self.get_aks_credentials(self.resource_group, cluster_name)
        external_ip = self.get_service_external_ip(kubeconfig_path)

        # Get Kubernetes client and retrieve pods and nodes
        k8s_client = self.get_k8s_client(kubeconfig_path)
        # pods = self.get_cluster_pods(k8s_client)
        nodes = self.get_cluster_nodes(k8s_client)

        # Extract relevant information
        relevant_info = {
            "id": cluster_info.get("id"),
            "name": cluster_info.get("name"),
            "location": cluster_info.get("location"),
            "provisioning_state": cluster_info.get("provisioning_state"),
            "power_state": cluster_info.get("power_state", {}).get("code"),
            "kubernetes_version": cluster_info.get("kubernetes_version"),
            "dns_prefix": cluster_info.get("dns_prefix"),
            "fqdn": cluster_info.get("fqdn"),
            "agent_pool_profiles": [{
                "count": profile.get("count"),
                "vm_size": profile.get("vm_size"),
                "os_disk_size_gb": profile.get("os_disk_size_gb"),
                "os_type": profile.get("os_type"),
                "provisioning_state": profile.get("provisioning_state"),
                "power_state": profile.get("power_state", {}).get("code"),
                "name": profile.get("name")
            } for profile in cluster_info.get("agent_pool_profiles", [])],
            "node_resource_group": cluster_info.get("node_resource_group"),
            "enable_rbac": cluster_info.get("enable_rbac"),
            "network_profile": {
                "network_plugin": cluster_info.get("network_profile", {}).get("network_plugin"),
                "service_cidr": cluster_info.get("network_profile", {}).get("service_cidr"),
                "dns_service_ip": cluster_info.get("network_profile", {}).get("dns_service_ip"),
                "outbound_type": cluster_info.get("network_profile", {}).get("outbound_type"),
                "load_balancer_sku": cluster_info.get("network_profile", {}).get("load_balancer_sku")
            },
            "service_external_ip": external_ip,
            # "pods": pods,
            "nodes": nodes
        }

        return relevant_info

    def list_clusters(self):
        clusters = self.container_service_client.managed_clusters.list()
        return [self.get_cluster_details(cluster.name) for cluster in clusters]

    # Compute (VM) Methods

    def serialize_instance(self, instance):
        print(f'instance: {instance}')
        nic_id = instance.network_profile.network_interfaces[0].id
        network_interface = self.network_client.network_interfaces.get(
            self.resource_group, nic_id.split('/')[-1]
        )
        ip_config = network_interface.ip_configurations[0]

        public_ip_address = None
        if ip_config.public_ip_address:
            public_ip = self.network_client.public_ip_addresses.get(
                self.resource_group, ip_config.public_ip_address.id.split('/')[-1]
            )
            public_ip_address = public_ip.ip_address
        print(instance)
        return {
            "provider": "azure",
            "id": instance.id,
            "name": instance.name,
            "status": self.get_instance_status(instance),
            "created_at": instance.time_created,
            "zone": instance.location,
            "machine_type": instance.hardware_profile.vm_size,
            "network_ip": ip_config.private_ip_address,
            "external_ip": public_ip_address,
        }

    def get_instance_status(self, instance):
        instance_view = instance.instance_view
        if instance_view and instance_view.statuses:
            for status in instance_view.statuses:
                if 'PowerState' in status.code:
                    return self.map_to_unified_status(status.code)
        return self.map_to_unified_status(instance.provisioning_state)

    def map_to_unified_status(self, azure_status):
        status_mapping = {
            'PowerState/running': 'running',
            'PowerState/deallocated': 'stopped',
            'PowerState/deallocating': 'stopping',
            'PowerState/starting': 'starting',
            'PowerState/stopping': 'stopping',
            'PowerState/stopped': 'stopped',
            'PowerState/unknown': 'unknown',
            'Succeeded': 'running',
            'Failed': 'error',
            'Creating': 'creating',
            'Deleting': 'deleting'
        }
        return status_mapping.get(azure_status, 'unknown')

    def list_instances(self):
        instances = self.compute_client.virtual_machines.list_all()
        instances_details = []

        for instance in instances:
            instance_detail = self.compute_client.virtual_machines.get(
                resource_group_name=instance.id.split('/')[4],  # Extract resource group name from instance ID
                vm_name=instance.name,
                expand=InstanceViewTypes.instance_view
            )
            instances_details.append(self.serialize_instance(instance_detail))

        return instances_details

    def create_virtual_network(self, vnet_name, subnet_name):
        vnet_params = {
            'location': settings.AZURE_LOCATION,
            'address_space': {'address_prefixes': ['10.0.0.0/16']},
            'subnets': [{'name': subnet_name, 'address_prefix': '10.0.0.0/24'}]
        }
        async_vnet_creation = self.network_client.virtual_networks.begin_create_or_update(self.resource_group, vnet_name, vnet_params)
        return async_vnet_creation.result()

    def create_public_ip_address(self, public_ip_name):
        public_ip_params = {'location': settings.AZURE_LOCATION, 'public_ip_allocation_method': 'Dynamic'}
        async_public_ip_creation = self.network_client.public_ip_addresses.begin_create_or_update(self.resource_group, public_ip_name, public_ip_params)
        return async_public_ip_creation.result()

    def create_network_interface(self, nic_name, vnet_name, subnet_name, public_ip_name):
        subnet_info = self.network_client.subnets.get(self.resource_group, vnet_name, subnet_name)
        public_ip_info = self.create_public_ip_address(public_ip_name)
        ip_config = NetworkInterfaceIPConfiguration(
            name='ipconfig1', subnet=subnet_info, private_ip_allocation_method='Dynamic', public_ip_address=public_ip_info
        )
        nic_params = {'location': settings.AZURE_LOCATION, 'ip_configurations': [ip_config]}
        async_nic_creation = self.network_client.network_interfaces.begin_create_or_update(self.resource_group, nic_name, nic_params)
        return async_nic_creation.result()

    def create_instance(self, vm_name, vm_size, image_reference, admin_password=None, ssh_key=None, nic_name=None):
        nic_info = self.network_client.network_interfaces.get(self.resource_group, nic_name)
        os_profile = OSProfile(computer_name=vm_name, admin_username=self.os_username)
        if admin_password:
            os_profile.admin_password = admin_password
        elif ssh_key:
            try:
                with open(ssh_key, 'r') as ssh_file:
                    ssh_key_data = ssh_file.read()
            except:
                ssh_key_data = ssh_key
                logger.info("{} is not a path like file".format(ssh_key))

            os_profile.linux_configuration = LinuxConfiguration(
                disable_password_authentication=True,
                ssh=SshConfiguration(public_keys=[SshPublicKey(path=f'/home/{self.os_username}/.ssh/authorized_keys', key_data=ssh_key_data)])
            )
        else:
            raise ValueError("Either admin_password or ssh_key_path must be provided")

        params = {
            'location': settings.AZURE_LOCATION,
            'os_profile': os_profile,
            'hardware_profile': {'vm_size': vm_size},
            'storage_profile': {'image_reference': image_reference},
            'network_profile': {'network_interfaces': [{'id': nic_info.id, 'primary': True}]}
        }
        async_vm_creation = self.compute_client.virtual_machines.begin_create_or_update(self.resource_group, vm_name, params)
        return self.serialize_instance(async_vm_creation.result())

    def get_instance_info(self, vm_name):
        vm = self.compute_client.virtual_machines.get(self.resource_group, vm_name)

        # Get NIC ID from VM network profile
        nic_id = vm.network_profile.network_interfaces[0].id
        nic_name = nic_id.split('/')[-1]

        # Fetch the NIC details
        nic = self.network_client.network_interfaces.get(self.resource_group, nic_name)

        # Extract the internal IP address
        internal_ip = nic.ip_configurations[0].private_ip_address

        # Extract the public IP address
        public_ip_id = nic.ip_configurations[0].public_ip_address.id
        public_ip_name = public_ip_id.split('/')[-1]
        public_ip = self.network_client.public_ip_addresses.get(self.resource_group, public_ip_name).ip_address

        return {
            'internal_ip': internal_ip,
            'public_ip': public_ip
        }

    def manage_instance(self, action, vm_name):
        method = getattr(self.compute_client.virtual_machines, f"begin_{action}")
        async_vm_action = method(self.resource_group, vm_name)
        async_vm_action.result()

    def delete_instance(self, vm_name):
        try:
            # Get VM information
            vm = self.compute_client.virtual_machines.get(self.resource_group, vm_name)
            nic_id = vm.network_profile.network_interfaces[0].id
            disk_name = vm.storage_profile.os_disk.name

            # Delete the VM
            async_vm_delete = self.compute_client.virtual_machines.begin_delete(self.resource_group, vm_name)
            async_vm_delete.result()

            # Delete the OS disk
            async_disk_delete = self.compute_client.disks.begin_delete(self.resource_group, disk_name)
            async_disk_delete.result()

            # Get the NIC name from its ID
            nic_name = nic_id.split('/')[-1]

            # Delete the NIC
            async_nic_delete = self.network_client.network_interfaces.begin_delete(self.resource_group, nic_name)
            async_nic_delete.result()

            # Get the Public IP name associated with the NIC
            nic = self.network_client.network_interfaces.get(self.resource_group, nic_name)
            public_ip_id = nic.ip_configurations[0].public_ip_address.id
            public_ip_name = public_ip_id.split('/')[-1]

            # Delete the Public IP
            async_public_ip_delete = self.network_client.public_ip_addresses.begin_delete(self.resource_group, public_ip_name)
            async_public_ip_delete.result()

            return {"message": f"VM {vm_name} and its associated resources have been deleted."}
        except Exception as e:
            logger.error(f"Error deleting instance {vm_name}: {e}")
            return {"error": str(e)}

    # Storage Methods
    def serialize_bucket(self, bucket):
        return {
            "id": bucket['id'],
            "name": bucket['name'],
            "location": bucket['location'],
            "creation_time": bucket['creation_time'],
            "sku": bucket['sku'],
            "kind": bucket['kind'],
            "primary_endpoints": bucket['primary_endpoints']
        }

    def list_buckets(self):
        storage_accounts = self.storage_client.storage_accounts.list_by_resource_group(self.resource_group)
        serialized_buckets = []
        for account in storage_accounts:
            serialized_buckets.append(self.serialize_bucket(account.as_dict()))
        return serialized_buckets

    def list_objects(self, account_name, container_name=None):
        blob_service_client = self._get_blob_service_client(account_name)

        if container_name:
            container_client = blob_service_client.get_container_client(container_name)
            blobs = container_client.list_blobs()
            return [{"name": blob.name, "size": blob.size, "last_modified": blob.last_modified} for blob in blobs]
        else:
            containers = blob_service_client.list_containers()
            all_blobs = []
            for container in containers:
                container_client = blob_service_client.get_container_client(container.name)
                blobs = container_client.list_blobs()
                for blob in blobs:
                    print(blob)
                    all_blobs.append({
                        "container_name": container.name,
                        "name": blob.name,
                        "size": blob.size,
                        "last_modified": blob.last_modified
                    })
            return all_blobs

    def manage_bucket(self, action, account_name, location='eastus'):
        if action == 'create':
            params = StorageAccountCreateParameters(sku=Sku(name='Standard_LRS'), kind=Kind.STORAGE_V2, location=location)
            async_storage_creation = self.storage_client.storage_accounts.begin_create(self.resource_group, account_name, params)
            async_storage_creation.result()
        else:
            self.storage_client.storage_accounts.delete(self.resource_group, account_name)

    def manage_container(self, action, account_name, container_name):
        blob_service_client = self._get_blob_service_client(account_name)
        container_client = blob_service_client.get_container_client(container_name)
        if action == 'create':
            if not container_client.exists():
                container_client = blob_service_client.create_container(container_name)
        else:
            container_client.delete_container()
        return container_client

    def manage_file(self, action, account_name, container_name, file_path, blob_name):
        blob_service_client = self._get_blob_service_client(account_name)

        container_client = blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            self.manage_container('create', account_name, container_name)

        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        method = getattr(blob_client, action)
        if action == 'upload_blob':
            with open(file_path, "rb") as data:
                method(data)
            return {"message": f"File {file_path} uploaded to container {container_name} as {blob_name}"}
        else:
            with open(file_path, "wb") as download_file:
                download_file.write(method().readall())
            return {"status": "downloaded"}

    def delete_object(self, account_name, container_name, blob_name):
        blob_service_client = self._get_blob_service_client(account_name)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.delete_blob()
        return {"status": "deleted"}

    def _get_blob_service_client(self, account_name):
        account_url = f"https://{account_name}.blob.core.windows.net"
        return BlobServiceClient(account_url=account_url, credential=settings.AZURE_STORAGE_ACCOUNT_KEY)

    def generate_presigned_url(self, account_name, container_name, blob_name, expiration=3600):
        try:
            blob_service_client = self._get_blob_service_client(account_name)
            blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

            sas_token_expiry = datetime.utcnow() + timedelta(seconds=int(expiration))
            logging.info(f"SAS token expiry time: {sas_token_expiry}")

            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=container_name,
                blob_name=blob_name,
                account_key=settings.AZURE_STORAGE_ACCOUNT_KEY,
                permission=BlobSasPermissions(read=True),
                expiry=sas_token_expiry
            )

            sas_url = f"{blob_client.url}?{sas_token}"
            logging.info(f"Generated SAS URL: {sas_url}")

            return sas_url
        except Exception as e:
            logging.error(f"Error generating presigned URL: {e}")
            raise e

    def create_network_security_group(self, nsg_name, ports):
        security_rules = [
            {
                'name': f'allow-port-{port}',
                'protocol': 'Tcp',
                'source_port_range': '*',
                'destination_port_range': str(port),
                'source_address_prefix': '*',
                'destination_address_prefix': '*',
                'access': 'Allow',
                'priority': 1000 + index,
                'direction': 'Inbound'
            }
            for index, port in enumerate(ports)
        ]
        nsg_params = {'location': settings.AZURE_LOCATION, 'security_rules': security_rules}
        async_nsg_creation = self.network_client.network_security_groups.begin_create_or_update(self.resource_group, nsg_name, nsg_params)
        async_nsg_creation.result()

    def associate_nsg_with_subnet(self, vnet_name, subnet_name, nsg_name):
        subnet_info = self.network_client.subnets.get(self.resource_group, vnet_name, subnet_name)
        subnet_info.network_security_group = self.network_client.network_security_groups.get(self.resource_group, nsg_name)
        async_subnet_update = self.network_client.subnets.begin_create_or_update(self.resource_group, vnet_name, subnet_name, subnet_info)
        async_subnet_update.result()

    def run_docker_container(self, ip_address, image, ports, ssh_key_path):
        container_name = f"{image}-container".replace('/', '-').replace(':', '-').replace(' ', '')
        port_mappings = ' '.join([f'-p 80:{port}' for port in ports])
        run_container_command = f'sudo docker run -d --name {container_name} {port_mappings} {image}'
        output, error = self.run_ssh_command(ip_address, run_container_command, ssh_key_path)
        if error:
            logger.error(f"Failed to start Docker container {container_name}: {error}")
            list_containers_command = 'docker ps --format "{{.Names}}"'
            output, error = self.run_ssh_command(ip_address, list_containers_command, ssh_key_path)
            if container_name in output or output.strip() == container_name:
                logger.info(f"Docker container {container_name} is running despite the error.")
            else:
                return {"error": f"Failed to start Docker container {container_name}"}
        return {
            "ip_address": ip_address
        }

    def install_docker(self, ip_address, ssh_private_key_path):
        commands = [
            'sudo apt-get update -y',
            'sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io',
            'sudo systemctl start docker',
            f'sudo usermod -a -G docker {self.os_username}'
        ]
        for command in commands:
            output, error = self.run_ssh_command(ip_address, command, ssh_private_key_path)
            if error:
                print(f"Error installing Docker: {error}")
            else:
                print(f"Docker installation output: {output}")
        configure_docker_cmd = f'sudo mkdir -p /etc/docker && echo \'{{"insecure-registries":["{settings.NEXUS_REGISTRY_URL}:{settings.NEXUS_REGISTRY_DOCKER_PORT}"]}}\' | sudo tee /etc/docker/daemon.json && sudo systemctl restart docker'
        self.run_ssh_command(ip_address, configure_docker_cmd, ssh_private_key_path)
        docker_login_cmd = docker_login_cmd = f'echo {settings.NEXUS_REGISTRY_PASSWORD} | sudo docker login -u {settings.NEXUS_REGISTRY_USERNAME} --password-stdin {settings.NEXUS_REGISTRY_URL}:{settings.NEXUS_REGISTRY_DOCKER_PORT}'
        self.run_ssh_command(ip_address, docker_login_cmd, settings.SSH_PRIVATE_KEY)

    def get_access_token(self):
        token = self.credential.get_token("https://management.azure.com/.default")
        return token.token

    def get_cost_and_usage(self, start_date, end_date):
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json'
        }
        payload = {
            "type": "Usage",
            "timeframe": "Custom",
            "timePeriod": {"from": start_date, "to": end_date},
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ResourceGroup"}]
            }
        }
        response = requests.post(self.cost_management_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def get_cost_by_service(self, start_date, end_date):
        headers = {
            'Authorization': f'Bearer {self.get_access_token()}',
            'Content-Type': 'application/json'
        }
        payload = {
            "type": "Usage",
            "timeframe": "Custom",
            "timePeriod": {"from": start_date, "to": end_date},
            "dataset": {
                "granularity": "Daily",
                "aggregation": {"totalCost": {"name": "Cost", "function": "Sum"}},
                "grouping": [{"type": "Dimension", "name": "ServiceName"}]
            }
        }
        response = requests.post(self.cost_management_url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()

    def create_deploy_and_get_ip(self, cluster_name, image_name, service_name, container_port):
        insecure_registry = "{settings.NEXUS_REGISTRY_URL}:{settings.NEXUS_REGISTRY_DOCKER_PORT}"
        response = self.deploy_and_create_cluster(
            cluster_name=cluster_name,
            image_name=image_name,
            service_name=service_name,
            container_port=container_port,
            insecure_registry=insecure_registry

        )
        cluster = response["cluster"]
        kubeconfig_path = response["kubeconfig_path"]
        external_ip = self.get_service_external_ip(kubeconfig_path)
        return {"external_ip": external_ip, "cluster": cluster}
