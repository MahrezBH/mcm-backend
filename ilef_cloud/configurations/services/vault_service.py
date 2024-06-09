import hvac
from django.conf import settings


class VaultService:
    def __init__(self):
        self.client = hvac.Client(
            url=settings.VAULT_ADDR,
            token=settings.VAULT_TOKEN,
        )

    def store_secret(self, secret_data, path=settings.VAULT_SECRET_PATH):
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=secret_data,
        )

    def fetch_secret(self, path=settings.VAULT_SECRET_PATH):
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
