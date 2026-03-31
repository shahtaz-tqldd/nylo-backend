import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
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


class ResourceName(models.TextChoices):
    PRODUCTS = "PRODUCTS", _("Products")
    CUSTOMERS = "CUSTOMERS", _("Customers")
    ORDERS = "ORDERS", _("Orders")
    MESSAGES = "MESSAGES", _("Messages")
    COUPONS = "COUPONS", _("Coupons")
    SALES = "SALES", _("Sales")


class ActionName(models.TextChoices):
    VIEW = "VIEW", _("View")
    CREATE = "CREATE", _("Create")
    UPDATE = "UPDATE", _("Update")
    DELETE = "DELETE", _("Delete")
    EXPORT = "EXPORT", _("Export")


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

        return AdminPermission.objects.filter(
            admin_profile__user=self,
            resource__name=resource,
            action__name=action,
        ).exists()


class AdminProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="admin_profile")
    job_title = models.CharField(max_length=100, blank=True, verbose_name=_("Job Title"))
    department = models.CharField(max_length=100, blank=True, verbose_name=_("Department"))
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


class Resource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50,
        choices=ResourceName.choices,
        unique=True,
        verbose_name=_("Resource Name"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Resource")
        verbose_name_plural = _("Resources")

    def __str__(self):
        return self.get_name_display()


class Action(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50,
        choices=ActionName.choices,
        unique=True,
        verbose_name=_("Action Name"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        verbose_name = _("Action")
        verbose_name_plural = _("Actions")

    def __str__(self):
        return self.get_name_display()


class AdminPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_profile = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        related_name="permissions",
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        verbose_name=_("Resource"),
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        verbose_name=_("Action"),
    )
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
                fields=["admin_profile", "resource", "action"],
                name="unique_admin_permission",
            )
        ]
        indexes = [
            models.Index(fields=["admin_profile", "resource", "action"]),
        ]

    def __str__(self):
        return f"{self.admin_profile.user.email} - {self.resource.name}:{self.action.name}"


class PermissionRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name=_("Role Name"))
    description = models.TextField(blank=True, verbose_name=_("Role Description"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Permission Role")
        verbose_name_plural = _("Permission Roles")

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        PermissionRole,
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        constraints = [
            models.UniqueConstraint(
                fields=["role", "resource", "action"],
                name="unique_role_permission",
            )
        ]

    def __str__(self):
        return f"{self.role.name} - {self.resource.name}:{self.action.name}"


class AdminRoleAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_profile = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        related_name="role_assignments",
    )
    role = models.ForeignKey(PermissionRole, on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Admin Role Assignment")
        verbose_name_plural = _("Admin Role Assignments")
        constraints = [
            models.UniqueConstraint(
                fields=["admin_profile", "role"],
                name="unique_admin_role_assignment",
            )
        ]

    def __str__(self):
        return f"{self.admin_profile.user.email} - {self.role.name}"
