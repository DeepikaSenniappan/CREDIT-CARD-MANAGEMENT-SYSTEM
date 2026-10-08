from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import Card, Transaction, User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=10, style={"input_type": "password"})
    email = serializers.EmailField(validators=[UniqueValidator(queryset=User.objects.all())])

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")
        read_only_fields = ("id",)

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class CardSerializer(serializers.ModelSerializer):
    masked_number = serializers.ReadOnlyField()

    class Meta:
        model = Card
        fields = (
            "id", "provider_payment_method_id", "brand", "last4", "masked_number",
            "card_type", "expiry_month", "expiry_year", "created_at",
        )
        read_only_fields = ("id", "created_at")
        extra_kwargs = {"provider_payment_method_id": {"write_only": True}}

    def to_internal_value(self, data):
        forbidden = {"number", "card_number", "pan", "cvv", "cvc", "security_code"}
        if forbidden.intersection(data.keys()):
            raise serializers.ValidationError({
                "non_field_errors": ["Card numbers and security codes must never be submitted or stored."]
            })
        return super().to_internal_value(data)

    def validate_last4(self, value):
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError("Provide exactly the final four digits.")
        return value

    def validate_expiry_month(self, value):
        if not 1 <= value <= 12:
            raise serializers.ValidationError("Expiry month must be between 1 and 12.")
        return value

    def create(self, validated_data):
        return Card.objects.create(user=self.context["request"].user, **validated_data)


class TransactionSerializer(serializers.ModelSerializer):
    card_mask = serializers.ReadOnlyField(source="card.masked_number")

    class Meta:
        model = Transaction
        fields = ("id", "card_mask", "amount", "currency", "status", "failure_reason", "created_at", "updated_at")


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_active", "is_staff", "date_joined")
        read_only_fields = ("id", "username", "email", "date_joined")