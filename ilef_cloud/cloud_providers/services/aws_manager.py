import boto3
from django.conf import settings
from django.utils.crypto import get_random_string
from cloud_providers.services.shared import inspect_image
from cloud_providers.services.base import BaseCloudManager, logger
import subprocess
import os
import yaml
import time


class AWSManager(BaseCloudManager):
    def __init__(self):
        super().__init__(os_username='ubuntu')
        self.session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.ec2 = self.session.client('ec2')
        self.s3 = self.session.client('s3')
        self.ce = self.session.client('ce')  # Cost Explorer client
        self.ec2_client = boto3.client('ec2',
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                       region_name=settings.AWS_REGION)
        self.eks_client = boto3.client('eks',
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                       region_name=settings.AWS_REGION)
        self.iam_client = boto3.client('iam',
                                       aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                       aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                       region_name=settings.AWS_REGION)
        self.cloudformation_client = boto3.client('cloudformation',
                                                  aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                                  aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                                                  region_name=settings.AWS_REGION)
        self.eks_cluster_role_arn = settings.AWS_EKS_CLUSTER_ROLE_ARN
        self.eks_node_role_arn = settings.AWS_EKS_NODE_ROLE_ARN

    def get_kubeconfig(self, cluster_name):
        kubeconfig_path = os.path.expanduser("~/.kube/config")
        cmd = [
            'aws', 'eks', 'update-kubeconfig',
            '--name', cluster_name,
            '--region', settings.AWS_REGION,
            '--kubeconfig', kubeconfig_path
        ]
        subprocess.run(cmd, check=True)
        return kubeconfig_path

    def get_service_external_ip(self, kubeconfig_path, namespace='default'):
        cmd = [
            'kubectl', '--kubeconfig', kubeconfig_path, 'get', 'svc', '-n', namespace, '-o', 'json'
        ]
        services = subprocess.check_output(cmd).decode('utf-8')
        services = yaml.safe_load(services)

        for service in services['items']:
            if service['spec']['type'] == 'LoadBalancer':
                if 'status' in service and 'loadBalancer' in service['status'] and 'ingress' in service['status']['loadBalancer']:
                    return service['status']['loadBalancer']['ingress'][0].get('hostname') or service['status']['loadBalancer']['ingress'][0].get('ip')

        return None

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

    def apply_yaml(self, kubeconfig_path, yaml_content):
        process = subprocess.Popen(['kubectl', '--kubeconfig', kubeconfig_path, 'apply', '-f', '-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=yaml_content.encode())
        if process.returncode != 0:
            print(f"Error applying YAML: {stderr.decode('utf-8')}")
            raise Exception(f"Error applying YAML: {stderr.decode('utf-8')}")
        print(f"YAML applied successfully: {stdout.decode('utf-8')}")

    def get_default_vpc_and_subnets(self):
        vpcs = self.ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])['Vpcs']
        if not vpcs:
            raise Exception("No default VPC found")
        default_vpc_id = vpcs[0]['VpcId']

        subnets = self.ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [default_vpc_id]}])['Subnets']
        subnet_ids = []
        availability_zones = set()

        for subnet in subnets:
            if len(availability_zones) >= 2:
                break
            if subnet['AvailabilityZone'] not in availability_zones:
                subnet_ids.append(subnet['SubnetId'])
                availability_zones.add(subnet['AvailabilityZone'])

        if len(availability_zones) < 2:
            raise Exception("Not enough availability zones for creating an EKS cluster")

        return default_vpc_id, subnet_ids

    def create_cluster(self, cluster_name, nodegroup_name, nodegroup_size, instance_types):
        vpc_id, subnet_ids = self.get_default_vpc_and_subnets()
        security_group_id = self.create_security_group(cluster_name, vpc_id)

        cluster = self.eks_client.create_cluster(
            name=cluster_name,
            version='1.23',  # Specify the latest supported version as needed
            roleArn=self.eks_cluster_role_arn,
            resourcesVpcConfig={
                'subnetIds': subnet_ids,
                'securityGroupIds': [security_group_id],
                'endpointPublicAccess': True
            }
        )

        waiter = self.eks_client.get_waiter('cluster_active')
        waiter.wait(name=cluster_name)

        nodegroup = self.create_nodegroup(cluster_name, nodegroup_name, nodegroup_size, subnet_ids, instance_types)
        return {"cluster": cluster, "nodegroup": nodegroup}

    def create_security_group(self, cluster_name, vpc_id):
        response = self.ec2_client.create_security_group(
            GroupName=f'{cluster_name}-sg',
            Description='EKS cluster security group',
            VpcId=vpc_id
        )
        security_group_id = response['GroupId']
        self.ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': '-1',
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )
        return security_group_id

    def create_nodegroup(self, cluster_name, nodegroup_name, nodegroup_size, subnet_ids, instance_types):
        nodegroup = self.eks_client.create_nodegroup(
            clusterName=cluster_name,
            nodegroupName=nodegroup_name,
            scalingConfig={
                'minSize': nodegroup_size['min'],
                'maxSize': nodegroup_size['max'],
                'desiredSize': nodegroup_size['desired']
            },
            diskSize=20,
            subnets=subnet_ids,
            instanceTypes=instance_types,
            amiType='AL2_x86_64',  # Amazon Linux 2
            nodeRole=self.eks_node_role_arn
        )

        waiter = self.eks_client.get_waiter('nodegroup_active')
        waiter.wait(clusterName=cluster_name, nodegroupName=nodegroup_name)

        return nodegroup

    def deploy_and_create_cluster(self, cluster_name, image_name, service_name, nodegroup_name, nodegroup_size, instance_types, container_port=5000):
        # Create EKS cluster and node group
        cluster_info = self.create_cluster(cluster_name, nodegroup_name, nodegroup_size, instance_types)
        kubeconfig_path = self.get_kubeconfig(cluster_name)

        # Generate and apply deployment YAML
        deployment_yaml_content = self.generate_deployment_yaml(image_name, container_port=container_port)
        print(f"Applying deployment YAML: {deployment_yaml_content}")
        self.apply_yaml(kubeconfig_path, deployment_yaml_content)

        # Generate and apply service YAML
        service_yaml_content = self.generate_service_yaml(service_name=service_name, container_port=container_port)
        print(f"Applying service YAML: {service_yaml_content}")
        self.apply_yaml(kubeconfig_path, service_yaml_content)

        # Retrieve the external IP
        external_ip = None
        for _ in range(5):
            try:
                external_ip = self.get_service_external_ip(kubeconfig_path, namespace='default')
                if external_ip:
                    break
            except Exception as e:
                print(f"Error getting external IP: {e}")
            print("Retrying in 15 seconds...")
            time.sleep(15)

        if not external_ip:
            raise Exception("Failed to get external IP for the service")

        return {"cluster_info": cluster_info, "kubeconfig_path": kubeconfig_path, "external_ip": external_ip}

    def list_clusters(self):
        clusters = self.eks_client.list_clusters()['clusters']
        cluster_details = [self.get_cluster_details(cluster_name) for cluster_name in clusters]
        return cluster_details

    def get_cluster_details(self, cluster_name):
        cluster = self.eks_client.describe_cluster(name=cluster_name)['cluster']

        kubeconfig_path = self.get_kubeconfig(cluster_name)
        external_ip = self.get_service_external_ip(kubeconfig_path)

        relevant_info = {
            "name": cluster.get("name"),
            "status": cluster.get("status"),
            "endpoint": cluster.get("endpoint"),
            "version": cluster.get("version"),
            "roleArn": cluster.get("roleArn"),
            "resourcesVpcConfig": cluster.get("resourcesVpcConfig"),
            "kubernetesNetworkConfig": cluster.get("kubernetesNetworkConfig"),
            "service_external_ip": external_ip
        }

        return relevant_info

    def delete_cluster(self, cluster_name):
        delete_operation = self.eks_client.delete_cluster(name=cluster_name)
        return delete_operation

    def _handle_response(self, response, key):
        return response.get(key, [])

    def serialize_instance(self, instance):
        return {
            "id": instance['InstanceId'],
            "name": instance['Tags'][0]['Value'] if 'Tags' in instance and instance['Tags'] else "Unnamed",
            "status": instance['State']['Name'],
            "creation_timestamp": instance['LaunchTime'].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "zone": instance['Placement']['AvailabilityZone'],
            "machine_type": instance['InstanceType'],
            "network_ip": instance['PrivateIpAddress'],
            "external_ip": instance['PublicIpAddress'] if 'PublicIpAddress' in instance else None
        }

    def list_instances(self):
        instances = self.ec2.describe_instances()
        serialized_instances = []
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                serialized_instances.append(self.serialize_instance(instance))
        return serialized_instances

    def manage_instance(self, action, instance_id):
        method = getattr(self.ec2, action)
        return method(InstanceIds=[instance_id])

    def create_instance(self, instance_type, key_name, min_count=1, max_count=1, image_id=None, security_group_id=None):
        if image_id is None:
            default_ami_ids = {
                'us-east-1': 'ami-0bb84b8ffd87024d8',
                'us-west-2': 'ami-0de53d8956e8dcf80',
            }
            image_id = default_ami_ids.get(settings.AWS_REGION)
            if not image_id:
                raise ValueError(f"No default Ubuntu 22.04 AMI ID found for region {settings.AWS_REGION}")

        response = self.ec2.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            KeyName=key_name,
            MinCount=min_count,
            MaxCount=max_count,
            SecurityGroupIds=[security_group_id] if security_group_id else []
        )
        return response

    def list_key_pairs(self):
        return self._handle_response(self.ec2.describe_key_pairs(), 'KeyPairs')

    def manage_key_pair(self, action, key_name):
        method = getattr(self.ec2, action)
        return method(KeyName=key_name)

    def list_buckets(self):
        return self._handle_response(self.s3.list_buckets(), 'Buckets')

    def manage_bucket(self, action, bucket_name, region=None):
        s3_client = self.session.client('s3', region_name=region) if region else self.s3
        method = getattr(s3_client, action)
        if action == 'create_bucket' and region != 'us-east-1':
            return method(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
        return method(Bucket=bucket_name)

    def manage_file(self, action, file_name, bucket_name, object_name=None):
        object_name = object_name or file_name
        method = getattr(self.s3, action)
        if action == 'upload_file':
            return method(file_name, bucket_name, object_name)
        if action == 'download_file':
            method(bucket_name, object_name, file_name)
            return {"message": "File downloaded successfully", "file_name": file_name}
        return method(Bucket=bucket_name, Key=object_name)

    def list_objects(self, bucket_name):
        return self._handle_response(self.s3.list_objects_v2(Bucket=bucket_name), 'Contents')

    def generate_presigned_url(self, bucket_name, object_name, expiration=3600):
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration
        )

    # def create_security_group(self, group_name, description, vpc_id):
    #     response = self.ec2.create_security_group(
    #         GroupName=group_name,
    #         Description=description,
    #         VpcId=vpc_id
    #     )
    #     return response['GroupId']

    def authorize_security_group_ingress(self, group_id, ports):
        ip_permissions = [
            {
                'IpProtocol': 'tcp',
                'FromPort': port,
                'ToPort': port,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
            for port in ports
        ]
        self.ec2.authorize_security_group_ingress(
            GroupId=group_id,
            IpPermissions=ip_permissions
        )

    def create_docker_image_server(self, image_id, instance_type, key_name, image, ssh_private_key, min_count=1, max_count=1):
        vpc_id = self.ec2.describe_vpcs()['Vpcs'][0]['VpcId']
        generated_code = get_random_string(3)
        security_group_id = self.create_security_group(
            f"{image}-{generated_code}-sg", f"Security group for {image} server #{generated_code}", vpc_id)
        ports = inspect_image(image)
        self.authorize_security_group_ingress(security_group_id, ports + [22, 80])

        response = self.create_instance(instance_type, key_name, min_count, max_count, image_id, security_group_id)
        instance_id = response['Instances'][0]['InstanceId']

        self.ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
        self.ec2.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])

        instance_info = self.ec2.describe_instances(InstanceIds=[instance_id])
        ip_address = instance_info['Reservations'][0]['Instances'][0]['PublicIpAddress']

        self.wait_for_ssh(ip_address, ssh_private_key)
        self.install_docker(ip_address, ssh_private_key)

        container_name = f"{image}-container".replace('/', '-').replace(':', '-').replace(' ', '')
        port_mappings = ' '.join([f'-p 80:{port}' for port in ports])
        run_container_command = f'sudo docker run -d --name {container_name} {port_mappings} {image}'
        output, error = self.run_ssh_command(ip_address, run_container_command, ssh_private_key)
        if error:
            logger.error(f"Failed to start Docker container {container_name}: {error}")
            list_containers_command = 'docker ps --format "{{.Names}}"'
            output, error = self.run_ssh_command(ip_address, list_containers_command, ssh_private_key)
            if container_name in output:
                logger.info(f"Docker container {container_name} is running despite the error.")
            else:
                return {"error": f"Failed to start Docker container {container_name}"}
        return {
            "instance_id": instance_id,
            "ip_address": ip_address
        }

    def get_cost_and_usage(self, start_date, end_date, granularity='MONTHLY', metrics=['UnblendedCost']):
        response = self.ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity=granularity,
            Metrics=metrics
        )
        return response['ResultsByTime']

    def get_cost_by_service(self, start_date, end_date):
        response = self.ce.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )
        return response['ResultsByTime']
