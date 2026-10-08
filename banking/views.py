import csv
from datetime import date

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .filters import TransactionFilter
from .models import AdminLog, Card, Transaction
from .permissions import IsStaffUser
from .serializers import AdminUserSerializer, CardSerializer, RegistrationSerializer, TransactionSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"detail": "A refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response({"detail": "Invalid refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class CardListCreateView(generics.ListCreateAPIView):
    serializer_class = CardSerializer

    def get_queryset(self):
        return Card.objects.filter(user=self.request.user)


class CardDeleteView(generics.DestroyAPIView):
    serializer_class = CardSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Card.objects.filter(user=self.request.user)


class TransactionListView(generics.ListAPIView):
    serializer_class = TransactionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TransactionFilter

    def get_queryset(self):
        return Transaction.objects.filter(user=self.request.user).select_related("card")


class AdminUserListView(generics.ListAPIView):
    queryset = User.objects.all().order_by("id")
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]

    def perform_update(self, serializer):
        user = serializer.save()
        AdminLog.objects.create(actor=self.request.user, action="USER_UPDATED", target_type="User", target_id=str(user.pk))


class AdminCardListView(generics.ListAPIView):
    queryset = Card.objects.select_related("user").all()
    serializer_class = CardSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]


class AdminTransactionListView(generics.ListAPIView):
    queryset = Transaction.objects.select_related("user", "card").all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsStaffUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("status", "user_id")


class AdminDailySummaryView(APIView):
    permission_classes = [IsAuthenticated, IsStaffUser]

    def get(self, request):
        raw_date = request.query_params.get("date")
        try:
            summary_date = date.fromisoformat(raw_date) if raw_date else timezone.localdate()
        except ValueError:
            return Response({"detail": "date must use YYYY-MM-DD format."}, status=400)
        transactions = Transaction.objects.filter(created_at__date=summary_date)
        summary = transactions.values("status").annotate(count=Count("id"), total=Sum("amount"))
        return Response({"date": summary_date, "by_status": list(summary)})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStaffUser])
def admin_export_transactions(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    writer = csv.writer(response)
    writer.writerow(("id", "user_id", "card_last4", "amount", "currency", "status", "created_at"))
    for transaction in Transaction.objects.select_related("card").all().iterator():
        writer.writerow((transaction.id, transaction.user_id, transaction.card.last4, transaction.amount,
                         transaction.currency, transaction.status, transaction.created_at.isoformat()))
    AdminLog.objects.create(actor=request.user, action="TRANSACTIONS_EXPORTED", target_type="Transaction")
    return response