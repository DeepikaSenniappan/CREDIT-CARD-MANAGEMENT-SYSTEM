from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/logout/", views.LogoutView.as_view(), name="logout"),
    path("cards/", views.CardListCreateView.as_view(), name="cards"),
    path("cards/<uuid:id>/", views.CardDeleteView.as_view(), name="card-delete"),
    path("transactions/", views.TransactionListView.as_view(), name="transactions"),
    path("admin/users/", views.AdminUserListView.as_view(), name="admin-users"),
    path("admin/users/<int:pk>/", views.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/cards/", views.AdminCardListView.as_view(), name="admin-cards"),
    path("admin/transactions/", views.AdminTransactionListView.as_view(), name="admin-transactions"),
    path("admin/transactions/export/", views.admin_export_transactions, name="admin-transaction-export"),
    path("admin/summary/daily/", views.AdminDailySummaryView.as_view(), name="admin-daily-summary"),
]