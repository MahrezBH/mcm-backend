from django.utils.crypto import get_random_string


def get_image_name(url: str, provider) -> str:
    # Extract the relevant part of the URL
    path_parts = url.split('/')
    image_with_version = path_parts[-1]

    formatted_name = '-'.join(image_with_version.split(':')) + f'{get_random_string(3)}-{provider}'

    return formatted_name.lower()
