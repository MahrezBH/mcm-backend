from datetime import timedelta
import os
import hvac

# Vault configuration
VAULT_ADDR = 'http://37.27.4.176:8200'  # Replace with your Vault server address
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
SECRET_KEY = vault_secrets.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_yasg',
    'rest_framework_simplejwt',
    'corsheaders',
    'cloud_providers',
    'configurations',
    'core'
)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=10),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
}
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",
    "http://65.21.108.31:4200"
]
# CORS_ALLOW_ALL_ORIGINS = True # to allow all orings
SSH_PRIVATE_KEY = vault_secrets.get('SSH_PRIVATE_KEY')
SSH_PUBLIC_KEY = vault_secrets.get('SSH_PUBLIC_KEY')

# AZURE Configuration
AZURE_TENANT_ID = vault_secrets.get('AZURE_TENANT_ID')
AZURE_CLIENT_ID = vault_secrets.get('AZURE_CLIENT_ID')
AZURE_CLIENT_SECRET = vault_secrets.get('AZURE_CLIENT_SECRET')
AZURE_SUBSCRIPTION_ID = vault_secrets.get('AZURE_SUBSCRIPTION_ID')
AZURE_RESOURCE_GROUP = vault_secrets.get('AZURE_RESOURCE_GROUP')
AZURE_LOCATION = vault_secrets.get('AZURE_LOCATION')
AZURE_STORAGE_CONNECTION_STRING = vault_secrets.get('AZURE_STORAGE_CONNECTION_STRING')
AZURE_STORAGE_ACCOUNT_KEY = vault_secrets.get('AZURE_STORAGE_ACCOUNT_KEY')
AZURE_DEFAULT_BUCKET = vault_secrets.get('AZURE_DEFAULT_BUCKET')

