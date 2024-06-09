from rest_framework import serializers
from .models import KeyPair, Storage


class KeyPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = KeyPair
        fields = '__all__'


class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storage
        fields = '__all__'
