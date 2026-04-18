import json

from django.db import IntegrityError
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated

from app.base.pagination import CustomPagination
from app.utils.cloudinary import delete_image
from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from products.models import (
    Brand,
    Category,
    Collection,
    CollectionItem,
    Color,
    GenderChoice,
    OfferProductItem,
    Product,
    SignatureProductItem,
    Size,
)
from products.v1.admin.serializers import (
    BrandSerializer,
    CategorySerializer,
    CollectionSerializer,
    ColorSerializer,
    FeaturedProductActionSerializer,
    FeaturedProductItemSerializer,
    OfferProductActionSerializer,
    OfferProductItemSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductSettingsSerializer,
    ProductUpsertSerializer,
    SizeSerializer,
)


class AdminResponseMixin:
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"
    success_list_message = "Items fetched successfully."
    success_detail_message = "Item fetched successfully."
    success_create_message = "Item created successfully."
    success_update_message = "Item updated successfully."
    success_delete_message = "Item deleted successfully."
    output_serializer_class = None

    def get_output_serializer_class(self):
        return self.output_serializer_class or self.get_serializer_class()

    def get_output_serializer(self, instance):
        serializer_class = self.get_output_serializer_class()
        return serializer_class(instance, context=self.get_serializer_context())

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page if page is not None else queryset, many=True)

        meta = None
        if page is not None:
            meta = {
                "total": self.paginator.page.paginator.count,
                "page": self.paginator.page.number,
                "page_size": self.paginator.page.paginator.per_page,
            }

        return APIResponse.success(data=serializer.data, meta=meta, message=self.success_list_message)

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_output_serializer(self.get_object())
        return APIResponse.success(data=serializer.data, message=self.success_detail_message)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self.get_input_data())
        serializer.is_valid(raise_exception=True)
        instance = self.perform_create(serializer)
        output = self.get_output_serializer(instance)
        return APIResponse.success(
            data=output.data,
            message=self.success_create_message,
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=self.get_input_data(), partial=True)
        serializer.is_valid(raise_exception=True)
        instance = self.perform_update(serializer)
        output = self.get_output_serializer(instance)
        return APIResponse.success(data=output.data, message=self.success_update_message)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return APIResponse.success(message=self.success_delete_message)

    def get_input_data(self):
        return self.request.data

    def perform_create(self, serializer):
        return serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        return serializer.save(updated_by=self.request.user)


class AdminCreateAPIView(AdminResponseMixin, generics.CreateAPIView):
    pass


class AdminListAPIView(AdminResponseMixin, generics.ListAPIView):
    pass


class AdminRetrieveAPIView(AdminResponseMixin, generics.RetrieveAPIView):
    pass


class AdminUpdateAPIView(AdminResponseMixin, generics.UpdateAPIView):
    pass


class AdminDeleteAPIView(AdminResponseMixin, generics.DestroyAPIView):
    pass


