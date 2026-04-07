from django.urls import include, path

from products.v1.admin import views

category_urls = [
    path("create/", views.CategoryCreateAPIView.as_view(), name="category-create"),
    path("update/<uuid:id>/", views.CategoryUpdateAPIView.as_view(), name="category-update"),
    path("delete/<uuid:id>/", views.CategoryDeleteAPIView.as_view(), name="category-delete"),
]

size_urls = [
    path("create/", views.SizeCreateAPIView.as_view(), name="size-create"),
    path("update/<uuid:id>/", views.SizeUpdateAPIView.as_view(), name="size-update"),
    path("delete/<uuid:id>/", views.SizeDeleteAPIView.as_view(), name="size-delete"),
]

color_urls = [
    path("create/", views.ColorCreateAPIView.as_view(), name="color-create"),
    path("update/<uuid:id>/", views.ColorUpdateAPIView.as_view(), name="color-update"),
    path("delete/<uuid:id>/", views.ColorDeleteAPIView.as_view(), name="color-delete"),
]

collection_urls = [
    path("create/", views.CollectionCreateAPIView.as_view(), name="collection-create"),
    path("list/", views.CollectionListAPIView.as_view(), name="collection-list"),
    path("<uuid:id>/", views.CollectionDetailsAPIView.as_view(), name="collection-details"),
    path("update/<uuid:id>/", views.CollectionUpdateAPIView.as_view(), name="collection-update"),
    path("delete/<uuid:id>/", views.CollectionDeleteAPIView.as_view(), name="collection-delete"),
]

product_urls = [
    path("create/", views.ProductCreateAPIView.as_view(), name="product-create"),
    path("list/", views.ProductListAPIView.as_view(), name="product-list"),
    path("<uuid:id>/", views.ProductDetailsAPIView.as_view(), name="product-details"),
    path("update/<uuid:id>/", views.ProductUpdateAPIView.as_view(), name="product-update"),
    path("delete/<uuid:id>/", views.ProductDeleteAPIView.as_view(), name="product-delete"),
]

urlpatterns = [
    path("category/", include((category_urls, "category_admin"))),
    path("size/", include((size_urls, "size_admin"))),
    path("color/", include((color_urls, "color_admin"))),
    path("collection/", include((collection_urls, "collection_admin"))),
    path("", include((product_urls, "product_admin"))),
    path("settings/", views.ProductSettingsAPIView.as_view(), name="product-settings"),
]
