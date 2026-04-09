from django.urls import include, path
from products.v1.client import views

product_user_urls = [
    path("add-to-cart/", views.AddToCartAPIView.as_view(), name="add-to-cart"),
    path("cart-item-list/", views.UserCartListAPIView.as_view(), name="cart-item-list"),
    path("add-to-favourite/", views.AddToFavouriteAPIView.as_view(), name="add-to-favourite"),
    path("favourite-item-list/", views.FavouriteListAPIView.as_view(), name="favourite-item-list"),
]

urlpatterns = [
    path("list/", views.ProductListAPIView.as_view(), name="product-list"),
    path("collection/list/", views.CollectionListAPIView.as_view(), name="collection-list"),
    path("settings/", views.ProductSettingsAPIView.as_view(), name="product-settings"),
    path("user/", include(product_user_urls)),
    path("<slug>/", views.ProductDetailsAPIView.as_view(), name="product-details"),
]
