"""
In-app notifications (the bell in the header). Order updates are written here when a seller packs, sends out or delivers an order.
A user only ever reads and changes their own.
"""

from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Notification
from .views import get_user_from_token


def push(email: str, title: str, body: str = '', order_id: str = '', kind: str = 'order') -> None:
    """Add a notification for `email`. Never raises: a failed notification must not break the order update that caused it."""
    if not email:
        return
    try:
        Notification.objects.create(userEmail=email.lower(), kind=kind, title=title[:150], body=body, orderId=order_id)
    except Exception:  # pragma: no cover - the database being unavailable is handled by the caller's own error
        pass


def _row(n: Notification) -> dict:
    return {'id': n.id, 'kind': n.kind, 'title': n.title, 'body': n.body, 'orderId': n.orderId, 'read': n.read, 'createdAt': n.createdAt}


@api_view(['GET'])
@permission_classes([AllowAny])
def notifications_view(request):
    """The signed-in user's latest notifications and how many are unread."""
    user = get_user_from_token(request)
    if not user:
        return Response({'detail': 'Please sign in.'}, status=http.HTTP_401_UNAUTHORIZED)
    mine = Notification.objects.filter(userEmail=user.email.lower())
    return Response({'unread': mine.filter(read=False).count(), 'items': [_row(n) for n in mine[:30]]})


@api_view(['POST'])
@permission_classes([AllowAny])
def notifications_read_view(request):
    """Mark one notification (`id`) or all of them as read."""
    user = get_user_from_token(request)
    if not user:
        return Response({'detail': 'Please sign in.'}, status=http.HTTP_401_UNAUTHORIZED)
    mine = Notification.objects.filter(userEmail=user.email.lower(), read=False)
    if request.data.get('id'):
        mine = mine.filter(id=request.data.get('id'))
    mine.update(read=True)
    return Response({'success': True})
