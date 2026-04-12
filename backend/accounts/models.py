from enum import unique
from django.db import models
import uuid
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=25)
    slug = models.SlugField(max_length=100, unique=True)
    plan = models.CharField(
        max_length=20,
        choices=[("free", "Free"), ("pro", "Pro"), ("enterprise", "Enterprise")],
        default="free",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password, org, role="engineer", **extra_fields):
        if not email:
            raise ValueError("Email is Required")
        email = self.normalize_email(email)
        user = self.model(email=email, org=org, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_super_user(self, email, password, **extra_fields):
        org, _ = Organization.objects.get_or_create(
            slug="superadmin", defaults={"name": "Super Admin", "plan": "enterprise"}
        )
        extra_fields.setdefault("role", "admin")
        return self.create_user(email, password, org=org, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("engineer", "Engineer"),
        ("viewer", "Viewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="engineer")
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="users"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    label = models.CharField(max_length=100)
    key_hash = models.CharField(max_length=255, unique=True, db_index=True)
    user = (models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys"),)
    org = (
        models.ForeignKey(
            Organization, on_delete=models.CASCADE, related_name="api_keys"
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    @property
    def is_active(self):
        return self.revoked_at is None

    def __str__(self):
        return f"{self.label} ({'active' if self.is_active else 'revoked'})"
