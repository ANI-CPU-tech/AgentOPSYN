import hashlib
import secrets
from django.db.models import Value
from django.utils.text import slugify
from rest_framework import serializers
from .models import User, Organization, APIKey, Team


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    org_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    org_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists!")
        return value

    def validate(self, data):
        org_name = data.get("org_name")
        org_id = data.get("org_id")

        if not org_name and not org_id:
            raise serializers.ValidationError(
                "You must provide either an Organization Name to create one, or an Invite Code to join one."
            )
        if org_name and org_id:
            raise serializers.ValidationError(
                "Provide either org_name OR org_id, not both."
            )
        return data

    def create(self, validated_data):
        org_id = validated_data.get("org_id")
        org_name = validated_data.get("org_name")

        if org_id:
            # 🚀 JOINING AN EXISTING ORG
            try:
                org = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                raise serializers.ValidationError({"org_id": "Invalid Invite Code."})

            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                org=org,
                role="engineer",  # Joiners are engineers, not admins!
            )
        else:
            # 🚀 CREATING A NEW ORG
            base_slug = slugify(org_name)
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            org = Organization.objects.create(name=org_name, slug=slug)

            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                org=org,
                role="admin",  # Creators are admins!
            )

        return user


class UserSerializer(serializers.ModelSerializer):
    org_id = serializers.UUIDField(source="org.id", read_only=True)
    org_name = serializers.CharField(source="org.name", read_only=True)
    team_id = serializers.UUIDField(source="team.id", read_only=True, allow_null=True)
    team_name = serializers.CharField(
        source="team.name", read_only=True, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "role",
            "org_id",
            "org_name",
            "team_id",
            "team_name",
            "created_at",
        ]
        read_only_fields = ["id", "org_id", "org_name", "created_at"]


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email"]

    def validate_email(self, value):
        user = self.context["request"].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value


class APIKeySerializer(serializers.ModelSerializer):
    raw_key = serializers.SerializerMethodField()

    class Meta:
        model = APIKey
        fields = ["id", "label", "raw_key", "created_at", "revoked_at", "is_active"]
        read_only_fields = ["id", "created_at", "revoked_at", "is_active"]

    def get_raw_key(self, obj):
        return self.context.get("raw_key")


class CreateAPIKeySerializer(serializers.Serializer):
    label = serializers.CharField(max_length=100)

    def create(self, validated_data):
        user = self.context["request"].user
        raw_key = secrets.token_urlsafe(40)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        api_key = APIKey.objects.create(
            label=validated_data["label"],
            key_hash=key_hash,
            user=user,
            org=user.org,
        )
        api_key._raw_key = raw_key
        return api_key


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "repo_full_name", "created_at"]
        read_only_fields = ["id", "created_at"]
