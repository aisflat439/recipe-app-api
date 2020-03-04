from decimal import Decimal
import tempfile
import os

from PIL import Image

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe, Tag, Ingredient
from recipe.serializers import RecipeSerializer, RecipeDetailSerializer


RECIPES_URL = reverse('recipe:recipe-list')


def image_upload_url(recipe_id):
    """generates a url for recipe image upload"""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])


def detail_url(recipe_id):
    """Return recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def sample_ingredient(user, name='Kumquats'):
    """Create and return a sample recipe"""
    return Ingredient.objects.create(user=user, name=name)


def sample_tag(user, name='Main Course'):
    """Create and return a sample tag"""
    return Tag.objects.create(user=user, name=name)


def sample_recipe(user, **params):
    """Creates and returns a sample recipe"""
    defaults = {
        'title': 'Sample recipe',
        'time_minutes': 10,
        'price': 5.99
    }
    defaults.update(params)

    return Recipe.objects.create(user=user, **defaults)


class PublicRecipeApiTests(TestCase):
    """Tests the public recipe api, non authed user access"""

    def setUp(self):
        self.client = APIClient()

    def test_authorization_requried(self):
        """tests that auth is required"""
        response = self.client.get(RECIPES_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated API access"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "password123"
            )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """test retrieving a list of recipes"""
        sample_recipe(user=self.user)
        sample_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), len(serializer.data))
        self.assertEqual(response.data, serializer.data)

    def test_recipes_limited_to_user(self):
        """Test retriving recipes for user"""
        non_target_user = get_user_model().objects.create_user(
            "notme@user.com",
            "password123"
        )
        sample_recipe(user=non_target_user)
        sample_recipe(user=self.user)

        response = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data, serializer.data)

    def test_view_recipe_detail(self):
        """test viewing a recipe detail page"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        recipe.ingredients.add(sample_ingredient(user=self.user))

        url = detail_url(recipe.id)
        response = self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(response.data, serializer.data)

    def test_create_basic_recipe(self):
        """Test creating recipe"""
        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 8.75
        }

        response = self.client.post(RECIPES_URL, payload)
        recipe = Recipe.objects.get(id=response.data['id'])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(recipe, key))

    def test_create_recipe_with_tags(self):
        """Test creating a recipe with tags"""
        tag_one = sample_tag(user=self.user, name="Vegan")
        tag_two = sample_tag(user=self.user, name="Treats")

        payload = {
            'title': 'Chocolate cheesecake',
            'time_minutes': 30,
            'price': 8.75,
            'tags': [tag_one.id, tag_two.id],
        }

        response = self.client.post(RECIPES_URL, payload)
        recipe = Recipe.objects.get(id=response.data['id'])
        tags = recipe.tags.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(tags.count(), 2)
        self.assertIn(tag_one, tags)
        self.assertIn(tag_two, tags)

    def test_create_recipe_with_ingredients(self):
        """Creates ingredients, adds to a recipes, posts and validates"""
        ingredient_one = sample_ingredient(user=self.user, name="Cucumber")
        ingredient_two = sample_ingredient(user=self.user, name="Avocado")

        payload = {
            'title': 'Cucumber Salad',
            'time_minutes': 10,
            'price': 4.75,
            'ingredients': [ingredient_one.id, ingredient_two.id],
        }

        response = self.client.post(RECIPES_URL, payload)
        recipe = Recipe.objects.get(id=response.data['id'])
        ingredients = recipe.ingredients.all()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ingredients.count(), 2)
        self.assertIn(ingredient_one, ingredients)
        self.assertIn(ingredient_two, ingredients)

    def test_partial_update_recipe(self):
        """Test updating with patch"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        new_tag = sample_tag(user=self.user, name='Curry')

        payload = {
            'title': 'Chicken Curry',
            'tags': [new_tag.id]
        }

        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        tags = recipe.tags.all()

        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(len(tags), 1)
        self.assertIn(new_tag, tags)

    def test_full_update_recipe(self):
        """Test full update with a put"""
        recipe = sample_recipe(user=self.user)
        recipe.tags.add(sample_tag(user=self.user))
        payload = {
            'title': 'Yee derp',
            'time_minutes': 19,
            'price': 69.99
        }

        url = detail_url(recipe.id)
        self.client.put(url, payload)
        recipe.refresh_from_db()
        tags = recipe.tags.all()

        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.price, round(Decimal(69.99), 2))
        self.assertEqual(recipe.time_minutes, payload['time_minutes'])
        self.assertEqual(tags.count(), 0)


class RecipeImageUploadTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "password123"
            )
        self.client.force_authenticate(self.user)
        self.recipe = sample_recipe(user=self.user)

    def tearDown(self):
        self.recipe.image.delete()

    def test_uploading_an_image_to_recipe(self):
        """recipe creation"""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as ntf:
            img = Image.new('RGB', (10, 10))
            img.save(ntf, format='JPEG')
            ntf.seek(0)
            response = self.client.post(
                url,
                {'image': ntf},
                format='multipart'
            )
            self.recipe.refresh_from_db()

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('image', response.data)
            self.assertTrue(os.path.exists(self.recipe.image.path))

    def test_upload_image_bad_request(self):
        """uploading an invalid image fails"""
        url = image_upload_url(self.recipe.id)
        response = self.client.post(
            url,
            {'image': 'not-an-image'},
            format='multipart'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_recipes_by_tags(self):
        """returns recipes with specific tags another comment"""
        recipe_one = sample_recipe(user=self.user, title="soup")
        recipe_two = sample_recipe(user=self.user, title="salad")
        tag_one = sample_tag(user=self.user, name="Lunch")
        tag_two = sample_tag(user=self.user, name="Dinner")
        recipe_one.tags.add(tag_one)
        recipe_two.tags.add(tag_two)
        recipe_three = sample_recipe(user=self.user, title="tacos")

        response = self.client.get(
            RECIPES_URL,
            {'tags': f'{tag_one.id}, {tag_two.id}'}
        )
        serializer_one = RecipeSerializer(recipe_one)
        serializer_two = RecipeSerializer(recipe_two)
        serializer_three = RecipeSerializer(recipe_three)

        self.assertIn(serializer_one.data, response.data)
        self.assertIn(serializer_two.data, response.data)
        self.assertNotIn(serializer_three.data, response.data)

    def test_filter_recipes_by_ingredients(self):
        """returns recipes with specific ingredients random comment"""
        recipe_one = sample_recipe(user=self.user, title="soup")
        recipe_two = sample_recipe(user=self.user, title="salad")
        ingredient_one = sample_ingredient(user=self.user, name="chicken")
        ingredient_two = sample_ingredient(user=self.user, name="fish")
        recipe_one.ingredients.add(ingredient_one)
        recipe_two.ingredients.add(ingredient_two)
        recipe_three = sample_recipe(user=self.user, title="tacos")

        response = self.client.get(
            RECIPES_URL,
            {'ingredients': f'{ingredient_one.id}, {ingredient_two.id}'}
        )
        serializer_one = RecipeSerializer(recipe_one)
        serializer_two = RecipeSerializer(recipe_two)
        serializer_three = RecipeSerializer(recipe_three)

        self.assertIn(serializer_one.data, response.data)
        self.assertIn(serializer_two.data, response.data)
        self.assertNotIn(serializer_three.data, response.data)
