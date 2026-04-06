import json

from django.db.models import IntegerField, Max, Prefetch, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import generics, pagination, serializers, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView

from app.base.pagination import CustomPagination
from app.utils.cloudinary import delete_image
from app.utils.response import APIResponse
from auth.permissions import IsAdmin
from products.models import Category, Collection, CollectionItem, Color, Product, Size
from products.v1.admin.serializers import (
    AdminProductListSerializer,
    CategorySerializer,
    CollectionProductBulkAddSerializer,
    CollectionSerializer,
    ColorSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
    ProductUpsertSerializer,
    SizeSerializer,
)


class AdminResponseMixin:
    success_list_message = "Items fetched successfully."
    success_create_message = "Item created successfully."
    success_update_message = "Item updated successfully."
    success_delete_message = "Item deleted successfully."
    detail_serializer_class = None

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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(created_by=request.user, updated_by=request.user)
        output = self.get_output_serializer(instance)
        return APIResponse.success(
            data=output.data,
            message=self.success_create_message,
            status=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_output_serializer(instance)
        return APIResponse.success(data=serializer.data, message="Item fetched successfully.")

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(updated_by=request.user)
        output = self.get_output_serializer(instance)
        return APIResponse.success(data=output.data, message=self.success_update_message)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return APIResponse.success(message=self.success_delete_message)

    def get_output_serializer(self, instance):
        serializer_class = self.detail_serializer_class or self.get_serializer_class()
        return serializer_class(instance, context=self.get_serializer_context())


class AdminModelListCreateAPIView(AdminResponseMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]


class AdminModelDetailAPIView(AdminResponseMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"


class CategoryListCreateAPIView(AdminModelListCreateAPIView):
    queryset = Category.objects.all().order_by("name")
    serializer_class = CategorySerializer
    success_list_message = "Categories fetched successfully."
    success_create_message = "Category created successfully."


class CategoryDetailAPIView(AdminModelDetailAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    success_update_message = "Category updated successfully."
    success_delete_message = "Category deleted successfully."


class SizeListCreateAPIView(AdminModelListCreateAPIView):
    queryset = Size.objects.all().order_by("order", "name")
    serializer_class = SizeSerializer
    success_list_message = "Sizes fetched successfully."
    success_create_message = "Size created successfully."


class SizeDetailAPIView(AdminModelDetailAPIView):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    success_update_message = "Size updated successfully."
    success_delete_message = "Size deleted successfully."


class ColorListCreateAPIView(AdminModelListCreateAPIView):
    queryset = Color.objects.all().order_by("name")
    serializer_class = ColorSerializer
    success_list_message = "Colors fetched successfully."
    success_create_message = "Color created successfully."


class ColorDetailAPIView(AdminModelDetailAPIView):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    success_update_message = "Color updated successfully."
    success_delete_message = "Color deleted successfully."


class CollectionListCreateAPIView(AdminModelListCreateAPIView):
    serializer_class = CollectionSerializer
    pagination_class = CustomPagination
    success_list_message = "Collections fetched successfully."
    success_create_message = "Collection created successfully."

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


class CollectionListAPIView(AdminResponseMixin, generics.ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = CollectionSerializer
    pagination_class = CustomPagination
    success_list_message = "Collections fetched successfully."

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


class CollectionDetailAPIView(AdminModelDetailAPIView):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    success_update_message = "Collection updated successfully."
    success_delete_message = "Collection deleted successfully."


class CollectionBulkAddProductsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, *args, **kwargs):
        collection = generics.get_object_or_404(Collection, id=kwargs["id"])
        serializer = CollectionProductBulkAddSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        products = serializer.context["products"]
        existing_ids = set(
            CollectionItem.objects.filter(collection=collection, product_id__in=serializer.validated_data["product_ids"])
            .values_list("product_id", flat=True)
        )
        next_order = (
            CollectionItem.objects.filter(collection=collection).aggregate(max_order=Max("order"))["max_order"] or 0
        )
        items = []
        for product in products:
            if product.id in existing_ids:
                continue
            next_order += 1
            items.append(
                CollectionItem(
                    collection=collection,
                    product=product,
                    order=next_order,
                    created_by=request.user,
                    updated_by=request.user,
                )
            )

        CollectionItem.objects.bulk_create(items)
        return APIResponse.success(
            data={"created_count": len(items), "skipped_count": len(existing_ids)},
            message="Products added to collection successfully.",
            status=status.HTTP_201_CREATED,
        )


class ProductQuerysetMixin:
    pagination_class = CustomPagination

    def get_base_queryset(self):
        return (
            Product.objects.select_related("category")
            .prefetch_related(
                Prefetch("variants", to_attr="prefetched_variants"),
                Prefetch("collectionitem_set", queryset=CollectionItem.objects.select_related("collection"), to_attr="prefetched_collection_items"),
            )
            .all()
        )

    def apply_filters(self, queryset):
        params = self.request.query_params

        text = params.get("text")
        if text:
            queryset = queryset.filter(
                Q(title__icontains=text)
                | Q(description__icontains=text)
                | Q(brand__icontains=text)
                | Q(sku__icontains=text)
            )

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


class AdminProductListCreateAPIView(ProductQuerysetMixin, generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return ProductUpsertSerializer
        return ProductListSerializer

    def get_queryset(self):
        return self.apply_filters(self.get_base_queryset())

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = ProductListSerializer(page, many=True)
        payload = {
            "meta": {
                "total": self.paginator.page.paginator.count,
                "page": self.paginator.page.number,
                "page_size": self.get_page_size(request),
            },
            "data": serializer.data,
        }
        return APIResponse.success(data=payload, message="Products fetched successfully.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self._get_payload(), context={"request": request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        output = ProductDetailSerializer(self._refresh_product(product))
        return APIResponse.success(
            data=output.data,
            message="Product created successfully.",
            status=status.HTTP_201_CREATED,
        )

    def _get_payload(self):
        product_data = self.request.data.get("product_data")
        if product_data:
            try:
                return json.loads(product_data)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({"product_data": "Invalid JSON payload."}) from exc
        return self.request.data

    def _refresh_product(self, product):
        return self.get_base_queryset().get(id=product.id)


class AdminProductDetailAPIView(ProductQuerysetMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return ProductUpsertSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        return self.get_base_queryset()

    def retrieve(self, request, *args, **kwargs):
        serializer = ProductDetailSerializer(self.get_object())
        return APIResponse.success(data=serializer.data, message="Product fetched successfully.")

    def patch(self, request, *args, **kwargs):
        product = self.get_object()
        serializer = self.get_serializer(product, data=self._get_payload(), partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        output = ProductDetailSerializer(self.get_queryset().get(id=product.id))
        return APIResponse.success(data=output.data, message="Product updated successfully.")

    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        if product.image_url:
            delete_image(image_url=product.image_url)
        for variant in product.variants.exclude(image_url__isnull=True).exclude(image_url=""):
            delete_image(image_url=variant.image_url)
        product.delete()
        return APIResponse.success(message="Product deleted successfully.")

    def _get_payload(self):
        product_data = self.request.data.get("product_data")
        if product_data:
            try:
                return json.loads(product_data)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({"product_data": "Invalid JSON payload."}) from exc
        return self.request.data


class AdminProductListAPIView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminProductListSerializer
    pagination_class = CustomPagination

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

        return APIResponse.success(
            data=serializer.data,
            meta=meta,
            message="Products fetched successfully.",
        )

    def get_queryset(self):
        queryset = (
            Product.objects.select_related("category")
            .prefetch_related("variants", "variants__size", "variants__color")
            .annotate(
                total_stock=Coalesce(
                    Sum("variants__stock"),
                    Value(0),
                    output_field=IntegerField(),
                ),
                total_orders_placed=Coalesce(
                    Sum("order_items__quantity"),
                    Value(0),
                    output_field=IntegerField(),
                ),
            )
            .order_by("-created_at")
            .distinct()
        )

        params = self.request.query_params

        category_ids = params.getlist("category")
        genders = params.getlist("gender")
        size_ids = params.getlist("size")
        color_ids = params.getlist("color")
        is_active = params.get("is_active")
        search = params.get("search")

        if category_ids:
            queryset = queryset.filter(category_id__in=category_ids)

        if genders:
            queryset = queryset.filter(gender__in=genders)

        if size_ids:
            queryset = queryset.filter(variants__size_id__in=size_ids)

        if color_ids:
            queryset = queryset.filter(variants__color_id__in=color_ids)

        if is_active is not None:
            if is_active.lower() == "true":
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == "false":
                queryset = queryset.filter(is_active=False)

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(sku__icontains=search)
                | Q(slug__icontains=search)
                | Q(brand__icontains=search)
                | Q(category__name__icontains=search)
            )

        return queryset.distinct()
