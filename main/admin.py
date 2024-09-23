from django.contrib import admin

# Register your models here.

from .models import Resource
from .models import Booking
from .models import Queue


admin.site.register(Resource)
admin.site.register(Booking)
admin.site.register(Queue)
