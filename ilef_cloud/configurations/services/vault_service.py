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

    def delete_secret_key(self, path, key):
        try:
            # Fetch the existing secret data
            existing_secret_data = self.fetch_secret(path)
            if key in existing_secret_data:
                # Remove the key
                del existing_secret_data[key]
                # Store the updated data back to Vault
                self.store_secret(existing_secret_data, path)
                return True
            else:
                return False
        except Exception as e:
            raise e
