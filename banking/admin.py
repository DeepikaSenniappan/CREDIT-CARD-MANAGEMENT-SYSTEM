from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminLog, Card, Transaction, User


@admin.register(User)
class BankingUserAdmin(UserAdmin):
    list_display = ("id", "username", "email", "is_staff", "is_active")


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "brand", "last4", "card_type", "created_at")
    readonly_fields = ("provider_payment_method_id",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "currency", "status", "created_at")
    list_filter = ("status", "currency", "created_at")
    readonly_fields = ("id", "user", "card", "amount", "currency", "status", "failure_reason", "created_at", "updated_at")


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "actor", "action", "target_type", "target_id")
    readonly_fields = ("actor", "action", "target_type", "target_id", "created_at", "details")