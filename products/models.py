from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify
from app.base.models import BaseModel

hex_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}){1,2}$',
    message="Enter a valid hex color code"
)
class GenderChoice(models.TextChoices):
    MEN = 'men', 'Men'
    WOMEN = 'women', 'Women'
    UNISEX = 'unisex', 'Unisex'
    KIDS = 'kids', 'Kids'

class Collection(BaseModel):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=256, null=True, blank=True)
    type = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    slug = models.SlugField(unique=True, blank=True)

    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class Category(BaseModel):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Size(BaseModel):
    name = models.CharField(max_length=10)
    order = models.IntegerField(default=0)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['order']


class Color(BaseModel):
    name = models.CharField(max_length=20)
    color_code = models.CharField(max_length=7, validators=[hex_validator])
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Product(BaseModel):
    title = models.CharField(max_length=256)
    description = models.TextField(null=True, blank=True)
    brand = models.CharField(max_length=100, null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)

    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    gender = models.CharField(max_length=10, choices=GenderChoice.choices)
    
    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    features = models.JSONField(null=True, blank=True)
    specifications = models.JSONField(null=True, blank=True)
    tags = models.JSONField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    
    meta_title = models.CharField(max_length=255, null=True, blank=True)
    meta_description = models.CharField(max_length=255, null=True, blank=True)
    
    sku = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
      if not self.slug:
          base = slugify(self.title)
          slug = base
          
          n = 1
          while Product.objects.filter(slug=slug).exists():
              slug = f"{base}-{n}"
              n += 1
          
          self.slug = slug

      super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
        ]

class ProductVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    size = models.ForeignKey(Size, on_delete=models.SET_NULL, null=True, blank=True)
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    stock = models.IntegerField(default=0)
    
    image_url = models.URLField(null=True, blank=True)

    sku = models.CharField(max_length=100, null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.title} - {self.size.name if self.size else 'No Size'} - {self.color.name if self.color else 'No Color'}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.product.title)
            size_slug = slugify(self.size.name) if self.size else 'no-size'
            color_slug = slugify(self.color.name) if self.color else 'no-color'
            slug = f"{base_slug}-{size_slug}-{color_slug}"
            
            n = 1
            while ProductVariant.objects.filter(slug=slug).exists():
                slug = f"{slug}-{n}"
                n += 1
            
            self.slug = slug

        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [('product', 'size', 'color')]
        indexes = [
            models.Index(fields=['slug']),
        ]

class CollectionItem(BaseModel):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.collection.title} - {self.product.title}"
    
    class Meta:
        unique_together = [('collection', 'product')]
        ordering = ['order']


