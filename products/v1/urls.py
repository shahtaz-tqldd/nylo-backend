from django.urls import include, path

from products.v1.views import admin, client


client_urls = [
    path("list/", client.ProductListAPIView.as_view(), name="product-list"),
    path("settings/", admin.ProductSettingsAPIView.as_view(), name="product-settings"),
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
    path("", admin.CollectionListCreateAPIView.as_view(), name="collection-list-create"),
    path("<uuid:id>/", admin.CollectionDetailAPIView.as_view(), name="collection-detail"),
    path(
        "<uuid:id>/items/add-products/",
        admin.CollectionBulkAddProductsAPIView.as_view(),
        name="collection-add-products",
    ),
]


product_admin_urls = [
    path("", admin.AdminProductListCreateAPIView.as_view(), name="admin-product-list-create"),
    path("<uuid:id>/", admin.AdminProductDetailAPIView.as_view(), name="admin-product-detail"),
]


urlpatterns = [
    *client_urls,
    path("admin/category/", include((category_urls, "category_admin"))),
    path("admin/size/", include((size_urls, "size_admin"))),
    path("admin/color/", include((color_urls, "color_admin"))),
    path("admin/collection/", include((collection_urls, "collection_admin"))),
    path("admin/product/", include((product_admin_urls, "product_admin"))),
]
