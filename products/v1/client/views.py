from django.db import transaction
from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated

from app.base.pagination import CustomPagination
from app.utils.response import APIResponse
from products.models import (
    Category,
    Collection,
    CollectionItem,
    Color,
    GenderChoice,
    OfferProductItem,
    Product,
    SignatureProductItem,
    Size,
    UserCartItem,
    UserFavouriteItem,
)
from products.v1.client.serializers import (
    AddToCartSerializer,
    AddToFavouriteSerializer,
    FeaturedProductsSerializer,
    PublicCollectionListSerializer,
    ProductDetailSerializer,
    ProductSettingsSerializer,
    PublicProductListSerializer,
    UserCartItemSerializer,
    UserFavouriteItemSerializer,
)


class PublicResponseMixin:
    permission_classes = [AllowAny]
    lookup_field = "id"
    success_list_message = "Products fetched successfully."
    success_detail_message = "Product fetched successfully."

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
        serializer = self.get_serializer(self.get_object())
        return APIResponse.success(data=serializer.data, message=self.success_detail_message)


class ProductQuerysetMixin:
    pagination_class = CustomPagination

    def get_base_queryset(self):
        return (
            Product.objects.select_related("category")
            .prefetch_related(
                Prefetch("variants", to_attr="prefetched_variants"),
                Prefetch(
                    "collectionitem_set",
                    queryset=CollectionItem.objects.select_related("collection"),
                    to_attr="prefetched_collection_items",
                ),
            )
            .filter(is_active=True)
        )

    def apply_filters(self, queryset):
        params = self.request.query_params

        text = params.get("search") or params.get("text")
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

    def get_queryset(self):
        return self.apply_filters(self.get_base_queryset())


class ProductListAPIView(ProductQuerysetMixin, PublicResponseMixin, generics.ListAPIView):
    serializer_class = PublicProductListSerializer


class CollectionListAPIView(ProductQuerysetMixin, PublicResponseMixin, generics.ListAPIView):
    serializer_class = PublicCollectionListSerializer
    success_list_message = "Collections fetched successfully."

    def get_queryset(self):
        queryset = Collection.objects.annotate(
            total_products=Count("items", filter=Q(items__product__is_active=True), distinct=True)
        )

        text = (self.request.query_params.get("search") or self.request.query_params.get("text") or "").strip()
        if text:
            queryset = queryset.filter(
                Q(title__icontains=text)
                | Q(subtitle__icontains=text)
                | Q(type__icontains=text)
                | Q(description__icontains=text)
                | Q(slug__icontains=text)
            )

        return queryset.order_by("title")


