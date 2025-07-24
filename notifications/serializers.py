from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import Notification


class GenericRelatedField(serializers.RelatedField):
    """
    A custom field to handle generic foreign key relationships.
    Returns a dictionary with the object's string representation and type.
    """

    def to_representation(self, value):
        if value is None:
            return None
        return {
            'id': value.pk,
            'type': value.__class__.__name__,
            'str': str(value)
        }


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model with all relevant fields for API consumption.
    """
    # Generic foreign key fields with custom representation
    actor = GenericRelatedField(read_only=True)
    target = GenericRelatedField(read_only=True)
    action_object = GenericRelatedField(read_only=True)

    # Additional computed fields
    time_since = serializers.CharField(source='timesince', read_only=True)
    recipient_username = serializers.CharField(source='recipient.username', read_only=True)

    # ISO formatted timestamp
    timestamp_iso = serializers.DateTimeField(source='timestamp', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'recipient_username',
            'actor',
            'verb',
            'description',
            'target',
            'action_object',
            'level',
            'unread',
            'public',
            'timestamp',
            'timestamp_iso',
            'time_since',
            'data',  # JSON field for extra data
        ]
        read_only_fields = [
            'id',
            'timestamp',
            'timestamp_iso',
            'time_since',
            'recipient_username'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing notifications (less detailed).
    """
    actor_str = serializers.CharField(source='actor.__str__', read_only=True)
    time_since = serializers.CharField(source='timesince', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'actor_str',
            'verb',
            'level',
            'unread',
            'timestamp',
            'time_since',
        ]


class UnreadCountSerializer(serializers.Serializer):
    """
    Serializer for returning unread notification count.
    """
    unread_count = serializers.IntegerField()


class MarkAllAsReadSerializer(serializers.Serializer):
    """
    Serializer for mark all as read action response.
    """
    message = serializers.CharField()
    marked_count = serializers.IntegerField()


class MarkAsReadSerializer(serializers.Serializer):
    """
    Serializer for individual notification mark as read action.
    """
    success = serializers.BooleanField(default=True)
    message = serializers.CharField(default="Notification marked as read")


class BulkActionSerializer(serializers.Serializer):
    """
    Serializer for bulk actions on multiple notifications.
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False
    )
    action = serializers.ChoiceField(
        choices=['mark_read', 'mark_unread', 'delete'],
        required=True
    )