from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Resource(models.Model):
    name = models.CharField(max_length=100)
    max_slots = models.IntegerField()

    def __str__(self):
        return self.name

class Booking(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('queued', 'Queued'),
        ('completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Booking {self.id} for {self.resource.name}"

class Queue(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    position = models.IntegerField()

    def __str__(self):
        return f"Queue position {self.position} for booking {self.booking.id}"
