from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.db.models import Q
from .models import Booking, Resource, Queue
from .serializers import BookingSerializer, ResourceSerializer
from django.utils import timezone

class BookingViewSet(viewsets.ModelViewSet):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer

    def create(self, request, *args, **kwargs):
        # Получаем данные бронирования
        user = request.user
        resource_id = request.data.get('resource')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')

        # Проверяем наличие пересечений бронирований
        if self.is_slot_available(resource_id, start_time, end_time):
            # Создание бронирования
            booking = Booking.objects.create(
                user=user,
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                status='active'
            )
            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)
        else:
            # Если нет свободных слотов — добавляем в очередь
            booking = Booking.objects.create(
                user=user,
                resource_id=resource_id,
                start_time=start_time,
                end_time=end_time,
                status='queued'
            )
            queue_position = Queue.objects.filter(booking__resource_id=resource_id).count() + 1
            Queue.objects.create(booking=booking, position=queue_position)
            print(f"User {user.username} added to the queue at position {queue_position}")
            return Response({'detail': 'Added to the queue'}, status=status.HTTP_202_ACCEPTED)

    def is_slot_available(self, resource_id, start_time, end_time):
        overlapping_bookings = Booking.objects.filter(
            Q(resource_id=resource_id),
            Q(start_time__lt=end_time, end_time__gt=start_time),
            Q(status='active')
        )
        resource = Resource.objects.get(id=resource_id)
        return overlapping_bookings.count() < resource.max_slots

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        booking.delete()

        # Проверяем очередь и продвигаем пользователей
        next_in_queue = Queue.objects.filter(booking__resource_id=booking.resource_id).order_by('position').first()
        if next_in_queue:
            next_booking = next_in_queue.booking
            next_booking.status = 'active'
            next_booking.save()
            next_in_queue.delete()
            print(f"Booking {next_booking.id} moved from queue to active")

        return Response(status=status.HTTP_204_NO_CONTENT)

