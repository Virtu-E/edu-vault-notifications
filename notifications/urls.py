from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import NotificationViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

# URL patterns
urlpatterns = [
    # API endpoints
    path('api/', include(router.urls)),
]

# Available endpoints:
# GET    /api/notifications/                    - List all notifications
# GET    /api/notifications/{id}/               - Get specific notification
# PATCH  /api/notifications/{id}/               - Update notification (mark read/unread)
# DELETE /api/notifications/{id}/               - Delete notification
#
# Custom actions:
# GET    /api/notifications/unread/             - List unread notifications
# GET    /api/notifications/unread_count/       - Get unread count
# POST   /api/notifications/{id}/mark_read/     - Mark specific as read
# POST   /api/notifications/{id}/mark_unread/   - Mark specific as unread
# POST   /api/notifications/mark_all_read/      - Mark all as read
# POST   /api/notifications/mark_all_unread/    - Mark all as unread
# POST   /api/notifications/bulk_action/        - Bulk actions
# GET    /api/notifications/levels/             - Get available levels
#
# Query parameters for filtering:
# ?unread_only=true/false  - Filter by read status
# ?level=info/success/warning/error  - Filter by level
# ?verb=liked  - Filter by verb (contains)
# ?page=1&page_size=20  - Pagination