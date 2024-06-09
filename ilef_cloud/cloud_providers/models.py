from django.db import models


class CloudProvider(models.Model):
    PROVIDER_CHOICES = [
        ('aws', 'Amazon Web Services'),
        ('azure', 'Microsoft Azure'),
        ('gcp', 'Google Cloud Platform'),
        ('hetzner', 'Hetzner Cloud'),
    ]
    name = models.CharField(max_length=50, choices=PROVIDER_CHOICES, unique=True)
    api_key = models.CharField(max_length=255)
    api_secret = models.CharField(max_length=255)
    region = models.CharField(max_length=100)

    def __str__(self):
        return self.get_name_display()


class Instance(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('terminated', 'Terminated'),
        ('pending', 'Pending'),
    ]

    provider = models.ForeignKey(CloudProvider, on_delete=models.CASCADE)
    instance_id = models.CharField(max_length=100, unique=True)
    instance_type = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    key_name = models.CharField(max_length=100)
    private_ip = models.GenericIPAddressField(null=True, blank=True)
    public_ip = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.instance_id} ({self.get_provider_display()})"

    def total_cost(self):
        return self.cost_set.aggregate(models.Sum('amount'))['amount__sum']


class Cost(models.Model):
    provider = models.ForeignKey(CloudProvider, on_delete=models.CASCADE)
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE, null=True, blank=True)
    resource_type = models.CharField(max_length=100)  # e.g., 'instance', 'storage'
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    date = models.DateField()

    def __str__(self):
        return f"{self.resource_type} cost on {self.date}"


class Storage(models.Model):
    provider = models.ForeignKey(CloudProvider, on_delete=models.CASCADE)
    storage_id = models.CharField(max_length=100, unique=True)
    storage_type = models.CharField(max_length=100)  # e.g., 'S3', 'Blob'
    created_at = models.DateTimeField()
    location = models.URLField()

    def __str__(self):
        return f"{self.storage_id} ({self.provider.name})"

    def total_cost(self):
        return self.cost_set.aggregate(models.Sum('amount'))['amount__sum']


class KeyPair(models.Model):
    provider = models.ForeignKey(CloudProvider, on_delete=models.CASCADE)
    key_pair_id = models.CharField(max_length=100, unique=True)
    key_fingerprint = models.CharField(max_length=255)
    key_name = models.CharField(max_length=100)
    key_type = models.CharField(max_length=50)
    create_time = models.DateTimeField()

    def __str__(self):
        return f"{self.key_name} ({self.provider.name})"
