import hvac
from rest_framework import status
from configurations.services.vault_service import VaultService
from rest_framework.decorators import api_view
import requests
from requests.auth import HTTPBasicAuth
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import render
from ilef_cloud.response_utils import success_response, error_response
from django.conf import settings

vault_service = VaultService()


class NexusComponentsView(APIView):
    def get(self, request):
        # nexus_url = "http://your-nexus-server"
        repository_name = request.query_params.get("repository_name", "ilef")
        api_endpoint = f"http://{settings.NEXUS_REGISTRY_URL}:{settings.NEXUS_REGISTRY_DEFAULT_PORT}/service/rest/v1/components?repository={repository_name}"
        print(api_endpoint)

        try:
            response = requests.get(api_endpoint, auth=HTTPBasicAuth(settings.NEXUS_REGISTRY_USERNAME, settings.NEXUS_REGISTRY_PASSWORD))
            response.raise_for_status()  # Raises a HTTPError if the response status code is 4xx or 5xx

            components = response.json()
            return success_response(components, "Components fetched successfully")
        except requests.exceptions.HTTPError as http_err:
            return error_response(f"HTTP error occurred: {http_err}", status_code=response.status_code)
        except Exception as err:
            return error_response(f"An error occurred: {err}")


@api_view(['POST'])
def store_secret(request):
    path = request.data.get('path')
    secret_data = request.data.get('secret_data')

    if not path or not secret_data:
        return Response({'error': 'Path and secret_data are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        vault_service.store_secret(path, secret_data)
        return Response({'message': 'Secret stored successfully.'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def fetch_secret(request, path=None):
    key = request.GET.get('key')
    if not path:
        path = settings.VAULT_SECRET_PATH

    try:
        secret_data = vault_service.fetch_secret(path)
        if key:
            secret_data = secret_data[key]
        return Response({'secret_data': secret_data}, status=status.HTTP_200_OK)
    except hvac.exceptions.InvalidPath:
        return Response({'error': 'Invalid path or secret not found.'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
