from datetime import timedelta

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

        if not start_time or not end_time:
            return Response({'detail': 'Start time and end time are required.'}, status=status.HTTP_400_BAD_REQUEST)

        start_time = timezone.datetime.fromisoformat(start_time)
        end_time = timezone.datetime.fromisoformat(end_time)

        # Проверка максимальной длительности бронирования для ресурса
        resource = Resource.objects.get(id=resource_id)
        max_duration = timedelta(hours=resource.max_duration)  # Максимальная длительность в часах
        actual_duration = end_time - start_time

        if actual_duration > max_duration:
            return Response(
                {'detail': f'Booking duration exceeds the maximum allowed duration of {resource.max_duration} hours.'},
                status=status.HTTP_400_BAD_REQUEST
            )
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
        return not overlapping_bookings.exists()

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()

        booking.status = 'completed'
        booking.save()

        self.advance_queue(booking.resource)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        booking = self.get_object()
        old_status = booking.status  # Сохраняем старый статус

        response = super().update(request, *args, **kwargs)  # Выполняем обновление бронирования

        # Проверяем, изменился ли статус на 'completed'
        if old_status != 'completed' and self.get_object().status == 'completed':
            # Автоматически продвигаем пользователя в очереди
            self.advance_queue(booking.resource)

        return response

    def partial_update(self, request, *args, **kwargs):
        booking = self.get_object()
        old_status = booking.status  # Сохраняем старый статус

        response = super().partial_update(request, *args, **kwargs)  # Выполняем частичное обновление

        # Проверяем, изменился ли статус на 'completed'
        if old_status != 'completed' and self.get_object().status == 'completed':
            # Автоматически продвигаем пользователя в очереди
            self.advance_queue(booking.resource)

        return response

    def advance_queue(self, resource):
            # Ищем первого пользователя в очереди
        next_in_queue = Queue.objects.filter(booking__resource=resource).order_by('position').first()

        if next_in_queue:
                next_booking = next_in_queue.booking
                next_booking.status = 'active'
                next_booking.save()

                # Удаляем пользователя из очереди
                next_in_queue.delete()

                # Выводим уведомление в консоль (можно заменить реальным уведомлением)
                print(f"Booking {next_booking.id} moved from queue to active for resource {resource.name}")


