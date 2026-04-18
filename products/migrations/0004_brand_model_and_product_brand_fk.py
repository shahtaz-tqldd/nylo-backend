import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from django.utils.text import slugify


def migrate_product_brands(apps, schema_editor):
    Brand = apps.get_model("products", "Brand")
    Product = apps.get_model("products", "Product")

    brand_cache = {}

    for product in Product.objects.exclude(brand__isnull=True).exclude(brand=""):
        brand_name = (product.brand or "").strip()
        if not brand_name:
            continue

        brand = brand_cache.get(brand_name)
        if brand is None:
            base_slug = slugify(brand_name) or "brand"
            slug = base_slug
            index = 1
            while Brand.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{index}"
                index += 1

            brand, _ = Brand.objects.get_or_create(
                name=brand_name,
                defaults={"slug": slug},
            )
            brand_cache[brand_name] = brand

        product.brand_ref_id = brand.id
        product.save(update_fields=["brand_ref"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("products", "0003_offerproductitem_signatureproductitem"),
    ]

    operations = [
        migrations.CreateModel(
            name="Brand",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(blank=True, unique=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products_brand_created_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="products_brand_updated_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="product",
            name="brand_ref",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="products",
                to="products.brand",
            ),
        ),
        migrations.RunPython(migrate_product_brands, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="product",
            name="brand",
        ),
        migrations.RenameField(
            model_name="product",
            old_name="brand_ref",
            new_name="brand",
        ),
    ]
