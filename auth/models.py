import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

USER_ROLE = (
    ("CUSTOMER", "customer"),
    ("ADMIN", "admin"),
)
USER_STATUS = (
    ("INACTIVE", "inactive"),
    ("ACTIVE", "active"),
    ("BLOCKED", "blocked"),
)

phone_regex = RegexValidator(
    regex=r"^\+?1?\d{6,15}$", message=_("Phone Number should start with +")
)

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        unique=True,
        verbose_name=_("Email Address"),
        help_text=_("A valid email address is required!"),
    )

    role = models.CharField(
        max_length=10,
        choices=USER_ROLE,
        default="CUSTOMER",
        verbose_name=_("User Role"),
    )

    # Personal information
    first_name = models.CharField(max_length=32, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=32, verbose_name=_("Last Name"))
    phone = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        verbose_name=_("Phone Number"),
    )

    # Address fields
    address_line_1 = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Address Line 1")
    )
    address_line_2 = models.CharField(
        max_length=100, blank=True, null=True, verbose_name=_("Address Line 2")
    )
    city = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("City")
    )
    state_province = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("State/Province")
    )
    postal_code = models.CharField(
        max_length=20, blank=True, null=True, verbose_name=_("Postal/Zip Code")
    )
    country = models.CharField(
        max_length=50, blank=True, null=True, verbose_name=_("Country")
    )

    # Additional information
    profile_picture_url = models.URLField(
        blank=True, null=True, verbose_name=_("Profile Picture URL")
    )

    # Account status
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date Joined"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Last Update"))
    last_login = models.DateTimeField(auto_now=True, verbose_name=_("Last Login"))
    status = models.CharField(
        max_length=10,
        choices=USER_STATUS,
        default="INACTIVE",
        verbose_name=_("User Status"),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email
        super().save(*args, **kwargs)

    @property
    def is_customer(self):
        return self.role == "CUSTOMER"

    @property
    def is_admin(self):
        return self.role == "ADMIN"
    
    def has_permission(self, resource, action):
        """Check if user has a specific permission"""
        if self.is_superuser:
            return True
        
        if not self.is_admin:
            return False
        
        return AdminPermission.objects.filter(
            admin_profile__user=self,
            resource=resource,
            action=action
        ).exists()


class AdminProfile(models.Model):
    """Extended profile for admin users with role assignment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='admin_profile'
    )
    job_title = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name=_("Job Title")
    )
    department = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name=_("Department")
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_admins',
        verbose_name=_("Assigned By")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name=_("Active Status"))

    class Meta:
        verbose_name = _("Admin Profile")
        verbose_name_plural = _("Admin Profiles")

    def __str__(self):
        return f"{self.user.email} - {self.job_title or 'Admin'}"


class Resource(models.Model):
    """Define resources (domains) in the system"""
    RESOURCE_CHOICES = (
        ('PRODUCTS', 'Products'),
        ('CUSTOMERS', 'Customers'),
        ('ORDERS', 'Orders'),
        ('MESSAGES', 'Messages'),
        ('COUPONS', 'Coupons'),
        ('SALES', 'Sales'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50, 
        choices=RESOURCE_CHOICES, 
        unique=True,
        verbose_name=_("Resource Name")
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Description")
    )

    class Meta:
        verbose_name = _("Resource")
        verbose_name_plural = _("Resources")

    def __str__(self):
        return self.get_name_display()


class Action(models.Model):
    """Define actions that can be performed on resources"""
    ACTION_CHOICES = (
        ('VIEW', 'View'),
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('EXPORT', 'Export'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=50, 
        choices=ACTION_CHOICES, 
        unique=True,
        verbose_name=_("Action Name")
    )
    description = models.TextField(
        blank=True, 
        verbose_name=_("Description")
    )

    class Meta:
        verbose_name = _("Action")
        verbose_name_plural = _("Actions")

    def __str__(self):
        return self.get_name_display()


class AdminPermission(models.Model):
    """Granular permissions for admin users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_profile = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        verbose_name=_("Resource")
    )
    action = models.ForeignKey(
        Action,
        on_delete=models.CASCADE,
        verbose_name=_("Action")
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_permissions'
    )

    class Meta:
        verbose_name = _("Admin Permission")
        verbose_name_plural = _("Admin Permissions")
        unique_together = ('admin_profile', 'resource', 'action')
        indexes = [
            models.Index(fields=['admin_profile', 'resource', 'action']),
        ]

    def __str__(self):
        return f"{self.admin_profile.user.email} - {self.resource.name}:{self.action.name}"


class PermissionRole(models.Model):
    """Predefined role templates for quick assignment"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100, 
        unique=True,
        verbose_name=_("Role Name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Role Description")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Permission Role")
        verbose_name_plural = _("Permission Roles")

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Link roles to specific permissions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        PermissionRole,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    action = models.ForeignKey(Action, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Role Permission")
        verbose_name_plural = _("Role Permissions")
        unique_together = ('role', 'resource', 'action')

    def __str__(self):
        return f"{self.role.name} - {self.resource.name}:{self.action.name}"


class AdminRoleAssignment(models.Model):
    """Assign predefined roles to admin users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_profile = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        related_name='role_assignments'
    )
    role = models.ForeignKey(
        PermissionRole,
        on_delete=models.CASCADE
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='role_assignments_made'
    )

    class Meta:
        verbose_name = _("Admin Role Assignment")
        verbose_name_plural = _("Admin Role Assignments")
        unique_together = ('admin_profile', 'role')

    def __str__(self):
        return f"{self.admin_profile.user.email} - {self.role.name}"