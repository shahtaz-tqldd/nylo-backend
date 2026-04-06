from django.db.models import Prefetch, Q

from rest_framework import generics
from rest_framework.permissions import AllowAny

from app.base.pagination import CustomPagination
from app.utils.response import APIResponse
from products.models import (
    CollectionItem, 
    Product, 
    Category, 
    Collection, 
    CollectionItem, 
    Color, 
    Product,
    Size, 
    GenderChoice
)
from products.v1.client.serializers import (
    ProductDetailSerializer, 
    PublicProductListSerializer, 
    ProductSettingsSerializer
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
            .filter(is_active=True)
        )

    def apply_filters(self, queryset):
        params = self.request.query_params

        text = params.get("search")
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
            queryset = queryset.filter(variants__size_id__in=size_ids, variants__is_active=True)

        color_ids = params.getlist("color_id") or params.getlist("color_ids")
        if len(color_ids) == 1 and "," in color_ids[0]:
            color_ids = [item.strip() for item in color_ids[0].split(",") if item.strip()]
        if color_ids:
            queryset = queryset.filter(variants__color_id__in=color_ids, variants__is_active=True)

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


class ProductListAPIView(ProductQuerysetMixin, generics.ListAPIView):
    serializer_class = PublicProductListSerializer
    pagination_class = CustomPagination

    def get_queryset(self):
        return self.apply_filters(self.get_base_queryset())

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        
        meta= {
            "total": self.paginator.page.paginator.count,
            "page": self.paginator.page.number,
            "page_size": 10,
        }

        return APIResponse.success(
            meta=meta, 
            data=serializer.data, 
            message="Products fetched successfully."
        )


class ProductDetailAPIView(ProductQuerysetMixin, generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return self.get_base_queryset()

    def retrieve(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object())
        return APIResponse.success(
            data=serializer.data, 
            message="Product fetched successfully."
        )


class ProductSettingsAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        data = {
            "categories": Category.objects.all().order_by("name"),
            "sizes": Size.objects.all().order_by("order", "name"),
            "colors": Color.objects.all().order_by("name"),
            "collections": Collection.objects.all().order_by("title"),
            "genders": [{"value": value, "label": label} for value, label in GenderChoice.choices],
        }
        serializer = ProductSettingsSerializer(data)
        return APIResponse.success(
            data=serializer.data, 
            message="Product settings fetched successfully."
        )


