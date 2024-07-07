from django.urls import path
from cloud_providers.views import (
    CordonNodeView, DrainNodeView, ListEC2Instances, CreateEC2Instance, RetrieveAzureCosts, RetrieveAzureCostsByService, StartEC2Instance, StopEC2Instance, TerminateEC2Instance,
    ListS3Buckets, CreateS3Bucket, DeleteS3Bucket, UncordonNodeView, UploadFile, UploadFileToS3, DownloadFileFromS3, ListS3Objects,
    DeleteS3Object, GeneratePresignedUrl, ListKeyPairs, CreateKeyPair, DeleteAWSKeyPair,
    ListHetznerInstances, CreateHetznerInstance, StartHetznerInstance, StopHetznerInstance,
    TerminateHetznerInstance, ListHetznerKeyPairs, CreateHetznerKeyPair, DeleteHetznerKeyPair,
    ListGCPInstances, CreateGCPInstance, StartGCPInstance, StopGCPInstance, TerminateGCPInstance,
    ListGCPBuckets, CreateGCPBucket, DeleteGCPBucket, UploadFileToGCP, DownloadFileFromGCP,
    ListGCPObjects, DeleteGCPObject, GenerateGCPPresignedUrl,
    ListAzureInstances, CreateAzureInstance, StartAzureInstance, StopAzureInstance, TerminateAzureInstance,
    ListAzureBuckets, CreateAzureBucket, DeleteAzureBucket, UploadFileToAzure, DownloadFileFromAzure,
    ListAzureObjects, DeleteAzureObject, GenerateAzurePresignedUrl, RetrieveCosts, DeployDockerImage, DeployDockerImageToCluster,
    ListClusters, AzureGetCluster, DeleteCluster, ListAWSClusters, GetAWSCluster, DeleteAWSCluster, CreateAndDeployAWSCluster,
    InstanceView, StartInstance, StopInstance, RestartInstance, TerminateInstance, ListAllObjects,
    GeneratePresignedUrl, DeleteObject,
)