# AWS Configuration
AWS_ACCESS_KEY_ID = vault_secrets.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = vault_secrets.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = vault_secrets.get('AWS_REGION')
AWS_SSH_PRIVATE_KEY = vault_secrets.get('AWS_SSH_PRIVATE_KEY')
AWS_SSH_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAgvuoejbdUygRMA1bSxLJgWrPxAx30y/0xvqCh2WxM79enbUy
Xv7j3dArtFryEtrXHqx42iMvc5AW3j8yhdYDn0/4ArHC9XXMFBF6Ji/Ii6GXj+nk
V6pWJ9wEngNX/lV6uq4HcTvgF5+zRPVNzQzigIJDrhUvwKYO1NlFxRiT7OYK77CC
xkdIgwdV0j+AFm+tLz7YMAnSfhR3I6Wmk+g8HoC8ThMeSCrG906B3/OnbjLI6zSM
03SfQ1zmLMMYM8gMbSA6a3vDRw8avRGPMHReRHR3hqkgJiRZF3wWFOXh24PaV1EZ
nT1WZfiikWze1KPdcTaa/8QMkKRyE/avOWhVfQIDAQABAoIBAARQpBE6o3ns1Pwf
RIWpncfMrAGKY5wqdUbk084AFKFeyZAqevlULk+NXxM298iVOwcAqY6OIC8PbSFv
NYvhLAdgjAwSrRiHA+0ZUkvVwSaQcTzFeMdGjkYL4n8OHyT6zes+dnJNhalhkndQ
GXsK1J9lKzOd8Q/IqK5sZfcDQ0RHl6xEgh7wgdZ4cCwJlE1IoPhvaqL73fJq7P6c
KVbqbfQu0ywVYzJR+QlflHpNt9D6OWG9T6b388D9Q8BLP8FoFKX0TTyW6wKlnEwS
LyA8OrWJCCRFDX+feHQRviyq2Q3d330r9lPhS/sUInVg7QxI9bNqTde8UK9MtG6p
aWAWW8UCgYEAy84Vrj8YMlK7ZGaMLub9guigUHwkfkChx/Dy2cnmO3RJ6cB1Twmb
jDz1IyX4vYds4Y/IoPBfCjZuCfUrAqWH9sHUoe9lb0+66Mp3j8WSnjyqCbetu5lV
toGwW3B88zvOPP177ewJTGEJhDQo4wZbBpU2Vl4jtB/HyKCRb1fineMCgYEApIcz
Y1seZOyO+rtK7qrFQUWBlvOCkMwbXY5WUZUIa8hbqB1hL3Erld6tkyZVQJ1fDtir
55XSQ/QHypog6Xy4jHm8z4QDZ1hd7L0RYLdwKdNpeWSZPdCihEjv3XRENRcfGlJt
enGS6hQZB6fr1T6Sl/iTn89CJflpjxWA/cbBnR8CgYEAq8yccBcVwY4GE1tyfjMP
ruOECHStmpPHDLFrNfXBE4syp04qVScHLU9RYYCnzrSzLu0ytaAKraQ2XESELiX1
mCfKo3sXaZ6vM39BDDwDHUqMF8bzN7nJDCEE1f/cBHn8n2MarfQT3oPKLtx9Purj
nof3lxSiSjukANaB4ncWO/sCgYAiax429MLg/hPTJAdC8nqdcvrvJzXzMJ+w7Kvm
GTVPxvRVsP+5uwURLypElEpVYBaYtn8PzWnVSWGv4ppr/elliboT91v27KeJdOwD
vZw7Q7zW5lKgedrlrZRwUXhLWvDowsGgUc4YJeguj9RoIdTs8dWAIw2FgC2y/x6i
+EdcpQKBgHtNECELZK/sRvBIz/rONT+UfkRLIwUzw/SP0dmvr37rlWhpG6Wd3QL4
MNMQqeLxLa/9jU0K/4Kry+ZHQB41rDNqIDjQQIUu+xSd9/bJ71gWuzt9O6wWtV1Y
/PKcgf6qhT3bDsFt28ExhJcfFiZVK7n1a17nn9tZWZTaVOTIEC3g
-----END RSA PRIVATE KEY-----"""

AWS_EKS_CLUSTER_ROLE_ARN = None
AWS_EKS_NODE_ROLE_ARN = None
AWS_DEFAULT_KEY_NAME = vault_secrets.get('AWS_DEFAULT_KEY_NAME')
AWS_DEFAULT_BUCKET = vault_secrets.get('AWS_DEFAULT_BUCKET')

# GCP Configuration
GCP_PROJECT_ID = vault_secrets.get('GCP_PROJECT_ID')
GCP_ZONE = vault_secrets.get('GCP_ZONE')
GCP_BILLING_ACCOUNT_ID = vault_secrets.get('GCP_BILLING_ACCOUNT_ID')
GCP_DEFAULT_BUCKET = vault_secrets.get('GCP_DEFAULT_BUCKET')
GCP_SERVICE_ACCOUNT_INFO = {
    "type": "service_account",
    "project_id": "ilef-cloud",
    "private_key_id": "fcc0cf91f94b3f681c5862322f81d3cda501fe29",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDflelx6dX/lVGa\nn1Pg1/xFJl9PaucJrbEkWq7L/GwhNxVrgSfvEsa6LO+FLCIEc4LQCm6BDcHUQE1E\nbDX9qhK/XGubbs1oPLHi2KpJ/YWvHlyurazzuU67uNY6Wxphfbmfmcc4rTaffmYh\njEJ39GlrZX114z/NFj34KxQ0fklpHvFg8dfPoU9VHtpAF/Vy1MqGdzFfxXbALB0k\nWjS81d0WgbQFuMYQSmgN/6e5W6el4eIo5LUQfVY0+xX3szrVLsK6kILues37DH4Y\nuxswTiC6dVz7RfRl8GQ9MXc7glaJOHls0ZCmmvC/bGttuhX0G9h4g++P2hDOfJ/y\nX7Kkb9i7AgMBAAECggEAF+lvgwhQI7pzdMbvcI+I4lhdPyAev3E9DbdJFHXVlqPO\nfaXdgHsQl96waxyyMqmr5tYGxXSUM0ABQ30TNSLYSHD47TGndCtxluI3LByaDIWB\nwgi/A33hBsCY4LrXkm+gx4npvY0A14PsJlBa13tjPuImzdHVA/kJ/Z2V1pte/Ifo\nbZQyiIvBQr2gPwTd47qHFFDbapuCl1hR4Fv7ziHBjEyrbCzJPzP9Vi667Rr4EzSm\nwEbpZS4v//Ww/Rt2iKEJjR81QeB4QM1tvA+dXa4qp3Bwt5LyYTB1BSuJtwY+UNUl\n/6kTUSohVP1jGSuEWcXOQNb+cPBN5YY40AH7h+/EmQKBgQD6AtNbkw6nl+8eg4Cg\nHFOTHfFmTzYy0HH1caRvoVPEN1nQ3FiHsbhc6YGs087OAekdQ5Xq+Gcv/h1gmzJq\n0hd+sFeas+qfrNacuSAFFk8K6SEPhlAO0C2bNxbtS9f9HT/8hd6sIz9Qmcf0Uhqe\n9khtSEccQi8VP49Puvip1RSoVQKBgQDk8Qi/x5xqEU5zbmNcxGRCccQBEUGbavbH\nEOlo16lov6nssz+J8F4WBULhJybnXgmSa+mqRyUw1mqMdhcftIGCRZVWM2oUw9S0\npk3uWiaE+d42l4+9VH9j1AIbr0+S1d/pwIW4yNj+9c4+/GiWBtd40zNkTtiSOl5Y\nIkMl0DjMzwKBgQDdhaVrDZk9jFT2j4Rn2dF/mFdt1J/sVF+1H9WYh7SmNnkhpCvZ\nR/JYeRpKXX5vcKfyIxFyGlmr35h+IeWBWtgwi+WDkQlCJC4gvbOObl7pBvohPFwx\nU+olDqIE7l/ZyZIJmUBc+/o825WdeSZXVVeFZTaE5mu7gw7jkYKFUOU15QKBgBLb\nX5McR9/cqQ+M6hY7/t4SLMjBuRuqBcWDuRXvnX6JOt/KK9OavsUljcqpxOSNtFAh\nH0/tKD0LjB8hounzni8yuAgvl+856g0vHYAiYMXXJtxsQ2SezxdT4RCSsgUwJI9G\nUj1UHbtyV5iMhbjFu32yN6ttax0wPZEY0VsN+X+1AoGBAPaAbxeIQPXdjuX+Lmbc\nYJSXJlDEbBVXHWrLpszkQd7fDXgL6fG41lxjCx774Onn5aJGkvuKMPw8cI+dsMZj\neCGryk5RpdTpF47WPJG/iXYzkp6Cf8QnICldZ01JMHlhCL2im9UPabvSC12rB3lR\nvTQPsWAGMjQWp44hHg4DOQFH\n-----END PRIVATE KEY-----\n",
    "client_email": "ilef-cloud-service@ilef-cloud.iam.gserviceaccount.com",
    "client_id": "100717358151444763844",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/ilef-cloud-service%40ilef-cloud.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}


# Hetzner configuration
HETZNER_API_TOKEN = vault_secrets.get('HETZNER_API_TOKEN')
HETZNER_DEFAULT_KEY_NAME = vault_secrets.get('HETZNER_DEFAULT_KEY_NAME')

NEXUS_REGISTRY_URL = vault_secrets.get('NEXUS_REGISTRY_URL')
NEXUS_REGISTRY_DEFAULT_PORT = vault_secrets.get('NEXUS_REGISTRY_DEFAULT_PORT')
NEXUS_REGISTRY_DOCKER_PORT = vault_secrets.get('NEXUS_REGISTRY_DOCKER_PORT')
NEXUS_REGISTRY_USERNAME = vault_secrets.get('NEXUS_REGISTRY_USERNAME')
NEXUS_REGISTRY_PASSWORD = vault_secrets.get('NEXUS_REGISTRY_PASSWORD')
