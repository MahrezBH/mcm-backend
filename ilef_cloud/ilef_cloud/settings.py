import os
import hvac

# Vault configuration
VAULT_ADDR = 'http://95.217.11.89:8200'  # Replace with your Vault server address
VAULT_TOKEN = os.getenv('VAULT_TOKEN')  # Securely get the Vault token from environment variables
VAULT_SECRET_PATH = 'ilef/myapp'  # Correct path without trailing slash


def get_all_vault_secrets():
    try:
        print(f"VAULT_ADDR: {VAULT_ADDR}")
        print(f"VAULT_TOKEN: {VAULT_TOKEN}")
        print(f"VAULT_SECRET_PATH: {VAULT_SECRET_PATH}")

        client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)
        print(f"Client initialized: {client.is_authenticated()}")

        # Fetch secrets from Vault
        print(f"Fetching secrets from path: {VAULT_SECRET_PATH}")
        response = client.secrets.kv.v2.read_secret_version(path=VAULT_SECRET_PATH)
        print(f"Response from Vault: {response}")

        # Debugging response structure
        if 'data' in response and 'data' in response['data']:
            secrets = response['data']['data']
            return secrets
        else:
            print("Unexpected response structure:", response)
            return None

    except hvac.exceptions.InvalidPath as e:
        print(f"Invalid path error: {e}")
        return None
    except Exception as e:
        print(f"Error fetching secrets from Vault: {e}")
        return None


# Fetching secrets from Vault
vault_secrets = get_all_vault_secrets()


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'uw7s_r-tt(w8#bp&c5t%jr$c4wd*0ql+x=xw4=gv2d)qz#+_l('

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloud_providers',
    'configurations',
)

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


ROOT_URLCONF = 'ilef_cloud.urls'

WSGI_APPLICATION = 'ilef_cloud.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'django_project.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        # 'django': {
        #     'handlers': ['console', 'file'],
        #     'level': 'DEBUG',
        #     'propagate': True,
        # },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        }
    },
}

SSH_PRIVATE_KEY = vault_secrets.get('SSH_PRIVATE_KEY')
# SSH_PRIVATE_KEY_PATH = '/home/mahrezbh/.ssh/id_rsa'
# SSH_ILEF_PRIVATE_KEY_PATH = '/home/mahrezbh/Desktop/pfe/Workspace/ilef_cloud/cloud_providers/services/ilef.pem'
SSH_PUBLIC_KEY = vault_secrets.get('SSH_PUBLIC_KEY')
# SSH_PUBLIC_KEY_PATH = '/home/mahrezbh/.ssh/id_rsa.pub'

# AZURE Configuration
AZURE_TENANT_ID = vault_secrets.get('AZURE_TENANT_ID')
AZURE_CLIENT_ID = vault_secrets.get('AZURE_CLIENT_ID')
AZURE_CLIENT_SECRET = vault_secrets.get('AZURE_CLIENT_SECRET')
AZURE_SUBSCRIPTION_ID = vault_secrets.get('AZURE_SUBSCRIPTION_ID')
AZURE_RESOURCE_GROUP = vault_secrets.get('AZURE_RESOURCE_GROUP')
AZURE_LOCATION = vault_secrets.get('AZURE_LOCATION')
AZURE_STORAGE_CONNECTION_STRING = vault_secrets.get('AZURE_STORAGE_CONNECTION_STRING')
AZURE_STORAGE_ACCOUNT_KEY = vault_secrets.get('AZURE_STORAGE_ACCOUNT_KEY')


# AWS Configuration
AWS_ACCESS_KEY_ID = vault_secrets.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = vault_secrets.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = vault_secrets.get('AWS_REGION')
AWS_SSH_PRIVATE_KEY = vault_secrets.get('AWS_SSH_PRIVATE_KEY')
# AWS_SSH_PRIVATE_KEY_PATH = '/home/mahrezbh/Desktop/pfe/Workspace/ilef_cloud/cloud_providers/services/ilef.pem'

# GCP Configuration
GCP_PROJECT_ID = vault_secrets.get('GCP_PROJECT_ID')
GCP_ZONE = vault_secrets.get('GCP_ZONE')
GCP_BILLING_ACCOUNT_ID = vault_secrets.get('GCP_BILLING_ACCOUNT_ID')
GCP_SERVICE_ACCOUNT_FILE = '/home/mahrezbh/Desktop/pfe/Workspace/ilef_cloud/cloud_providers/services/ilef-cloud-fcc0cf91f94b.json'

# Hetzner configuration
HETZNER_API_TOKEN = vault_secrets.get('HETZNER_API_TOKEN')

NEXUS_REGISTRY_URL = "95.217.11.89"
# NEXUS_REGISTRY_URL = vault_secrets.get('NEXUS_REGISTRY_URL')
NEXUS_REGISTRY_DEFAULT_PORT = vault_secrets.get('NEXUS_REGISTRY_DEFAULT_PORT')
NEXUS_REGISTRY_DOCKER_PORT = vault_secrets.get('NEXUS_REGISTRY_DOCKER_PORT')
NEXUS_REGISTRY_USERNAME = vault_secrets.get('NEXUS_REGISTRY_USERNAME')
NEXUS_REGISTRY_PASSWORD = vault_secrets.get('NEXUS_REGISTRY_PASSWORD')
