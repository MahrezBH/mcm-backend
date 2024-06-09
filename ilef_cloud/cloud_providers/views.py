from django.utils.crypto import get_random_string
from datetime import datetime
from time import sleep
from django.utils import timezone
from cloud_providers.services.azure_manager import AzureManager
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

from cloud_providers.services.shared import get_default_os_image, inspect_image
from .models import KeyPair, CloudProvider, Storage, Instance
from .serializers import KeyPairSerializer, StorageSerializer
from cloud_providers.services.aws_manager import AWSManager
from cloud_providers.services.gcp_manager import GCPManager
from cloud_providers.services.hetzner_manager import HetznerManager
from ilef_cloud.response_utils import success_response, error_response
import os


class ListEC2Instances(APIView):
    def get(self, request):
        aws_manager = AWSManager()
        try:
            instances = aws_manager.list_instances()
            return success_response(instances)
        except Exception as e:
            return error_response(str(e))


class CreateEC2Instance(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        image_id = request.data.get('image_id')
        instance_type = request.data.get('instance_type')
        key_name = request.data.get('key_name')

        try:
            response = aws_manager.create_instance(instance_type, key_name, image_id=image_id)
            # instance_data = response['Instances'][0]
            # instance_id = instance_data['InstanceId']
            # state = instance_data['State']['Name']
            # private_ip = instance_data['PrivateIpAddress']
            # public_ip = instance_data.get('PublicDnsName', None)
            # instance_type = instance_data['InstanceType']
            # launch_time = instance_data['LaunchTime']
            # key_name = instance_data['KeyName']

            # provider, _ = CloudProvider.objects.get_or_create(name='aws')
            # instance = Instance.objects.create(
            #     provider=provider,
            #     instance_id=instance_id,
            #     instance_type=instance_type,
            #     status=state,
            #     created_at=launch_time,
            #     updated_at=launch_time,
            #     key_name=key_name,
            #     private_ip=private_ip,
            #     public_ip=public_ip
            # )
            # instance.save()
            return success_response(response, "Instance created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class StartEC2Instance(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        instance_id = request.data.get('instance_id')
        try:
            response = aws_manager.manage_instance('start_instances', instance_id)
            # instance = Instance.objects.get(instance_id=instance_id)
            # instance.status = response['StartingInstances'][0]['CurrentState']['Name']
            # instance.save()
            return success_response(response)
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class StopEC2Instance(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        instance_id = request.data.get('instance_id')
        try:
            response = aws_manager.manage_instance('stop_instances', instance_id)
            # instance = Instance.objects.get(instance_id=instance_id)
            # instance.status = response['StoppingInstances'][0]['CurrentState']['Name']
            # instance.save()
            return success_response(response)
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class TerminateEC2Instance(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        instance_id = request.data.get('instance_id')
        try:
            response = aws_manager.manage_instance('terminate_instances', instance_id)
            # instance = Instance.objects.get(instance_id=instance_id)
            # instance.status = response['TerminatingInstances'][0]['CurrentState']['Name']
            # instance.save()
            return success_response(response)
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class ListS3Buckets(APIView):
    def get(self, request):
        aws_manager = AWSManager()
        try:
            buckets = aws_manager.list_buckets()
            # provider = CloudProvider.objects.get(name='aws')
            # for bucket in buckets:
            #     Storage.objects.update_or_create(
            #         provider=provider,
            #         storage_id=bucket['Name'],
            #         defaults={
            #             'storage_type': 'S3',
            #             'created_at': bucket['CreationDate'],
            #             'location': f"http://{bucket['Name']}.s3.amazonaws.com/"
            #         }
            #     )
            # serializer = StorageSerializer(Storage.objects.filter(provider=provider), many=True)
            return success_response(buckets)
        except Exception as e:
            return error_response(str(e))


class CreateS3Bucket(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        bucket_name = request.data.get('bucket_name')
        region = request.data.get('region', 'us-east-1')
        try:
            response = aws_manager.manage_bucket('create_bucket', bucket_name, region)
            # provider = CloudProvider.objects.get(name='aws')
            # Storage.objects.create(
            #     provider=provider,
            #     storage_id=bucket_name,
            #     storage_type='S3',
            #     created_at=response['ResponseMetadata']['HTTPHeaders']['date'],
            #     location=response['Location']
            # )
            return success_response(response, "Bucket created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class DeleteS3Bucket(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        bucket_name = request.data.get('bucket_name')
        try:
            response = aws_manager.manage_bucket('delete_bucket', bucket_name)
            # provider = CloudProvider.objects.get(name='aws')
            # storage = Storage.objects.get(provider=provider, storage_id=bucket_name)
            # storage.delete()
            return success_response(response, "Bucket deleted successfully", status.HTTP_204_NO_CONTENT)
        except Storage.DoesNotExist:
            return error_response("Bucket not found in database")
        except Exception as e:
            return error_response(str(e))


class UploadFileToS3(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        aws_manager = AWSManager()
        file_obj = request.FILES['file']
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name', file_obj.name)

        file_path = os.path.join(settings.MEDIA_ROOT, file_obj.name)
        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

        try:
            response = aws_manager.manage_file('upload_file', file_path, bucket_name, object_name)
            os.remove(file_path)
            return success_response(response, "File uploaded successfully")
        except Exception as e:
            return error_response(str(e))


class DownloadFileFromS3(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name')
        file_name = request.data.get('file_name')
        try:
            response = aws_manager.manage_file('download_file', file_name, bucket_name, object_name)
            return success_response(response)
        except Exception as e:
            return error_response(str(e))


class ListS3Objects(APIView):
    def get(self, request):
        aws_manager = AWSManager()
        bucket_name = request.query_params.get('bucket_name')
        try:
            objects = aws_manager.list_objects(bucket_name)
            return success_response(objects)
        except Exception as e:
            return error_response(str(e))


class DeleteS3Object(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name')
        try:
            response = aws_manager.manage_file('delete_object', None, bucket_name, object_name)
            return success_response(response, "Object deleted successfully", status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return error_response(str(e))


class GeneratePresignedUrl(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name')
        expiration = request.data.get('expiration', 3600)
        try:
            url = aws_manager.generate_presigned_url(bucket_name, object_name, expiration)
            return success_response({'url': url})
        except Exception as e:
            return error_response(str(e))


class ListKeyPairs(APIView):
    def get(self, request):
        aws_manager = AWSManager()
        try:
            key_pairs = aws_manager.list_key_pairs()
            # provider = CloudProvider.objects.get(name='aws')
            # for key_pair in key_pairs:
            #     KeyPair.objects.update_or_create(
            #         provider=provider,
            #         key_pair_id=key_pair['KeyPairId'],
            #         defaults={
            #             'key_fingerprint': key_pair['KeyFingerprint'],
            #             'key_name': key_pair['KeyName'],
            #             'key_type': key_pair['KeyType'],
            #             'create_time': key_pair['CreateTime'],
            #         }
            #     )
            # serializer = KeyPairSerializer(KeyPair.objects.filter(provider=provider), many=True)
            return success_response(key_pairs)
        except Exception as e:
            return error_response(str(e))


class CreateKeyPair(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        key_name = request.data.get('key_name')
        try:
            key_pair = aws_manager.manage_key_pair('create_key_pair', key_name)
            # provider = CloudProvider.objects.get(name='aws')
            # KeyPair.objects.create(
            #     provider=provider,
            #     key_pair_id=key_pair['KeyPairId'],
            #     key_fingerprint=key_pair['KeyFingerprint'],
            #     key_name=key_pair['KeyName'],
            #     key_type=key_pair['KeyType'],
            #     create_time=key_pair['CreateTime']
            # )
            return success_response(key_pair, "Key pair created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class DeleteAWSKeyPair(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        key_name = request.data.get('key_name')
        try:
            response = aws_manager.manage_key_pair('delete_key_pair', key_name)
            # provider = CloudProvider.objects.get(name='aws')
            # key_pair = KeyPair.objects.get(provider=provider, key_name=key_name)
            # key_pair.delete()
            return success_response(response, "Key pair deleted successfully", status.HTTP_204_NO_CONTENT)
        except KeyPair.DoesNotExist:
            return error_response("Key pair not found")
        except Exception as e:
            return error_response(str(e))


class ListAWSClusters(APIView):
    def get(self, request):
        aws_manager = AWSManager()
        try:
            clusters = aws_manager.list_clusters()
            return Response(clusters, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAWSCluster(APIView):
    def get(self, request, cluster_name):
        aws_manager = AWSManager()
        try:
            cluster = aws_manager.get_cluster_details(cluster_name)
            return Response(cluster, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeleteAWSCluster(APIView):
    def delete(self, request, cluster_name):
        aws_manager = AWSManager()
        try:
            aws_manager.delete_cluster(cluster_name)
            return Response({"message": "Cluster deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateAndDeployAWSCluster(APIView):
    def post(self, request):
        aws_manager = AWSManager()
        cluster_name = request.data.get('cluster_name')
        image_name = request.data.get('image_name')
        service_name = request.data.get('service_name')
        nodegroup_name = request.data.get('nodegroup_name')
        nodegroup_size = request.data.get('nodegroup_size')
        instance_types = request.data.get('instance_types')
        container_port = request.data.get('container_port', 5000)

        if not all([cluster_name, image_name, service_name, nodegroup_name, nodegroup_size, instance_types]):
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = aws_manager.deploy_and_create_cluster(
                cluster_name, image_name, service_name, nodegroup_name, nodegroup_size, instance_types, container_port
            )
            return Response(result, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListHetznerInstances(APIView):
    def get(self, request):
        hetzner_manager = HetznerManager()
        try:
            instances = hetzner_manager.list_instances()
            return success_response(instances)
        except Exception as e:
            return error_response(str(e))


class CreateHetznerInstance(APIView):
    def post(self, request):
        hetzner_manager = HetznerManager()
        name = request.data.get('name')
        server_type = request.data.get('server_type')
        image = request.data.get('image')
        key_pair_name = request.data.get('key_pair_name')

        try:
            # key_pair = KeyPair.objects.get(key_name=key_pair_name)
            response = hetzner_manager.create_instance(name, server_type, image, key_pair_name)
            server_data = response['server']

            # instance_id = server_data['id']
            # status = server_data['status']
            # created_at = server_data['created']
            # public_ip = server_data['public_net']['ipv4']['ip']
            # private_ip = None
            # instance_type = server_data['server_type']['name']

            # provider, _ = CloudProvider.objects.get_or_create(name='hetzner')
            # instance = Instance.objects.create(
            #     provider=provider,
            #     instance_id=instance_id,
            #     instance_type=instance_type,
            #     status=status,
            #     created_at=created_at,
            #     updated_at=created_at,
            #     key_name=key_pair.key_name,
            #     private_ip=private_ip,
            #     public_ip=public_ip
            # )
            # instance.save()
            return success_response(server_data, "Instance created successfully", status.HTTP_201_CREATED)
        except KeyPair.DoesNotExist:
            return error_response("Key pair not found")
        except Exception as e:
            return error_response(str(e))


class StartHetznerInstance(APIView):
    def post(self, request):
        hetzner_manager = HetznerManager()
        instance_id = request.data.get('instance_id')

        try:
            response = hetzner_manager.manage_instance('poweron', instance_id)
            action_data = response['action']
            # current_state = action_data['status']

            # instance = Instance.objects.get(instance_id=instance_id)
            # instance.status = current_state
            # instance.save()
            return success_response(action_data)
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class StopHetznerInstance(APIView):
    def post(self, request):
        hetzner_manager = HetznerManager()
        instance_id = request.data.get('instance_id')

        try:
            response = hetzner_manager.manage_instance('shutdown', instance_id)
            action_data = response['action']
            # current_state = action_data['status']

            # instance = Instance.objects.get(instance_id=instance_id)
            # instance.status = current_state
            # instance.save()
            return success_response(action_data)
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class TerminateHetznerInstance(APIView):
    def post(self, request):
        hetzner_manager = HetznerManager()
        instance_id = request.data.get('instance_id')

        try:
            response = hetzner_manager.delete_instance(instance_id)
            # instance = Instance.objects.get(instance_id=instance_id)
            # instance.status = 'terminated'
            # instance.save()
            return success_response(response)
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class ListHetznerKeyPairs(APIView):
    def get(self, request):
        hetzner_manager = HetznerManager()
        try:
            key_pairs = hetzner_manager.list_key_pairs()
            return success_response(key_pairs)
        except Exception as e:
            return error_response(str(e))


class CreateHetznerKeyPair(APIView):
    def post(self, request):
        hetzner_manager = HetznerManager()
        name = request.data.get('name')
        public_key = request.data.get('public_key')

        try:
            data = {'name': name, 'public_key': public_key}
            key_pair = hetzner_manager.manage_key_pair('create', data=data)
            # provider, _ = CloudProvider.objects.get_or_create(name='hetzner')
            # KeyPair.objects.create(
            #     provider=provider,
            #     key_pair_id=key_pair['id'],
            #     key_fingerprint=key_pair['fingerprint'],
            #     key_name=key_pair['name'],
            #     public_key=key_pair['public_key'],
            #     create_time=key_pair['created']
            # )
            return success_response(key_pair, "Key pair created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class DeleteHetznerKeyPair(APIView):
    def post(self, request):
        hetzner_manager = HetznerManager()
        key_id = request.data.get('key_id')

        try:
            response = hetzner_manager.manage_key_pair('delete', key_id=key_id)
            print(response)
            return success_response(response, "Key pair deleted successfully", status.HTTP_204_NO_CONTENT)
        except KeyPair.DoesNotExist:
            return error_response("Key pair not found")
        except Exception as e:
            return error_response(str(e))


class ListGCPInstances(APIView):
    def get(self, request):
        gcp_manager = GCPManager()
        try:
            instances = gcp_manager.list_instances()
            # Convert instances to a JSON serializable format
            serialized_instances = [self.serialize_instance(instance) for instance in instances]
            return success_response(serialized_instances)
        except Exception as e:
            return error_response(str(e))

    def serialize_instance(self, instance):
        # Extract relevant fields from the instance object
        return {
            "id": instance.id,
            "name": instance.name,
            "status": instance.status,
            "creation_timestamp": instance.creation_timestamp,
            "zone": instance.zone,
            "machine_type": instance.machine_type,
            "network_ip": instance.network_interfaces[0].network_i_p if instance.network_interfaces else None,
            "external_ip": instance.network_interfaces[0].access_configs[0].nat_i_p if instance.network_interfaces and instance.network_interfaces[0].access_configs else None,
        }


class CreateGCPInstance(APIView):
    def post(self, request):
        server_name = request.data.get('server_name')
        server_type = request.data.get('server_type')
        os_image = request.data.get('os_image')
        ssh_key_path = request.data.get('ssh_key_path')
        if not os_image:
            os_image = {
                "image_family": "debian-10",
                "image_project": "debian-cloud"
            }
        if not ssh_key_path:
            ssh_key_path = settings.SSH_PUBLIC_KEY
        if not all([server_name, server_type, os_image, ssh_key_path]):
            return error_response("Missing required parameters", status.HTTP_400_BAD_REQUEST)

        image_family = os_image.get('image_family')
        image_project = os_image.get('image_project')

        try:
            manager = GCPManager()
            instance = manager.create_instance(
                server_name, server_type, f"projects/{image_project}/global/images/family/{image_family}",
                ssh_key_path)
            serialized_instance = self.serialize_instance(instance)
            return success_response(serialized_instance, "Instance created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))

    def serialize_instance(self, instance):
        return {
            "id": instance.id,
            "name": instance.name,
            "status": instance.status,
            "creation_timestamp": instance.creation_timestamp.isoformat() if isinstance(instance.creation_timestamp, datetime) else instance.creation_timestamp,
            "zone": instance.zone,
            "machine_type": instance.machine_type,
            "network_ip": instance.network_interfaces[0].network_i_p if instance.network_interfaces else None,
            "external_ip": instance.network_interfaces[0].access_configs[0].nat_i_p if instance.network_interfaces and instance.network_interfaces[0].access_configs else None
        }


class StartGCPInstance(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        instance_name = request.data.get('instance_name')

        try:
            response = gcp_manager.manage_instance('start', instance_name)
            return success_response(response, "Instance started successfully")
        except Exception as e:
            return error_response(str(e))


class StopGCPInstance(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        instance_name = request.data.get('instance_name')

        try:
            response = gcp_manager.manage_instance('stop', instance_name)
            return success_response(response, "Instance stopped successfully")
        except Exception as e:
            return error_response(str(e))


class TerminateGCPInstance(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        instance_name = request.data.get('instance_name')

        try:
            response = gcp_manager.terminate_instance(instance_name)
            return success_response(response, "Instance terminated successfully")
        except Exception as e:
            return error_response(str(e))


class ListGCPBuckets(APIView):
    def get(self, request):
        gcp_manager = GCPManager()
        try:
            buckets = gcp_manager.list_buckets()
            buckets_info = [{
                "name": bucket.name,
                "location": bucket.location,
                "time_created": bucket.time_created,
                "storage_class": bucket.storage_class,
                "id": bucket.id,
                "self_link": bucket.self_link,
                "project_number": bucket.project_number
            } for bucket in buckets]
            return success_response(buckets_info)
        except Exception as e:
            return error_response(str(e))


class CreateGCPBucket(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        bucket_name = request.data.get('bucket_name')
        location = request.data.get('location', 'US')

        if not bucket_name:
            return error_response("Bucket name is required", status.HTTP_400_BAD_REQUEST)

        try:
            bucket = gcp_manager.manage_bucket('create_bucket', bucket_name, location)
            bucket_info = {
                "name": bucket.name,
                "location": bucket.location,
                "time_created": bucket.time_created,
                "storage_class": bucket.storage_class,
                "id": bucket.id,
                "self_link": bucket.self_link,
                "project_number": bucket.project_number
            }
            return success_response(bucket_info, "Bucket created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class DeleteGCPBucket(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        bucket_name = request.data.get('bucket_name')
        try:
            response = gcp_manager.manage_bucket('delete_bucket', bucket_name)
            return success_response(response, "Bucket deleted successfully", status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return error_response(str(e))


class UploadFileToGCP(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        gcp_manager = GCPManager()
        file_obj = request.FILES['file']
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name', file_obj.name)

        file_path = os.path.join(settings.MEDIA_ROOT, file_obj.name)
        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)
        try:
            response = gcp_manager.manage_file('upload_from_filename', file_path, bucket_name, object_name)
            # os.remove(file_path)
            return success_response(response, "File uploaded successfully")
        except Exception as e:
            return error_response(str(e))


class DownloadFileFromGCP(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name')
        file_name = request.data.get('file_name')

        file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        try:
            response = gcp_manager.manage_file('download_to_filename', file_path, bucket_name, object_name)
            return success_response(response)
        except Exception as e:
            return error_response(str(e))


class ListGCPObjects(APIView):
    def get(self, request):
        gcp_manager = GCPManager()
        bucket_name = request.query_params.get('bucket_name')

        if not bucket_name:
            return error_response("No bucket name provided", status.HTTP_400_BAD_REQUEST)

        try:
            objects = gcp_manager.list_objects(bucket_name)
            serialized_objects = [self.serialize_object(obj) for obj in objects]
            return success_response(serialized_objects)
        except Exception as e:
            return error_response(str(e))

    def serialize_object(self, obj):
        return {
            "name": obj.name,
            "size": obj.size,
            "content_type": obj.content_type,
            "time_created": obj.time_created,
            "updated": obj.updated,
            "storage_class": obj.storage_class,
            "id": obj.id,
            "self_link": obj.self_link
        }


class DeleteGCPObject(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name')

        if not bucket_name:
            return error_response("No bucket name provided", status.HTTP_400_BAD_REQUEST)
        if not object_name:
            return error_response("No object name provided", status.HTTP_400_BAD_REQUEST)

        try:
            response = gcp_manager.delete_object(bucket_name, object_name)
            return success_response(response, "Object deleted successfully", status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return error_response(str(e))


class GenerateGCPPresignedUrl(APIView):
    def post(self, request):
        gcp_manager = GCPManager()
        bucket_name = request.data.get('bucket_name')
        object_name = request.data.get('object_name')
        expiration = request.data.get('expiration', 3600)

        if not bucket_name:
            return error_response("No bucket name provided", status.HTTP_400_BAD_REQUEST)
        if not object_name:
            return error_response("No object name provided", status.HTTP_400_BAD_REQUEST)

        try:
            url = gcp_manager.generate_presigned_url(bucket_name, object_name, expiration)
            return success_response({'url': url})
        except Exception as e:
            return error_response(str(e))


class RetrieveCosts(APIView):
    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        aws_manager = AWSManager()
        gcp_manager = GCPManager()

        costs = []

        try:
            aws_costs = aws_manager.get_cost_and_usage(start_date, end_date)
            for cost in aws_costs:
                costs.append({
                    'provider': 'AWS',
                    'amount': cost['Total']['UnblendedCost']['Amount'],
                    'currency': cost['Total']['UnblendedCost']['Unit'],
                    'date': cost['TimePeriod']['End'],
                    'resource_type': 'Compute'
                })

            gcp_costs = gcp_manager.get_cost_and_usage(start_date, end_date)
            for cost in gcp_costs:
                costs.append({
                    'provider': 'GCP',
                    'amount': cost['Total']['Amount'],
                    'currency': cost['Total']['Unit'],
                    'date': cost['Date'],
                    'resource_type': 'Compute'
                })

            return success_response(costs)
        except Exception as e:
            return error_response(str(e))


class DeployDockerImage(APIView):
    def post(self, request):
        provider = request.data.get('provider')
        server_name = request.data.get('server_name')
        server_type = request.data.get('server_type')
        os_image = request.data.get('os_image', get_default_os_image(provider))
        image = request.data.get('image')
        ssh_key_id = request.data.get('ssh_key_id', settings.SSH_PUBLIC_KEY)
        ssh_private_key = settings.SSH_PRIVATE_KEY
        ports = request.data.get('ports', inspect_image(image))
        if not all([provider, server_name, server_type, os_image, image]):
            return error_response("Missing required parameters", status.HTTP_400_BAD_REQUEST)

        try:
            if provider == 'hetzner':
                manager = HetznerManager()
                response = manager.create_docker_image_server(server_name, server_type, image, os_image, ssh_key_id)
            elif provider == 'gcp':
                image_family = os_image.get('image_family')
                image_project = os_image.get('image_project')
                manager = GCPManager()
                source_image = f"projects/{image_project}/global/images/family/{image_family}"
                response = manager.create_docker_image_server(
                    server_name, server_type, image, source_image)
            elif provider == 'aws':
                image_id = os_image.get('image_id')
                manager = AWSManager()
                response = manager.create_docker_image_server(
                    image_id=image_id,
                    instance_type=server_type,
                    key_name=ssh_key_id,
                    image=image,
                    ssh_private_key=settings.AWS_SSH_PRIVATE_KEY
                )
            elif provider == 'azure':
                image_reference = {
                    'publisher': os_image.get('publisher', 'Canonical'),
                    'offer': os_image.get('offer', '0001-com-ubuntu-server-jammy'),
                    'sku': os_image.get('sku', '22_04-lts'),
                    'version': os_image.get('version', 'latest')
                }
                manager = AzureManager()
                vnet_name = 'my-vnet'
                subnet_name = 'my-subnet'
                nsg_name = 'my-nsg'
                nic_name = f'{server_name}-nic'
                public_ip_name = f'{server_name}-ip'

                # Create network resources
                manager.create_virtual_network(vnet_name, subnet_name)
                manager.create_network_security_group(nsg_name, ports+[22, 80])
                manager.associate_nsg_with_subnet(vnet_name, subnet_name, nsg_name)
                manager.create_network_interface(nic_name, vnet_name, subnet_name, public_ip_name)

                # Create VM with the specified image
                manager.create_instance(server_name, server_type, image_reference, None, ssh_key_id, nic_name=nic_name)

                # Get public IP address of the VM
                public_ip_info = manager.network_client.public_ip_addresses.get(
                    manager.resource_group, public_ip_name)
                public_ip_address = public_ip_info.ip_address
                sleep(2)
                # Install Docker and run the container
                manager.install_docker(public_ip_address, ssh_private_key)
                response = manager.run_docker_container(
                    public_ip_address, image, ports, ssh_private_key)
            else:
                return error_response("Invalid provider", status.HTTP_400_BAD_REQUEST)

            return success_response(response, "Docker image deployed successfully", status.HTTP_200_OK)
        except Exception as e:
            return error_response(str(e))


class DeployDockerImageToCluster(APIView):
    def post(self, request):
        provider = request.data.get('provider')
        docker_image = request.data.get('image')
        docker_image_name = docker_image.split('/')[-1].replace('/', '-').replace(':', '-').replace('_', '-')
        cluster_name = request.data.get('cluster_name', f'cluster-{docker_image_name}-{get_random_string(4)}')
        service_name = request.data.get('service_name')
        if not service_name:
            service_name = f'service'
        deployment_yaml = request.data.get('deployment_yaml')
        service_yaml = request.data.get('service_yaml')
        ports = inspect_image(image=docker_image)
        if not all([provider, cluster_name, docker_image, service_name]):
            return Response({"error": "Missing required parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if provider == 'hetzner':
                manager = HetznerManager()
                response = manager.deploy_to_cluster(cluster_name, deployment_yaml, service_yaml)
            elif provider == 'gcp':
                manager = GCPManager()
                response = manager.deploy_to_cluster(cluster_name, deployment_yaml, service_yaml)
            elif provider == 'aws':
                manager = AWSManager()
                response = manager.deploy_to_cluster(cluster_name, deployment_yaml, service_yaml)
            elif provider == 'azure':
                manager = AzureManager()
                response = manager.create_deploy_and_get_ip(
                    cluster_name=cluster_name,
                    image_name=docker_image,
                    service_name=service_name,
                    container_port=ports[0]
                )
            else:
                return Response({"error": "Invalid provider"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Docker image deployed successfully", "response": response}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ListAzureInstances(APIView):
    def get(self, request):
        azure_manager = AzureManager()
        try:
            instances = azure_manager.list_instances()
            return success_response(instances)
        except Exception as e:
            return error_response(str(e))


class CreateAzureInstance(APIView):
    def post(self, request):
        vm_name = request.data.get('server_name')
        vm_size = request.data.get('server_type')
        image_reference = request.data.get('image_reference')
        # admin_username = request.data.get('admin_username', 'ubuntu')
        admin_password = request.data.get('admin_password', None)
        ssh_key = request.data.get('ssh_key_path', settings.SSH_PUBLIC_KEY)
        vnet_name = 'my-vnet'
        subnet_name = 'my-subnet'
        nsg_name = 'my-nsg'
        nic_name = f'{vm_name}-nic'
        public_ip_name = f'{vm_name}-ip'
        if not image_reference:
            image_reference = {
                'publisher': 'Canonical',
                'offer': '0001-com-ubuntu-server-jammy',
                'sku': '22_04-lts',
                'version': 'latest'
            }
        if not any([admin_password, ssh_key]):
            return error_response("Either admin_password or ssh_key_path must be provided", status.HTTP_400_BAD_REQUEST)

        try:
            azure_manager = AzureManager()

            # Create network resources
            azure_manager.create_virtual_network(vnet_name, subnet_name)
            azure_manager.create_network_security_group(nsg_name, ports=[22, 80])
            azure_manager.associate_nsg_with_subnet(vnet_name, subnet_name, nsg_name)
            azure_manager.create_network_interface(nic_name, vnet_name, subnet_name, public_ip_name)

            # Create VM
            azure_manager.create_instance(
                vm_name, vm_size, image_reference, admin_password, ssh_key, nic_name=nic_name)
            instance = azure_manager.get_instance_info(vm_name)
            return success_response(instance, "VM created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class StartAzureInstance(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        vm_name = request.data.get('instance_name')

        try:
            azure_manager.manage_instance('start', vm_name=vm_name)
            # instance = Instance.objects.get(instance_id=vm_name)
            # instance.status = "running"
            # instance.save()
            return success_response({}, "Instance started successfully")
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class StopAzureInstance(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        vm_name = request.data.get('instance_name')

        try:
            azure_manager.manage_instance('power_off', vm_name=vm_name)
            # instance = Instance.objects.get(instance_id=vm_name)
            # instance.status = "stopped"
            # instance.save()
            return success_response({}, "Instance stopped successfully")
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class TerminateAzureInstance(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        vm_name = request.data.get('instance_name')

        try:
            azure_manager.delete_instance(vm_name=vm_name)
            # instance = Instance.objects.get(instance_id=vm_name)
            # instance.status = 'terminated'
            # instance.save()
            return success_response({}, "Instance terminated successfully")
        except Instance.DoesNotExist:
            return error_response("Instance not found")
        except Exception as e:
            return error_response(str(e))


class ListAzureBuckets(APIView):
    def get(self, request):
        azure_manager = AzureManager()
        try:
            buckets = azure_manager.list_buckets()
            return success_response(buckets)
        except Exception as e:
            return error_response(str(e))


class CreateAzureBucket(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        account_name = request.data.get('account_name')
        location = request.data.get('location', 'eastus')

        try:
            azure_manager.manage_bucket('create', account_name, location)
            return success_response({}, "Bucket created successfully", status.HTTP_201_CREATED)
        except Exception as e:
            return error_response(str(e))


class DeleteAzureBucket(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        account_name = request.data.get('account_name')

        try:
            azure_manager.manage_bucket('delete', account_name)
            # provider = CloudProvider.objects.get(name='azure')
            # storage = Storage.objects.get(provider=provider, storage_id=account_name)
            # storage.delete()
            return success_response({}, "Bucket deleted successfully", status.HTTP_204_NO_CONTENT)
        except Storage.DoesNotExist:
            return error_response("Bucket not found in database")
        except Exception as e:
            return error_response(str(e))


class UploadFileToAzure(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        azure_manager = AzureManager()
        account_name = request.data.get('account_name')
        file_obj = request.FILES['file']
        container_name = request.data.get('container_name', f"file-{file_obj.name.replace('.', '-').replace(' ', '-').lower()}")
        print(f'container_name:  {container_name}')
        blob_name = request.data.get('blob_name', file_obj.name)

        if not container_name:
            return error_response("Missing required parameter: container_name", status.HTTP_400_BAD_REQUEST)

        file_path = os.path.join(settings.MEDIA_ROOT, file_obj.name)
        with open(file_path, 'wb+') as f:
            for chunk in file_obj.chunks():
                f.write(chunk)

        try:
            response = azure_manager.manage_file('upload_blob', account_name, container_name, file_path, blob_name)
            # os.remove(file_path)  # Optionally remove the file after upload
            return success_response(response, "File uploaded successfully", status.HTTP_200_OK)
        except Exception as e:
            return error_response(str(e))


class DownloadFileFromAzure(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        account_name = request.data.get('account_name')
        file_name = request.data.get('file_name')
        blob_name = request.data.get('blob_name', file_name)
        container_name = request.data.get('container_name', f"file-{file_name.replace('.', '-').replace(' ', '-').lower()}")

        file_path = os.path.join(settings.MEDIA_ROOT, file_name)
        try:
            response = azure_manager.manage_file('download_blob', account_name, container_name, file_path, blob_name)
            return success_response(response)
        except Exception as e:
            return error_response(str(e))


class ListAzureObjects(APIView):
    def get(self, request):
        azure_manager = AzureManager()
        account_name = request.query_params.get('account_name')
        container_name = request.query_params.get('container_name')

        try:
            objects = azure_manager.list_objects(account_name, container_name)
            return success_response(objects)
        except Exception as e:
            return error_response(str(e))


class DeleteAzureObject(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        account_name = request.data.get('account_name')
        container_name = request.data.get('container_name')
        blob_name = request.data.get('blob_name')

        try:
            response = azure_manager.delete_object(account_name, container_name, blob_name)
            return success_response(response, "Object deleted successfully", status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return error_response(str(e))


class GenerateAzurePresignedUrl(APIView):
    def post(self, request):
        azure_manager = AzureManager()
        account_name = request.data.get('account_name')
        container_name = request.data.get('container_name')
        blob_name = request.data.get('blob_name')
        expiration = request.data.get('expiration', 3600)

        if not container_name or not blob_name:
            return error_response("Missing required parameters", status.HTTP_400_BAD_REQUEST)

        try:
            response = azure_manager.generate_presigned_url(account_name, container_name, blob_name, expiration)
            return success_response(response)
        except Exception as e:
            return error_response(str(e))


class RetrieveAzureCosts(APIView):
    def get(self, request):
        azure_manager = AzureManager()
        current_date = datetime.now()
        first_date_of_month = current_date.replace(day=1)
        formatted_end_date = current_date.strftime("%Y-%m-%d")
        formatted_start_date = first_date_of_month.strftime("%Y-%m-%d")
        start_date = request.query_params.get('start_date', formatted_start_date)
        end_date = request.query_params.get('end_date', formatted_end_date)

        if not start_date or not end_date:
            return error_response("Missing required parameters: start_date and end_date", status.HTTP_400_BAD_REQUEST)

        try:
            response = azure_manager.get_cost_and_usage(start_date, end_date)
            return success_response(response, "Cost data retrieved successfully", status.HTTP_200_OK)
        except Exception as e:
            return error_response(str(e))


class RetrieveAzureCostsByService(APIView):
    def get(self, request):
        azure_manager = AzureManager()
        current_date = datetime.now()
        first_date_of_month = current_date.replace(day=1)
        formatted_end_date = current_date.strftime("%Y-%m-%d")
        formatted_start_date = first_date_of_month.strftime("%Y-%m-%d")
        start_date = request.query_params.get('start_date', formatted_start_date)
        end_date = request.query_params.get('end_date', formatted_end_date)

        if not start_date or not end_date:
            return error_response("Missing required parameters: start_date and end_date", status.HTTP_400_BAD_REQUEST)

        try:
            response = azure_manager.get_cost_by_service(start_date, end_date)
            return success_response(response, "Cost data by service retrieved successfully", status.HTTP_200_OK)
        except Exception as e:
            return error_response(str(e))


class AzureListClusters(APIView):
    def get(self, request):
        azure_manager = AzureManager()
        try:
            clusters = azure_manager.list_clusters()
            return Response(clusters, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AzureGetCluster(APIView):
    def get(self, request, cluster_name):
        azure_manager = AzureManager()
        try:
            cluster = azure_manager.get_cluster(cluster_name)
            return Response(cluster, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AzureDeleteCluster(APIView):
    def delete(self, request, cluster_name):
        azure_manager = AzureManager()
        try:
            azure_manager.delete_cluster(cluster_name)
            return Response({"message": "Cluster deleted successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
