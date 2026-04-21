import uuid

from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core import signing
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


phone_regex = RegexValidator(
    regex=r"^\+?1?\d{6,15}$",
    message=_("Phone number must be between 6 and 15 digits and may start with '+'."),
)


class UserRole(models.TextChoices):
    CUSTOMER = "CUSTOMER", _("Customer")
    ADMIN = "ADMIN", _("Admin")


class UserStatus(models.TextChoices):
    INACTIVE = "INACTIVE", _("Inactive")
    ACTIVE = "ACTIVE", _("Active")
    BLOCKED = "BLOCKED", _("Blocked")


class AdminModule(models.TextChoices):
    PRODUCT_MANAGEMENT = "PRODUCT_MANAGEMENT", _("Product Management")
    CUSTOMER_MANAGEMENT = "CUSTOMER_MANAGEMENT", _("Customer Management")
    ORDER_MANAGEMENT = "ORDER_MANAGEMENT", _("Order Management")
    COUPON_MANAGEMENT = "COUPON_MANAGEMENT", _("Coupon Management")
    SALES = "SALES", _("Sales")
    CHAT_SUPPORT = "CHAT_SUPPORT", _("Chat Support")


class AdminAction(models.TextChoices):
    VIEW = "VIEW", _("View")
    CREATE = "CREATE", _("Create")
    UPDATE = "UPDATE", _("Update")
    DELETE = "DELETE", _("Delete")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The email field is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.CUSTOMER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", UserStatus.ACTIVE)
        extra_fields.setdefault("role", UserRole.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        verbose_name=_("Email Address"),
        help_text=_("A valid email address is required."),
    )
    first_name = models.CharField(max_length=32, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=32, verbose_name=_("Last Name"))
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        verbose_name=_("Phone Number"),
    )
    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.CUSTOMER,
        verbose_name=_("User Role"),
    )
    status = models.CharField(
        max_length=16,
        choices=UserStatus.choices,
        default=UserStatus.INACTIVE,
        verbose_name=_("User Status"),
    )
    address_line_1 = models.CharField(max_length=100, blank=True, verbose_name=_("Address Line 1"))
    address_line_2 = models.CharField(max_length=100, blank=True, verbose_name=_("Address Line 2"))
    city = models.CharField(max_length=50, blank=True, verbose_name=_("City"))
    state_province = models.CharField(max_length=50, blank=True, verbose_name=_("State/Province"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Postal/Zip Code"))
    country = models.CharField(max_length=50, blank=True, verbose_name=_("Country"))
    profile_picture_url = models.URLField(blank=True, verbose_name=_("Profile Picture URL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    is_staff = models.BooleanField(default=False, verbose_name=_("Staff Status"))
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name=_("Date Joined"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def region(self):
        return f"{self.city} {self.country}".strip()

    @property
    def is_customer(self):
        return self.role == UserRole.CUSTOMER

    @property
    def is_admin_user(self):
        return self.role == UserRole.ADMIN

    def has_role_permission(self, resource, action):
        if self.is_superuser:
            return True

        if self.role != UserRole.ADMIN:
            return False

        admin_permission = AdminPermission.objects.filter(
            admin_profile__user=self,
            permission__module=resource,
        ).values_list("actions", flat=True).first()
        return action in (admin_permission or [])


class AdminProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    job_title = models.CharField(max_length=100, blank=True, verbose_name=_("Job Title"))
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_admins",
        verbose_name=_("Assigned By"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active Status"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Admin Profile")
        verbose_name_plural = _("Admin Profiles")

    def __str__(self):
        return f"{self.user.email} - {self.job_title or 'Admin'}"


class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    ACCEPTED = "ACCEPTED", _("Accepted")
    REVOKED = "REVOKED", _("Revoked")
    EXPIRED = "EXPIRED", _("Expired")


class AdminInvitation(models.Model):
    TOKEN_SALT = "admin-invitation"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(verbose_name=_("Email Address"))
    job_title = models.CharField(max_length=100, blank=True, verbose_name=_("Job Title"))
    direct_permissions = models.JSONField(default=list, blank=True, verbose_name=_("Direct Permissions"))
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admin_invitations_sent",
        verbose_name=_("Invited By"),
    )
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Accepted At"))
    revoked_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Revoked At"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Admin Invitation")
        verbose_name_plural = _("Admin Invitations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.email} - {self.status}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def status(self):
        if self.accepted_at:
            return InvitationStatus.ACCEPTED
        if self.revoked_at:
            return InvitationStatus.REVOKED
        if self.is_expired:
            return InvitationStatus.EXPIRED
        return InvitationStatus.PENDING

    @property
    def invitee_name(self):
        return self.email

    def issue_token(self):
        payload = {
            "invitation_id": str(self.id),
            "email": self.email,
            "expires_at": self.expires_at.isoformat(),
        }
        return signing.dumps(payload, salt=self.TOKEN_SALT)

    @classmethod
    def decode_token(cls, token):
        return signing.loads(token, salt=cls.TOKEN_SALT)


class Permission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    module = models.CharField(
        max_length=50,
        choices=AdminModule.choices,
        unique=True,
        verbose_name=_("Module"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")

    def __str__(self):
        return self.get_module_display()


class AdminPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_profile = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="admin_permissions",
        verbose_name=_("Permission"),
    )
    actions = models.JSONField(default=list, blank=True, verbose_name=_("Allowed Actions"))
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_permissions",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Admin Permission")
        verbose_name_plural = _("Admin Permissions")
        constraints = [
            models.UniqueConstraint(
                fields=["admin_profile", "permission"],
                name="unique_admin_permission",
            )
        ]
        indexes = [
            models.Index(fields=["admin_profile", "permission"]),
        ]

    def __str__(self):
        return f"{self.admin_profile.user.email} - {self.permission.module}:{','.join(self.actions)}"
