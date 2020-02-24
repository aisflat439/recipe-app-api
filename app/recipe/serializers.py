from rest_framework import serializers

from core.models import Tag, Ingredient, Recipe


class TagSerializer(serializers.ModelSerializer):
    """Serializer for the tag object"""

    class Meta:
        model = Tag
        fields = ('id', 'name')
        read_only_fields = ('id', )


class IngredientSerializer(serializers.ModelSerializer):
    """Serializes the Ingredient obejct"""

    class Meta:
        model = Ingredient
        fields = ('id', 'name')
        read_only_fields = ('id', )


class RecipeSerializer(serializers.ModelSerializer):
    """Serializes the Recipe object"""
    ingredients = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Ingredient.objects.all()
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )

    class Meta:
        model = Recipe
        fields = (
            'id',
            'title',
            'time_minutes',
            'price',
            'link',
            'ingredients',
            'tags'
        )
        read_only_fields = ('id',)


class RecipeDetailSerializer(RecipeSerializer):
    """Serializes a Recipe detail object"""
    ingredients = IngredientSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)


class RecipeImageSerializer(serializers.ModelSerializer):
    """Serializer for uploading images to recipe"""

    class Meta:
        model = Recipe
        fields = ('id', 'image')
        read_only_fields = ('id',)