class CategoryCreateAPIView(AdminCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    success_create_message = "Category created successfully."


class CategoryUpdateAPIView(AdminUpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    success_update_message = "Category updated successfully."


class CategoryDeleteAPIView(AdminDeleteAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    success_delete_message = "Category deleted successfully."


class BrandCreateAPIView(AdminCreateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    success_create_message = "Brand created successfully."


class BrandUpdateAPIView(AdminUpdateAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    success_update_message = "Brand updated successfully."


class BrandDeleteAPIView(AdminDeleteAPIView):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    success_delete_message = "Brand deleted successfully."


class SizeCreateAPIView(AdminCreateAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    success_create_message = "Size created successfully."


class SizeUpdateAPIView(AdminUpdateAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    success_update_message = "Size updated successfully."


class SizeDeleteAPIView(AdminDeleteAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    success_delete_message = "Size deleted successfully."


class ColorCreateAPIView(AdminCreateAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    success_create_message = "Color created successfully."


class ColorUpdateAPIView(AdminUpdateAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    success_update_message = "Color updated successfully."


class ColorDeleteAPIView(AdminDeleteAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    success_delete_message = "Color deleted successfully."


class CollectionQuerysetMixin:
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = Collection.objects.all().order_by("title")
        text = (self.request.query_params.get("text") or self.request.query_params.get("search") or "").strip()
        if text:
            queryset = queryset.filter(
                Q(title__icontains=text)
                | Q(subtitle__icontains=text)
                | Q(type__icontains=text)
                | Q(description__icontains=text)
                | Q(slug__icontains=text)
            )
        return queryset


class CollectionListAPIView(CollectionQuerysetMixin, AdminListAPIView):
    serializer_class = CollectionSerializer
    success_list_message = "Collections fetched successfully."


class CollectionDetailsAPIView(CollectionQuerysetMixin, AdminRetrieveAPIView):
    serializer_class = CollectionSerializer
    success_detail_message = "Collection fetched successfully."


class CollectionCreateAPIView(AdminCreateAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    success_create_message = "Collection created successfully."


class CollectionUpdateAPIView(AdminUpdateAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    success_update_message = "Collection updated successfully."


class CollectionDeleteAPIView(AdminDeleteAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    success_delete_message = "Collection deleted successfully."


class ProductQuerysetMixin:
    pagination_class = CustomPagination

    def get_base_queryset(self):
        return (
            Product.objects.select_related("category", "brand")
            .annotate(
                orders_count=Count("order_items__order", distinct=True),
                is_signature_item=Exists(
                    SignatureProductItem.objects.filter(product_id=OuterRef("pk"))
                ),
                is_offer_item=Exists(
                    OfferProductItem.objects.filter(product_id=OuterRef("pk"))
                ),
            )
            .prefetch_related(
                Prefetch("variants", to_attr="prefetched_variants"),
                Prefetch(
                    "collectionitem_set",
                    queryset=CollectionItem.objects.select_related("collection"),
                    to_attr="prefetched_collection_items",
                ),
            )
            .all()
        )

    def get_queryset(self):
        queryset = self.get_base_queryset()
        params = self.request.query_params

        text = params.get("text") or params.get("search")
        if text:
            queryset = queryset.filter(
                Q(title__icontains=text)
                | Q(description__icontains=text)
                | Q(brand__name__icontains=text)
                | Q(sku__icontains=text)
            )

        brand_id = params.get("brand_id")
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        category_id = params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        gender = params.get("gender")
        if gender:
            queryset = queryset.filter(gender=gender)

        size_ids = params.getlist("size_id") or params.getlist("size_ids")
        if len(size_ids) == 1 and "," in size_ids[0]:
            size_ids = [item.strip() for item in size_ids[0].split(",") if item.strip()]
        if size_ids:
            queryset = queryset.filter(variants__size_id__in=size_ids)

        color_ids = params.getlist("color_id") or params.getlist("color_ids")
        if len(color_ids) == 1 and "," in color_ids[0]:
            color_ids = [item.strip() for item in color_ids[0].split(",") if item.strip()]
        if color_ids:
            queryset = queryset.filter(variants__color_id__in=color_ids)

        collection_id = params.get("collection_id")
        if collection_id:
            queryset = queryset.filter(collectionitem__collection_id=collection_id)

        min_price = params.get("min_price")
        if min_price not in (None, ""):
            queryset = queryset.filter(price__gte=min_price)

        max_price = params.get("max_price")
        if max_price not in (None, ""):
            queryset = queryset.filter(price__lte=max_price)

        return queryset.distinct().order_by("-created_at")

    def get_input_data(self):
        product_data = self.request.data.get("product_data")
        if product_data:
            try:
                return json.loads(product_data)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({"product_data": "Invalid JSON payload."}) from exc
        return self.request.data

    def refresh_product(self, product):
        return self.get_base_queryset().get(id=product.id)


class ProductListAPIView(ProductQuerysetMixin, AdminListAPIView):
    serializer_class = ProductListSerializer
    success_list_message = "Products fetched successfully."


class ProductDetailsAPIView(ProductQuerysetMixin, AdminRetrieveAPIView):
    serializer_class = ProductDetailSerializer
    success_detail_message = "Product fetched successfully."


class ProductCreateAPIView(ProductQuerysetMixin, AdminCreateAPIView):
    serializer_class = ProductUpsertSerializer
    output_serializer_class = ProductDetailSerializer
    success_create_message = "Product created successfully."

    def get_input_data(self):
        return ProductQuerysetMixin.get_input_data(self)

    def perform_create(self, serializer):
        product = serializer.save()
        return self.refresh_product(product)


class ProductUpdateAPIView(ProductQuerysetMixin, AdminUpdateAPIView):
    serializer_class = ProductUpsertSerializer
    output_serializer_class = ProductDetailSerializer
    success_update_message = "Product updated successfully."

    def get_input_data(self):
        return ProductQuerysetMixin.get_input_data(self)

    def perform_update(self, serializer):
        product = serializer.save()
        return self.refresh_product(product)


class ProductDeleteAPIView(ProductQuerysetMixin, AdminDeleteAPIView):
    serializer_class = ProductDetailSerializer
    success_delete_message = "Product deleted successfully."

    def perform_destroy(self, instance):
        if instance.image_url:
            delete_image(image_url=instance.image_url)
        for variant in instance.variants.exclude(image_url__isnull=True).exclude(image_url=""):
            delete_image(image_url=variant.image_url)
        instance.delete()


class ProductSettingsAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, *args, **kwargs):
        data = {
            "brands": Brand.objects.all().order_by("name"),
            "categories": Category.objects.all().order_by("name"),
            "sizes": Size.objects.all().order_by("order", "name"),
            "colors": Color.objects.all().order_by("name"),
            "collections": Collection.objects.all().order_by("title"),
            "genders": [{"value": value, "label": label} for value, label in GenderChoice.choices],
        }
        serializer = ProductSettingsSerializer(data)
        return APIResponse.success(data=serializer.data, message="Product settings fetched successfully.")


class SignatureProductCreateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = FeaturedProductActionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item, created = SignatureProductItem.objects.get_or_create(
                product=serializer.product,
                defaults={"created_by": request.user, "updated_by": request.user},
            )
        except IntegrityError:
            item = SignatureProductItem.objects.get(product=serializer.product)
            created = False

        if not created:
            item.updated_by = request.user
            item.save(update_fields=["updated_by", "updated_at"])

        output = FeaturedProductItemSerializer(item)
        return APIResponse.success(
            data=output.data,
            message="Product added to signature items successfully.",
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SignatureProductDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = SignatureProductItem.objects.select_related("product")
    lookup_field = "product_id"
    lookup_url_kwarg = "product_id"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(message="Product removed from signature items successfully.")


class OfferProductCreateAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = OfferProductActionSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        defaults = {
            "offer_ends_at": serializer.validated_data.get("offer_ends_at"),
            "created_by": request.user,
            "updated_by": request.user,
        }

        try:
            item, created = OfferProductItem.objects.get_or_create(
                product=serializer.product,
                defaults=defaults,
            )
        except IntegrityError:
            item = OfferProductItem.objects.get(product=serializer.product)
            created = False

        if not created:
            item.offer_ends_at = serializer.validated_data.get("offer_ends_at", item.offer_ends_at)
            item.updated_by = request.user
            item.save(update_fields=["offer_ends_at", "updated_by", "updated_at"])

        output = OfferProductItemSerializer(item)
        return APIResponse.success(
            data=output.data,
            message="Product added to offer items successfully.",
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class OfferProductDeleteAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    queryset = OfferProductItem.objects.select_related("product")
    lookup_field = "product_id"
    lookup_url_kwarg = "product_id"

    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(message="Product removed from offer items successfully.")
