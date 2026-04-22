from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from .models import Message
from .serializers import MessageSerializer


class MessageListAPIView(generics.ListAPIView):
	serializer_class = MessageSerializer
	permission_classes = [permissions.IsAuthenticated]

	def get_queryset(self):
		target_user_id = self.request.query_params.get("user_id")
		if not target_user_id:
			raise ValidationError({"user_id": "This query parameter is required."})

		try:
			target_user_id = int(target_user_id)
		except (TypeError, ValueError):
			raise ValidationError({"user_id": "A valid integer user id is required."})

		if not User.objects.filter(id=target_user_id).exists():
			raise ValidationError({"user_id": "Receiver user does not exist."})

		return Message.objects.select_related("sender", "receiver").filter(
			Q(sender=self.request.user, receiver_id=target_user_id)
			| Q(sender_id=target_user_id, receiver=self.request.user)
		).order_by("created_at")


class MessageCreateAPIView(generics.CreateAPIView):
	serializer_class = MessageSerializer
	permission_classes = [permissions.IsAuthenticated]

	def perform_create(self, serializer):
		receiver_id = self.request.data.get("receiver")
		if receiver_id is None:
			raise ValidationError({"receiver": "This field is required."})

		try:
			receiver_id = int(receiver_id)
		except (TypeError, ValueError):
			raise ValidationError({"receiver": "A valid integer user id is required."})

		if receiver_id == self.request.user.id:
			raise ValidationError({"receiver": "You cannot send a message to yourself."})

		try:
			receiver = User.objects.get(id=receiver_id)
		except User.DoesNotExist:
			raise ValidationError({"receiver": "Receiver user does not exist."})

		serializer.save(sender=self.request.user, receiver=receiver)
