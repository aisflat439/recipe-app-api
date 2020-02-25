from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe

from recipe.serializers import TagSerializer

TAGS_URL = reverse('recipe:tag-list')


class PublicTagsApiTests(TestCase):
    """Test publicly available tags api"""

    def setUp(self):
        self.client = APIClient()

    def test_login_required(self):
        """test that login is required for getting tags"""
        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Test privately available tags api"""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            "test@test.com",
            "password123",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """allow a logged in user to retrieve tags"""
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Paleo')

        response = self.client.get(TAGS_URL)
        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_tags_limited_to_user(self):
        """test that tags returned are for the user"""
        non_target_user = get_user_model().objects.create_user(
            "baduser@test.com",
            "password123",
        )
        tag = Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=non_target_user, name='Desert')

        response = self.client.get(TAGS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], tag.name)

    def test_create_tag_successful(self):
        """test creating a new tag"""
        payload = {
            'name': 'Test Tag'
        }
        self.client.post(TAGS_URL, payload)

        exists = Tag.objects.filter(
            user=self.user,
            name=payload['name']
            ).exists()
        self.assertTrue(exists)

    def test_create_invalid_tag_fails(self):
        """Creating new tag with invalid payload fails"""
        """test creating a new tag"""
        payload = {
            'name': ''
        }
        response = self.client.post(TAGS_URL, payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_only_tags_assigned_to_recipes(self):
        """return only the tags that are actively assigned to a recipe"""
        tag_one = Tag.objects.create(user=self.user, name='Vegan')
        tag_two = Tag.objects.create(user=self.user, name='Paleo')
        recipe = Recipe.objects.create(
            title='tacos',
            time_minutes=20,
            price=5.55,
            user=self.user
        )
        recipe.tags.add(tag_one)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})
        serializer_one = TagSerializer(tag_one)
        serializer_two = TagSerializer(tag_two)

        self.assertIn(serializer_one.data, response.data)
        self.assertNotIn(serializer_two.data, response.data)

    def test_retrieve_tags_assigned_unique(self):
        """test filtering tags assigned returns unique items"""
        tag = Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Paleo')
        recipe_one = Recipe.objects.create(
            title='tacos',
            time_minutes=20,
            price=5.55,
            user=self.user
        )
        recipe_one.tags.add(tag)
        recipe_two = Recipe.objects.create(
            title='pancakes',
            time_minutes=10,
            price=2.55,
            user=self.user
        )
        recipe_two.tags.add(tag)

        response = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(response.data), 1)
