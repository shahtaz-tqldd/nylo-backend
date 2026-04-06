from django.urls import include, path

from products.v1.admin import views as admin
from products.v1.client import views as client

client_urls = [
    path("list/", client.ProductListAPIView.as_view(), name="product-list"),
    path("settings/", client.ProductSettingsAPIView.as_view(), name="product-settings"),
    path("<uuid:id>/", client.ProductDetailAPIView.as_view(), name="product-detail"),
]


category_urls = [
    path("", admin.CategoryListCreateAPIView.as_view(), name="category-list-create"),
    path("<uuid:id>/", admin.CategoryDetailAPIView.as_view(), name="category-detail"),
]


size_urls = [
    path("", admin.SizeListCreateAPIView.as_view(), name="size-list-create"),
    path("<uuid:id>/", admin.SizeDetailAPIView.as_view(), name="size-detail"),
]


color_urls = [
    path("", admin.ColorListCreateAPIView.as_view(), name="color-list-create"),
    path("<uuid:id>/", admin.ColorDetailAPIView.as_view(), name="color-detail"),
]


collection_urls = [
    path("list/", admin.CollectionListAPIView.as_view(), name="collection-list"),
    path("", admin.CollectionListCreateAPIView.as_view(), name="collection-list-create"),
    path("<uuid:id>/", admin.CollectionDetailAPIView.as_view(), name="collection-detail"),
    path(
        "<uuid:id>/items/add-products/",
        admin.CollectionBulkAddProductsAPIView.as_view(),
        name="collection-add-products",
    ),
]


product_admin_urls = [
    path("list/", admin.AdminProductListAPIView.as_view(), name="admin-product-list"),
    path("<uuid:id>/", admin.AdminProductDetailAPIView.as_view(), name="admin-product-detail"),
    path("", admin.AdminProductListCreateAPIView.as_view(), name="admin-product-list-create"),
]

admin_urls = [
    path("", include((product_admin_urls, "product_admin"))),
    path("category/", include((category_urls, "category_admin"))),
    path("size/", include((size_urls, "size_admin"))),
    path("color/", include((color_urls, "color_admin"))),
    path("collection/", include((collection_urls, "collection_admin"))),
]

urlpatterns = [
    *client_urls,
    path("admin/", include((admin_urls))),
]
