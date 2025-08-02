# nutrition-backend/routers/__init__.py
"""
Router package for Nutrition App API endpoints
"""

# Import all routers to make them available
from . import recipes
from . import ratings
from . import nutrition
from . import grocery
from . import nutritionCoach
from . import socialMediaImport
from . import recipeScaling

__all__ = [
    'recipes',
    'ratings',
    'nutrition',
    'grocery',
    'nutritionCoach',
    'socialMediaImport',
    'recipeScaling'
]