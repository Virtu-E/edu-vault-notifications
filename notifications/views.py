from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404

from .models import Notification
from .serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    UnreadCountSerializer,
    MarkAllAsReadSerializer,
    MarkAsReadSerializer,
    BulkActionSerializer
)


class NotificationPagination(PageNumberPagination):
    """
    Custom pagination for notifications.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications via API.
    Provides CRUD operations and custom actions for notification management.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = NotificationPagination

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'list':
            return NotificationListSerializer
        return NotificationSerializer

    def get_queryset(self):
        """
        Return notifications for the authenticated user only.
        Supports filtering by read/unread status and level.
        """
        queryset = self.request.user.notifications.all()

        # Filter by read/unread status
        unread_only = self.request.query_params.get('unread_only', None)
        if unread_only is not None:
            if unread_only.lower() in ['true', '1']:
                queryset = queryset.unread()
            elif unread_only.lower() in ['false', '0']:
                queryset = queryset.read()

        # Filter by level
        level = self.request.query_params.get('level', None)
        if level:
            queryset = queryset.filter(level=level)

        # Filter by verb (notification type)
        verb = self.request.query_params.get('verb', None)
        if verb:
            queryset = queryset.filter(verb__icontains=verb)

        return queryset.select_related('recipient').prefetch_related(
            'actor_content_type',
            'target_content_type',
            'action_object_content_type'
        )

    def perform_destroy(self, instance):
        """
        Override destroy to ensure users can only delete their own notifications.
        """
        if instance.recipient != self.request.user:
            return Response(
                {'error': 'You can only delete your own notifications'},
                status=status.HTTP_403_FORBIDDEN
            )
        instance.delete()

    def partial_update(self, request, pk=None):
        """
        Handle PATCH requests - mainly for marking as read/unread.
        """
        notification = self.get_object()

        # Check ownership
        if notification.recipient != request.user:
            return Response(
                {'error': 'You can only modify your own notifications'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Handle unread field specifically
        if 'unread' in request.data:
            if request.data['unread']:
                notification.mark_as_unread()
            else:
                notification.mark_as_read()

        serializer = self.get_serializer(notification, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get all unread notifications for the current user.
        GET /api/notifications/unread/
        """
        unread_notifications = self.get_queryset().unread()
        page = self.paginate_queryset(unread_notifications)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(unread_notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications.
        GET /api/notifications/unread_count/
        """
        count = self.get_queryset().unread().count()
        serializer = UnreadCountSerializer({'unread_count': count})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a specific notification as read.
        POST /api/notifications/{id}/mark_read/
        """
        notification = self.get_object()

        if notification.recipient != request.user:
            return Response(
                {'error': 'You can only modify your own notifications'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_as_read()
        serializer = MarkAsReadSerializer({
            'success': True,
            'message': 'Notification marked as read'
        })
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_unread(self, request, pk=None):
        """
        Mark a specific notification as unread.
        POST /api/notifications/{id}/mark_unread/
        """
        notification = self.get_object()

        if notification.recipient != request.user:
            return Response(
                {'error': 'You can only modify your own notifications'},
                status=status.HTTP_403_FORBIDDEN
            )

        notification.mark_as_unread()
        serializer = MarkAsReadSerializer({
            'success': True,
            'message': 'Notification marked as unread'
        })
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read for the current user.
        POST /api/notifications/mark_all_read/
        """
        marked_count = self.get_queryset().mark_all_as_read(recipient=request.user)

        serializer = MarkAllAsReadSerializer({
            'message': f'{marked_count} notifications marked as read',
            'marked_count': marked_count
        })
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_unread(self, request):
        """
        Mark all notifications as unread for the current user.
        POST /api/notifications/mark_all_unread/
        """
        marked_count = self.get_queryset().mark_all_as_unread(recipient=request.user)

        serializer = MarkAllAsReadSerializer({
            'message': f'{marked_count} notifications marked as unread',
            'marked_count': marked_count
        })
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """
        Perform bulk actions on multiple notifications.
        POST /api/notifications/bulk_action/

        Body:
        {
            "notification_ids": [1, 2, 3],
            "action": "mark_read"  # or "mark_unread" or "delete"
        }
        """
        serializer = BulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        notification_ids = serializer.validated_data['notification_ids']
        action_type = serializer.validated_data['action']

        # Get notifications that belong to the user
        notifications = self.get_queryset().filter(id__in=notification_ids)

        if not notifications.exists():
            return Response(
                {'error': 'No valid notifications found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Perform the action
        if action_type == 'mark_read':
            count = notifications.update(unread=False)
            message = f'{count} notifications marked as read'
        elif action_type == 'mark_unread':
            count = notifications.update(unread=True)
            message = f'{count} notifications marked as unread'
        elif action_type == 'delete':
            count = notifications.count()
            notifications.delete()
            message = f'{count} notifications deleted'

        return Response({
            'success': True,
            'message': message,
            'affected_count': count
        })

    @action(detail=False, methods=['get'])
    def levels(self, request):
        """
        Get available notification levels.
        GET /api/notifications/levels/
        """
        levels = [{'value': level, 'label': level.title()} for level in Notification.LEVELS]
        return Response({'levels': levels})