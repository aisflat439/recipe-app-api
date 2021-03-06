from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe

from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


class PublicIngredientsApiTest(TestCase):
    """Test the publicly available ingredients api"""
    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """Test that login is required to access ingredients"""
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIngredientsApiTest(TestCase):
    """Test the private ingredients can be retrieved by auth'd user"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "password123"
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients_list(self):
        """Retrieving the list of ingredients"""
        Ingredient.objects.create(
            user=self.user,
            name="Cucumber",
        )
        Ingredient.objects.create(
            user=self.user,
            name="Kale",
        )

        response = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_ingredietnts_are_limited_to_user(self):
        """"Test that ingredients are limited to users ingredients"""
        non_target_user = get_user_model().objects.create_user(
            "notme@user.com",
            "password123"
        )
        Ingredient.objects.create(
            user=non_target_user,
            name="Banana",
        )
        ingredient = Ingredient.objects.create(
            user=self.user,
            name="Kale",
        )
        response = self.client.get(INGREDIENTS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ingredient.name)

    def test_create_ingredient_successful(self):
        """Adding a valid ingredient succeeds"""
        payload = {'name': 'Cucumber'}
        self.client.post(INGREDIENTS_URL, payload)

        exists = Ingredient.objects.filter(
            user=self.user,
            name=payload['name']
        ).exists()
        self.assertTrue(exists)

    def test_create_ingredient_invalid(self):
        """Adding an invalid ingredient fails"""
        payload = {'name': ''}
        response = self.client.post(INGREDIENTS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_only_ingredients_assigned_to_recipes(self):
        """return only the ingredients that are actively assigned a recipe"""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Beef')
        ingredient2 = Ingredient.objects.create(user=self.user, name='Chicken')
        recipe = Recipe.objects.create(
            title='tacos',
            time_minutes=20,
            price=5.55,
            user=self.user
        )
        recipe.ingredients.add(ingredient1)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})
        serializer1 = IngredientSerializer(ingredient1)
        serializer2 = IngredientSerializer(ingredient2)

        self.assertIn(serializer1.data, response.data)
        self.assertNotIn(serializer2.data, response.data)

    def test_retrieve_ingredients_assigned_unique(self):
        """test filtering ingredients assigned returns unique items"""
        ingredient = Ingredient.objects.create(user=self.user, name='Beef')
        Ingredient.objects.create(user=self.user, name='Chicken')
        recipe1 = Recipe.objects.create(
            title='tacos',
            time_minutes=20,
            price=5.55,
            user=self.user
        )
        recipe1.ingredients.add(ingredient)
        recipe2 = Recipe.objects.create(
            title='pancakes',
            time_minutes=10,
            price=2.55,
            user=self.user
        )
        recipe2.ingredients.add(ingredient)

        response = self.client.get(INGREDIENTS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