urlpatterns = [
    # AWS Endpoints
    path('aws/ec2/instances/', ListEC2Instances.as_view(), name='list_ec2_instances'),
    path('aws/ec2/instances/create/', CreateEC2Instance.as_view(), name='create_ec2_instance'),
    path('aws/ec2/instances/start/', StartEC2Instance.as_view(), name='start_ec2_instance'),
    path('aws/ec2/instances/stop/', StopEC2Instance.as_view(), name='stop_ec2_instance'),
    path('aws/ec2/instances/terminate/', TerminateEC2Instance.as_view(), name='terminate_ec2_instance'),
    path('aws/s3/buckets/', ListS3Buckets.as_view(), name='list_s3_buckets'),
    path('aws/s3/buckets/create/', CreateS3Bucket.as_view(), name='create_s3_bucket'),
    path('aws/s3/buckets/delete/', DeleteS3Bucket.as_view(), name='delete_s3_bucket'),
    path('aws/s3/upload/', UploadFileToS3.as_view(), name='upload_file_to_s3'),
    path('aws/s3/download/', DownloadFileFromS3.as_view(), name='download_file_from_s3'),
    path('aws/s3/objects/', ListS3Objects.as_view(), name='list_s3_objects'),
    path('aws/s3/objects/delete/', DeleteS3Object.as_view(), name='delete_s3_object'),
    path('aws/s3/presigned-url/', GeneratePresignedUrl.as_view(), name='generate_presigned_url'),
    path('aws/key-pairs/', ListKeyPairs.as_view(), name='list_key_pairs'),
    path('aws/key-pairs/create/', CreateKeyPair.as_view(), name='create_key_pair'),
    path('aws/key-pairs/delete/', DeleteAWSKeyPair.as_view(), name='delete_aws_key_pair'),
    path('aws/clusters/', ListAWSClusters.as_view(), name='list-aws-clusters'),
    path('aws/clusters/create/', CreateAndDeployAWSCluster.as_view(), name='create-and-deploy-aws-cluster'),
    path('aws/clusters/<str:cluster_name>/', GetAWSCluster.as_view(), name='get-aws-cluster'),
    path('aws/clusters/<str:cluster_name>/delete/', DeleteAWSCluster.as_view(), name='delete-aws-cluster'),

    # Hetzner Endpoints
    path('hetzner/instances/', ListHetznerInstances.as_view(), name='list_hetzner_instances'),
    path('hetzner/instances/create/', CreateHetznerInstance.as_view(), name='create_hetzner_instance'),
    path('hetzner/instances/start/', StartHetznerInstance.as_view(), name='start_hetzner_instance'),
    path('hetzner/instances/stop/', StopHetznerInstance.as_view(), name='stop_hetzner_instance'),
    path('hetzner/instances/terminate/', TerminateHetznerInstance.as_view(), name='terminate_hetzner_instance'),
    path('hetzner/key-pairs/', ListHetznerKeyPairs.as_view(), name='list_hetzner_key_pairs'),
    path('hetzner/key-pairs/create/', CreateHetznerKeyPair.as_view(), name='create_hetzner_key_pair'),
    path('hetzner/key-pairs/delete/', DeleteHetznerKeyPair.as_view(), name='delete_hetzner_key_pair'),

    # GCP Endpoints
    path('gcp/instances/', ListGCPInstances.as_view(), name='list_gcp_instances'),
    path('gcp/instances/create/', CreateGCPInstance.as_view(), name='create_gcp_instance'),
    path('gcp/instances/start/', StartGCPInstance.as_view(), name='start_gcp_instance'),
    path('gcp/instances/stop/', StopGCPInstance.as_view(), name='stop_gcp_instance'),
    path('gcp/instances/terminate/', TerminateGCPInstance.as_view(), name='terminate_gcp_instance'),
    path('gcp/buckets/', ListGCPBuckets.as_view(), name='list_gcp_buckets'),
    path('gcp/buckets/create/', CreateGCPBucket.as_view(), name='create_gcp_bucket'),
    path('gcp/buckets/delete/', DeleteGCPBucket.as_view(), name='delete_gcp_bucket'),
    path('gcp/upload/', UploadFileToGCP.as_view(), name='upload_file_to_gcp'),
    path('gcp/download/', DownloadFileFromGCP.as_view(), name='download_file_from_gcp'),
    path('gcp/objects/', ListGCPObjects.as_view(), name='list_gcp_objects'),
    path('gcp/objects/delete/', DeleteGCPObject.as_view(), name='delete_gcp_object'),
    path('gcp/presigned-url/', GenerateGCPPresignedUrl.as_view(), name='generate_gcp_presigned_url'),

    # Azure Endpoints
    path('azure/instances/', ListAzureInstances.as_view(), name='list_azure_instances'),
    path('azure/instances/create/', CreateAzureInstance.as_view(), name='create_azure_instance'),
    path('azure/instances/start/', StartAzureInstance.as_view(), name='start_azure_instance'),
    path('azure/instances/stop/', StopAzureInstance.as_view(), name='stop_azure_instance'),
    path('azure/instances/terminate/', TerminateAzureInstance.as_view(), name='terminate_azure_instance'),
    path('azure/buckets/', ListAzureBuckets.as_view(), name='list_azure_buckets'),
    path('azure/buckets/create/', CreateAzureBucket.as_view(), name='create_azure_bucket'),
    path('azure/buckets/delete/', DeleteAzureBucket.as_view(), name='delete_azure_bucket'),
    path('azure/upload/', UploadFileToAzure.as_view(), name='upload_file_to_azure'),
    path('azure/download/', DownloadFileFromAzure.as_view(), name='download_file_from_azure'),
    path('azure/objects/', ListAzureObjects.as_view(), name='list_azure_objects'),
    path('azure/objects/delete/', DeleteAzureObject.as_view(), name='delete_azure_object'),
    path('azure/presigned-url/', GenerateAzurePresignedUrl.as_view(), name='generate_azure_presigned_url'),
    path('azure/costs/', RetrieveAzureCosts.as_view(), name='retrieve_azure_costs'),
    path('azure/costs-by-service/', RetrieveAzureCostsByService.as_view(), name='retrieve_azure_costs_by_service'),
    path('azure/clusters/<str:cluster_name>/', AzureGetCluster.as_view(), name='get-cluster'),

    # Cost Management
    path('costs/retrieve/', RetrieveCosts.as_view(), name='retrieve_costs'),

    # Docker Deployment
    path('docker/deploy/', DeployDockerImage.as_view(), name='deploy_docker_image'),
    path('docker/cluster/deploy/', DeployDockerImageToCluster.as_view(), name='deploy_docker_image_to_cluster'),
    path('docker/clusters/', ListClusters.as_view(), name='list-clusters'),
    path('docker/clusters/node/cordon/', CordonNodeView.as_view(), name='cordon-node'),
    path('docker/clusters/node/drain/', DrainNodeView.as_view(), name='uncordon-node'),
    path('docker/clusters/node/uncordon/', UncordonNodeView.as_view(), name='uncordon-node'),
    path('docker/clusters/<str:cluster_name>/delete/', DeleteCluster.as_view(), name='delete-cluster'),

    # General
    path('instances/', InstanceView.as_view(), name='list_instances'),
    path('instances/start/', StartInstance.as_view(), name='start_instances'),
    path('instances/stop/', StopInstance.as_view(), name='stop_instances'),
    path('instances/restart/', RestartInstance.as_view(), name='restart_instances'),
    path('instances/terminate/', TerminateInstance.as_view(), name='terminate_instances'),
    path('objects/', ListAllObjects.as_view(), name='list_objects'),
    path('objects/generate-presigned-url/', GeneratePresignedUrl.as_view(), name='generate-presigned-url'),
    path('objects/upload-file/', UploadFile.as_view(), name='upload-file'),
    path('objects/delete-object/', DeleteObject.as_view(), name='delete-object'),



]