class ProductDetailsAPIView(ProductQuerysetMixin, PublicResponseMixin, generics.RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return self.get_base_queryset()


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
        return APIResponse.success(data=serializer.data, message="Product settings fetched successfully.")


class FeaturedProductsAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        signature_items = SignatureProductItem.objects.select_related("product__category").prefetch_related(
            Prefetch("product__variants", to_attr="prefetched_variants")
        ).filter(product__is_active=True)

        offer_items = OfferProductItem.objects.select_related("product__category").prefetch_related(
            Prefetch("product__variants", to_attr="prefetched_variants")
        ).filter(
            product__is_active=True
        ).filter(
            Q(offer_ends_at__isnull=True) | Q(offer_ends_at__gte=timezone.now())
        )

        best_selling_products = (
            Product.objects.select_related("category")
            .prefetch_related(Prefetch("variants", to_attr="prefetched_variants"))
            .filter(is_active=True)
            .annotate(total_sold=Coalesce(Sum("order_items__quantity"), 0))
            .filter(total_sold__gt=0)
            .order_by("-total_sold", "-created_at")[:5]
        )

        serializer = FeaturedProductsSerializer(
            {
                "signature_items": signature_items,
                "offer_items": offer_items,
                "best_selling_products": best_selling_products,
            }
        )
        return APIResponse.success(data=serializer.data, message="Featured products fetched successfully.")


class AuthenticatedUserAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    unavailable_message = "This endpoint is not available yet."

    def not_available(self):
        return APIResponse.error(message=self.unavailable_message, status=status.HTTP_501_NOT_IMPLEMENTED)


class AddToCartAPIView(AuthenticatedUserAPIView):
    def post(self, request, *args, **kwargs):
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(errors=serializer.errors, message="Invalid cart payload.")

        product = serializer.validated_data["product"]
        variant = serializer.validated_data["variant"]
        action = serializer.validated_data["action"]

        if action == AddToCartSerializer.ACTION_ADD and variant.stock < 1:
            return APIResponse.error(
                message="This variant is out of stock.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            cart_item = (
                UserCartItem.objects.select_for_update()
                .filter(user=request.user, product=product, variant=variant)
                .first()
            )

            if action == AddToCartSerializer.ACTION_ADD:
                next_quantity = (cart_item.quantity + 1) if cart_item else 1
                if next_quantity > variant.stock:
                    return APIResponse.error(
                        message="Requested quantity exceeds available stock.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if cart_item:
                    cart_item.quantity = next_quantity
                    cart_item.save(update_fields=["quantity", "updated_at"])
                else:
                    cart_item = UserCartItem.objects.create(
                        user=request.user,
                        product=product,
                        variant=variant,
                        quantity=1,
                    )

                output = UserCartItemSerializer(cart_item)
                return APIResponse.success(data=output.data, message="Cart updated successfully.")

            if cart_item is None:
                return APIResponse.error(
                    message="Cart item not found.",
                    status=status.HTTP_404_NOT_FOUND,
                )

            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save(update_fields=["quantity", "updated_at"])
                output = UserCartItemSerializer(cart_item)
                return APIResponse.success(data=output.data, message="Cart updated successfully.")

            cart_item.delete()
            return APIResponse.success(message="Item removed from cart successfully.")


class UserCartListAPIView(AuthenticatedUserAPIView):
    pagination_class = CustomPagination

    def get(self, request, *args, **kwargs):
        queryset = (
            UserCartItem.objects.filter(user=request.user)
            .select_related("product__category", "variant__size", "variant__color")
            .order_by("-created_at")
        )
        total_items = queryset.aggregate(total_items=Sum("quantity"))["total_items"] or 0

        page = self.paginate_queryset(queryset)
        serializer = UserCartItemSerializer(page if page is not None else queryset, many=True)

        meta = {"total_items": total_items}
        if page is not None:
            meta.update(
                {
                    "total": self.paginator.page.paginator.count,
                    "page": self.paginator.page.number,
                    "page_size": self.paginator.page.paginator.per_page,
                }
            )

        return APIResponse.success(
            data=serializer.data,
            meta=meta,
            message="Cart items fetched successfully.",
        )


class AddToFavouriteAPIView(AuthenticatedUserAPIView):
    def post(self, request, *args, **kwargs):
        serializer = AddToFavouriteSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.error(errors=serializer.errors, message="Invalid favourite payload.")

        product = serializer.validated_data["product"]
        action = serializer.validated_data["action"]

        favourite_item = UserFavouriteItem.objects.filter(user=request.user, product=product).first()

        if action == AddToFavouriteSerializer.ACTION_ADD:
            if favourite_item is None:
                favourite_item = UserFavouriteItem.objects.create(user=request.user, product=product)
            output = UserFavouriteItemSerializer(favourite_item)
            return APIResponse.success(data=output.data, message="Favourite updated successfully.")

        if favourite_item is None:
            return APIResponse.error(
                message="Favourite item not found.",
                status=status.HTTP_404_NOT_FOUND,
            )

        favourite_item.delete()
        return APIResponse.success(message="Item removed from favourites successfully.")


class FavouriteListAPIView(AuthenticatedUserAPIView):
    def get(self, request, *args, **kwargs):
        queryset = (
            UserFavouriteItem.objects.filter(user=request.user)
            .select_related("product__category")
            .order_by("-created_at")
        )
        serializer = UserFavouriteItemSerializer(queryset, many=True)
        return APIResponse.success(data=serializer.data, message="Favourite items fetched successfully.")
