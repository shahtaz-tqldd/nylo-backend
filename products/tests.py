from rest_framework import status
from rest_framework.test import APITestCase

from auth.models import User
from products.models import Category, Color, GenderChoice, Product, ProductVariant, Size, UserCartItem


class AddToCartAPIViewTests(APITestCase):
    url = "/api/v1/products/user/add-to-cart/"

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="password123",
            first_name="Cart",
            last_name="User",
        )
        self.client.force_authenticate(self.user)

        self.category = Category.objects.create(name="Shoes")
        self.size = Size.objects.create(name="42", order=1)
        self.color = Color.objects.create(name="Black", color_code="#000000")
        self.product = Product.objects.create(
            title="Runner",
            category=self.category,
            gender=GenderChoice.MEN,
            price="99.99",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size=self.size,
            color=self.color,
            stock=5,
            is_active=True,
        )

    def test_add_sets_quantity_and_updates_existing_cart_item(self):
        response = self.client.post(
            self.url,
            {
                "action": "add",
                "product_id": str(self.product.id),
                "variant_id": str(self.variant.id),
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item = UserCartItem.objects.get(user=self.user, product=self.product, variant=self.variant)
        self.assertEqual(cart_item.quantity, 3)

        response = self.client.post(
            self.url,
            {
                "action": "add",
                "product_id": str(self.product.id),
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)
        self.assertEqual(UserCartItem.objects.filter(user=self.user, product=self.product, variant=self.variant).count(), 1)

    def test_add_rejects_quantity_above_available_stock(self):
        response = self.client.post(
            self.url,
            {
                "action": "add",
                "product_id": str(self.product.id),
                "variant_id": str(self.variant.id),
                "quantity": 6,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Requested quantity exceeds available stock.")
        self.assertFalse(UserCartItem.objects.filter(user=self.user, product=self.product, variant=self.variant).exists())

    def test_remove_uses_requested_quantity_and_deletes_when_empty(self):
        cart_item = UserCartItem.objects.create(
            user=self.user,
            product=self.product,
            variant=self.variant,
            quantity=5,
        )

        response = self.client.post(
            self.url,
            {
                "action": "remove",
                "product_id": str(self.product.id),
                "variant_id": str(self.variant.id),
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 3)

        response = self.client.post(
            self.url,
            {
                "action": "remove",
                "product_id": str(self.product.id),
                "variant_id": str(self.variant.id),
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Item removed from cart successfully.")
        self.assertFalse(UserCartItem.objects.filter(id=cart_item.id).exists())
