# nutrition-backend/routers/recipes.py - YOUR FEATURES + ALL P0/P1 SECURITY FIXES
import asyncio
import json
import re
from fractions import Fraction
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field, validator
import logging
from datetime import datetime

# Enhanced imports with security and performance
from config import config
from security import sanitize_string, validate_user_id, sanitize_recipe_data, ValidationError
from exceptions import (
    DatabaseError, ExternalServiceError, BusinessLogicError,
    DatabaseErrorContext, ExternalServiceErrorContext, safe_operation
)
from database_compatibility import supabase, init_supabase_compatibility
from services.enhanced_openai_service import enhanced_openai_service as openai_service

# Import your existing models (with enhanced validation)
from models.recipeModels import RecipeRequest, SingleRecipeRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# Load ingredient prices securely
ingredient_prices = {}
try:
    # Use relative path and handle missing file gracefully
    import os

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    prices_file = os.path.join(base_dir, "Data", "ingredient_prices.json")

    if os.path.exists(prices_file):
        with open(prices_file) as f:
            ingredient_prices = json.load(f)
        logger.info(f"✅ Loaded {len(ingredient_prices)} ingredient prices")
    else:
        logger.warning("⚠️ Ingredient prices file not found, using defaults")
except Exception as e:
    logger.warning(f"⚠️ Could not load ingredient prices: {e}")


# Enhanced Pydantic Models with Security Validation

class AdvancedRecipeRequest(BaseModel):
    """Enhanced recipe request with comprehensive validation"""

    title: str = Field(..., min_length=1, max_length=200, description="Recipe title")
    user_id: str = Field(..., description="User UUID")
    num_recipes: int = Field(3, ge=1, le=10, description="Number of recipes to generate")

    # Your advanced preference fields with validation
    budget: Optional[float] = Field(None, ge=1.0, le=1000.0)
    allergies: Optional[str] = Field(None, max_length=500)
    diet: Optional[str] = Field(None, max_length=100)
    dietary_restrictions: Optional[Dict[str, bool]] = Field(default_factory=dict)
    macro_targets: Optional[Dict[str, Any]] = Field(default_factory=dict)
    cuisine_preferences: Optional[Dict[str, List[str]]] = Field(default_factory=dict)
    cooking_constraints: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator('title')
    def validate_title(cls, v):
        """Validate and sanitize recipe title"""
        return sanitize_string(v, max_length=200, field_name="recipe title")

    @validator('user_id')
    def validate_user_id_format(cls, v):
        """Validate user ID format"""
        return validate_user_id(v)

    @validator('allergies')
    def validate_allergies(cls, v):
        """Validate allergies field"""
        if v is not None:
            return sanitize_string(v, max_length=500, field_name="allergies")
        return v

    @validator('diet')
    def validate_diet(cls, v):
        """Validate diet field"""
        if v is not None:
            return sanitize_string(v, max_length=100, field_name="diet")
        return v

    @validator('dietary_restrictions')
    def validate_dietary_restrictions(cls, v):
        """Validate dietary restrictions"""
        if v is None:
            return {}

        allowed_restrictions = [
            'vegetarian', 'vegan', 'glutenFree', 'dairyFree', 'nutFree',
            'soyFree', 'eggFree', 'shellfishFree', 'lowSodium', 'lowSugar',
            'keto', 'paleo', 'mediterranean', 'lowCarb', 'highProtein'
        ]

        validated = {}
        for key, value in v.items():
            if key in allowed_restrictions:
                validated[key] = bool(value)

        return validated


class UserPreferenceFeedback(BaseModel):
    """Model for user preference feedback"""

    rating: int = Field(..., ge=1, le=5, description="Recipe rating 1-5")
    cuisine: Optional[str] = Field(None, max_length=100)
    feedback_reason: Optional[str] = Field(None, max_length=500)
    recipe_id: Optional[str] = None

    @validator('cuisine')
    def validate_cuisine(cls, v):
        if v is not None:
            return sanitize_string(v, max_length=100, field_name="cuisine")
        return v

    @validator('feedback_reason')
    def validate_feedback_reason(cls, v):
        if v is not None:
            return sanitize_string(v, max_length=500, field_name="feedback reason")
        return v


# Enhanced utility functions with security
async def get_advanced_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get comprehensive user preferences with enhanced error handling"""

    # Validate user ID first
    validated_user_id = validate_user_id(user_id)

    try:
        async with DatabaseErrorContext("get_user_preferences", "user_preferences"):
            # Ensure database is initialized
            if not supabase:
                await init_supabase_compatibility()

            pref_resp = await supabase.table("user_preferences") \
                .select("*") \
                .eq("user_id", validated_user_id) \
                .limit(1) \
                .execute()

            if pref_resp.data and len(pref_resp.data) > 0:
                prefs = pref_resp.data[0]

                # Parse with enhanced validation
                result = {
                    'budget': _safe_float_parse(prefs.get("budget", "20.0"), default=20.0, min_val=1.0, max_val=1000.0),
                    'allergies': sanitize_string(prefs.get("allergies", ""), max_length=500,
                                                 field_name="allergies") if prefs.get("allergies") else "",
                    'diet': sanitize_string(prefs.get("diet", ""), max_length=100, field_name="diet") if prefs.get(
                        "diet") else "",
                    'dietary_restrictions': _validate_dict_field(prefs.get("dietary_restrictions", {})),
                    'macro_targets': _validate_dict_field(prefs.get("macro_targets", {})),
                    'cuisine_preferences': _validate_cuisine_preferences(prefs.get("cuisine_preferences", {})),
                    'cooking_constraints': _validate_cooking_constraints(prefs.get("cooking_constraints", {}))
                }

                logger.debug(f"Loaded preferences for user {validated_user_id[:8]}...")
                return result
            else:
                return get_default_preferences()

    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Error loading preferences for user {validated_user_id[:8]}...: {e}")
        return get_default_preferences()


def get_default_preferences() -> Dict[str, Any]:
    """Return secure default preferences"""
    return {
        'budget': 20.0,
        'allergies': "",
        'diet': "",
        'dietary_restrictions': {},
        'macro_targets': {},
        'cuisine_preferences': {"preferred": [], "disliked": []},
        'cooking_constraints': {}
    }


def _safe_float_parse(value: Any, default: float, min_val: float = None, max_val: float = None) -> float:
    """Safely parse float with bounds checking"""
    try:
        if isinstance(value, str):
            # Remove currency symbols and split on dash
            cleaned = value.replace('$', '').split('-')[0]
            result = float(cleaned)
        else:
            result = float(value)

        if min_val is not None and result < min_val:
            return min_val
        if max_val is not None and result > max_val:
            return max_val

        return result
    except (ValueError, TypeError, AttributeError):
        return default


def _validate_dict_field(value: Any) -> Dict[str, Any]:
    """Validate dictionary fields"""
    if isinstance(value, dict):
        return value
    return {}


def _validate_cuisine_preferences(value: Any) -> Dict[str, List[str]]:
    """Validate cuisine preferences with sanitization"""
    if not isinstance(value, dict):
        return {"preferred": [], "disliked": []}

    result = {"preferred": [], "disliked": []}

    for key in ["preferred", "disliked"]:
        if key in value and isinstance(value[key], list):
            sanitized_cuisines = []
            for cuisine in value[key]:
                if isinstance(cuisine, str):
                    try:
                        clean_cuisine = sanitize_string(cuisine, max_length=100, field_name="cuisine")
                        sanitized_cuisines.append(clean_cuisine)
                    except:
                        continue
            result[key] = sanitized_cuisines[:10]  # Limit to 10 cuisines

    return result


def _validate_cooking_constraints(value: Any) -> Dict[str, Any]:
    """Validate cooking constraints with bounds checking"""
    if not isinstance(value, dict):
        return {}

    validated = {}

    # Time constraints (1 minute to 12 hours)
    for time_field in ['maxCookTime', 'maxPrepTime']:
        if time_field in value:
            try:
                time_val = int(value[time_field])
                if 1 <= time_val <= 720:
                    validated[time_field] = time_val
            except (ValueError, TypeError):
                continue

    # Ingredient count (3 to 50)
    if 'maxIngredients' in value:
        try:
            ing_val = int(value['maxIngredients'])
            if 3 <= ing_val <= 50:
                validated['maxIngredients'] = ing_val
        except (ValueError, TypeError):
            pass

    # Difficulty level
    if 'difficultyLevel' in value:
        if value['difficultyLevel'] in ['beginner', 'intermediate', 'advanced']:
            validated['difficultyLevel'] = value['difficultyLevel']

    # Kitchen equipment
    if 'kitchenEquipment' in value and isinstance(value['kitchenEquipment'], list):
        equipment = []
        for eq in value['kitchenEquipment']:
            if isinstance(eq, str):
                try:
                    clean_eq = sanitize_string(eq, max_length=100, field_name="equipment")
                    equipment.append(clean_eq)
                except:
                    continue
        validated['kitchenEquipment'] = equipment[:20]  # Limit to 20 items

    return validated


async def build_advanced_prompt(title: str, user_prefs: Dict[str, Any], num_recipes: int = 3) -> str:
    """Build enhanced prompt with security validation"""

    # Sanitize title
    safe_title = sanitize_string(title, max_length=200, field_name="recipe title")

    # Validate number of recipes
    if not 1 <= num_recipes <= 10:
        raise ValidationError("Number of recipes must be between 1 and 10")

    # Build prompt (keeping your existing logic but with validation)
    prompt_parts = [
        "You are a world class chef that understands flavor, texture, and different cuisines who is exceptional at curating recipes with budget, calories, different cuisines, and macro nutrients.",
        "",
        f'Generate exactly {num_recipes} distinct recipes for: "{safe_title}".',
        "",
        "CONSTRAINTS:",
        f"- Budget: ${user_prefs['budget']:.2f} per recipe"
    ]

    # Add preferences (with sanitized values)
    if user_prefs.get('allergies'):
        prompt_parts.append(f"- Allergies/Avoid: {user_prefs['allergies']}")

    if user_prefs.get('diet'):
        prompt_parts.append(f"- Primary Diet: {user_prefs['diet']}")

    # Dietary restrictions
    dietary_restrictions = user_prefs.get('dietary_restrictions', {})
    active_restrictions = [key.replace('_', ' ').title() for key, value in dietary_restrictions.items() if value]
    if active_restrictions:
        prompt_parts.append(f"- Dietary Restrictions: {', '.join(active_restrictions)}")

    # Macro targets
    macro_targets = user_prefs.get('macro_targets', {})
    if macro_targets.get('enableTargets'):
        prompt_parts.append("- MACRO TARGETS:")
        for macro in ['calories', 'protein', 'carbs', 'fat', 'fiber']:
            if macro_targets.get(macro):
                prompt_parts.append(f"  • Target {macro.title()}: {macro_targets[macro]}")

    # Cuisine preferences
    cuisine_prefs = user_prefs.get('cuisine_preferences', {})
    if cuisine_prefs.get('preferred'):
        prompt_parts.append(f"- PREFERRED Cuisines: {', '.join(cuisine_prefs['preferred'])}")
    if cuisine_prefs.get('disliked'):
        prompt_parts.append(f"- AVOID Cuisines: {', '.join(cuisine_prefs['disliked'])}")

    # Cooking constraints
    cooking_constraints = user_prefs.get('cooking_constraints', {})
    constraint_mappings = {
        'maxCookTime': 'Max Cooking Time: {} minutes',
        'maxPrepTime': 'Max Prep Time: {} minutes',
        'maxIngredients': 'Max Ingredients: {} items'
    }

    for key, template in constraint_mappings.items():
        if cooking_constraints.get(key):
            prompt_parts.append(f"- {template.format(cooking_constraints[key])}")

    if cooking_constraints.get('difficultyLevel'):
        difficulty_map = {
            'beginner': 'Beginner (simple techniques)',
            'intermediate': 'Intermediate (moderate techniques)',
            'advanced': 'Advanced (complex techniques)'
        }
        prompt_parts.append(f"- Difficulty Level: {difficulty_map.get(cooking_constraints['difficultyLevel'])}")

    if cooking_constraints.get('kitchenEquipment'):
        prompt_parts.append(f"- Available Equipment: {', '.join(cooking_constraints['kitchenEquipment'])}")

    # Add format instructions (keeping your existing format)
    format_instructions = [
        "",
        "Format each recipe EXACTLY like this:",
        "",
        "RECIPE 1: [Recipe Name]",
        "",
        "Ingredients:",
        "- 1 cup ingredient1",
        "- 2 tbsp ingredient2",
        "- 3 pieces ingredient3",
        "",
        "Directions:",
        "1. First step",
        "2. Second step",
        "3. Third step",
        "",
        "Nutrition Facts:",
        "- Calories: 450",
        "- Protein: 25g",
        "- Carbs: 35g",
        "- Fat: 15g",
        "- Fiber: 5g",
        "",
        "Tags: tag1, tag2, tag3",
        "Cuisine: Italian",
        "Diet: Balanced",
        "Prep Time: 15 minutes",
        "Cook Time: 30 minutes",
        "Difficulty: Intermediate",
        "Cost Estimate: $8.50",
        "",
        "---",
        "",
        f"RECIPE 2: [Recipe Name]",
        "[Same format as above]",
        "",
        "---",
        "",
        f"RECIPE 3: [Recipe Name]",
        "[Same format as above]" if num_recipes >= 3 else "",
        "",
        "IMPORTANT NOTES:",
        "- Ensure recipes meet ALL specified constraints and targets",
        "- If macro targets are specified, prioritize hitting those numbers",
        "- Respect all dietary restrictions absolutely",
        "- Stay within the specified time and difficulty constraints",
        "- Use only available kitchen equipment",
        "- Make each recipe unique and flavorful"
    ]

    prompt_parts.extend(format_instructions)

    return "\n".join(prompt_parts).strip()


def validate_recipe_against_preferences(recipe_data: Dict[str, Any], user_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Validate recipe against preferences (keeping your existing logic with security enhancements)"""
    validation_score = 100
    issues = []

    # Safely convert recipe data to lowercase string for checking
    try:
        recipe_text = json.dumps(recipe_data, default=str).lower()
    except:
        recipe_text = str(recipe_data).lower()

    # Check dietary restrictions
    dietary_restrictions = user_prefs.get('dietary_restrictions', {})

    restriction_checks = {
        'glutenFree': ['wheat', 'flour', 'bread', 'pasta', 'gluten'],
        'dairyFree': ['milk', 'cheese', 'butter', 'cream', 'dairy'],
        'nutFree': ['nuts', 'peanut', 'almond', 'walnut', 'cashew'],
        'vegetarian': ['meat', 'chicken', 'beef', 'pork', 'fish', 'seafood'],
        'vegan': ['meat', 'chicken', 'beef', 'pork', 'fish', 'milk', 'cheese', 'butter', 'egg', 'honey']
    }

    for restriction, forbidden_items in restriction_checks.items():
        if dietary_restrictions.get(restriction):
            for item in forbidden_items:
                if item in recipe_text:
                    validation_score -= 20
                    issues.append(f"Contains {item} (violates {restriction})")
                    break  # Only penalize once per restriction

    # Check cuisine preferences
    cuisine_prefs = user_prefs.get('cuisine_preferences', {})
    recipe_cuisine = recipe_data.get('cuisine', '').lower()

    if cuisine_prefs.get('disliked'):
        disliked_lower = [c.lower() for c in cuisine_prefs['disliked']]
        if recipe_cuisine in disliked_lower:
            validation_score -= 15
            issues.append(f"Uses disliked cuisine: {recipe_cuisine}")

    if cuisine_prefs.get('preferred'):
        preferred_lower = [c.lower() for c in cuisine_prefs['preferred']]
        if recipe_cuisine in preferred_lower:
            validation_score += 10

    # Check cooking constraints
    cooking_constraints = user_prefs.get('cooking_constraints', {})

    if cooking_constraints.get('maxIngredients'):
        ingredient_count = len(recipe_data.get('ingredients', []))
        max_ingredients = int(cooking_constraints['maxIngredients'])
        if ingredient_count > max_ingredients:
            validation_score -= 10
            issues.append(f"Too many ingredients: {ingredient_count} > {max_ingredients}")

    return {
        'score': max(0, validation_score),
        'issues': issues,
        'passes_validation': validation_score >= 70
    }


def enhance_recipe_with_preferences(recipe_data: Dict[str, Any], user_prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance recipe with preference metadata (keeping your logic with security)"""

    # Add preference compliance score
    validation = validate_recipe_against_preferences(recipe_data, user_prefs)
    recipe_data['preference_score'] = validation['score']
    recipe_data['validation_issues'] = validation['issues']

    # Add preference tags safely
    preference_tags = []
    dietary_restrictions = user_prefs.get('dietary_restrictions', {})

    for restriction, active in dietary_restrictions.items():
        if active and isinstance(restriction, str):
            try:
                clean_tag = sanitize_string(restriction.replace('_', '-'), max_length=50, field_name="tag")
                preference_tags.append(clean_tag)
            except:
                continue

    if preference_tags:
        existing_tags = recipe_data.get('tags', [])
        # Ensure existing tags are also clean
        clean_existing = []
        for tag in existing_tags:
            if isinstance(tag, str):
                try:
                    clean_tag = sanitize_string(tag, max_length=50, field_name="tag")
                    clean_existing.append(clean_tag)
                except:
                    continue

        recipe_data['tags'] = list(set(clean_existing + preference_tags))[:10]  # Limit to 10 tags

    # Add macro compliance
    macro_targets = user_prefs.get('macro_targets', {})
    if macro_targets.get('enableTargets'):
        recipe_macros = recipe_data.get('macros', {})
        macro_compliance = {}

        for macro in ['calories', 'protein', 'carbs', 'fat', 'fiber']:
            target = macro_targets.get(macro)
            actual = recipe_macros.get(macro)

            if target and actual:
                try:
                    target_val = float(target)
                    actual_val = float(str(actual).replace('g', '').replace('kcal', ''))
                    if target_val > 0:
                        compliance = 100 - abs((actual_val - target_val) / target_val * 100)
                        macro_compliance[macro] = max(0, min(100, compliance))
                    else:
                        macro_compliance[macro] = 0
                except (ValueError, TypeError, ZeroDivisionError):
                    macro_compliance[macro] = 0

        recipe_data['macro_compliance'] = macro_compliance

    return recipe_data


def parse_ingredient_line_fixed(line: str) -> Dict[str, Any]:
    """Enhanced ingredient parsing with security validation"""

    # Sanitize input first
    try:
        clean_line = sanitize_string(line, max_length=200, field_name="ingredient line")
    except ValidationError:
        logger.warning(f"Invalid ingredient line: {line[:50]}...")
        return None

    # Common units for better detection
    common_units = [
        'cup', 'cups', 'tbsp', 'tsp', 'teaspoon', 'teaspoons', 'tablespoon', 'tablespoons',
        'lb', 'lbs', 'pound', 'pounds', 'oz', 'ounce', 'ounces', 'gram', 'grams', 'kg',
        'cloves', 'clove', 'piece', 'pieces', 'slice', 'slices', 'can', 'cans', 'jar', 'jars',
        'bottle', 'bottles', 'pack', 'packs', 'head', 'heads', 'bunch', 'bunches'
    ]

    # Extract quantity (numbers/fractions at the beginning)
    quantity_pattern = r'^(\d+(?:\.\d+)?(?:/\d+)?|\d+\s+\d+/\d+)'
    quantity_match = re.search(quantity_pattern, clean_line)

    if quantity_match:
        quantity_str = quantity_match.group(1)
        remaining_text = clean_line[quantity_match.end():].strip()

        try:
            if '/' in quantity_str:
                quantity = float(Fraction(quantity_str))
            else:
                quantity = float(quantity_str)
            # Validate reasonable quantity ranges
            quantity = max(0.001, min(1000.0, quantity))
        except (ValueError, ZeroDivisionError):
            quantity = 1.0
            remaining_text = clean_line
    else:
        quantity = 1.0
        remaining_text = clean_line

    # Extract unit from remaining text
    unit = ""
    ingredient_name = remaining_text

    words = remaining_text.split()
    if words:
        first_word = words[0].lower().rstrip(',')
        if first_word in common_units:
            unit = first_word
            ingredient_name = ' '.join(words[1:])

    # Clean up ingredient name
    ingredient_name = ingredient_name.strip()
    ingredient_name = re.sub(r',\s*$', '', ingredient_name)  # Fixed: was r',\s*'
    unit = unit.strip(',')

    # Handle special cases
    if not unit and ',' in ingredient_name:
        parts = ingredient_name.split(',', 1)
        ingredient_name = parts[0].strip()  # Fixed: indentation was wrong

    # Final validation
    if not ingredient_name:
        return None

    try:
        clean_name = sanitize_string(ingredient_name, max_length=100, field_name="ingredient name")
        clean_unit = sanitize_string(unit, max_length=20, field_name="unit") if unit else ""
    except ValidationError:
        return None

    return {
        "name": clean_name.lower(),
        "unit": clean_unit,
        "quantity": quantity
    }


def parse_single_recipe_enhanced(recipe_text: str, recipe_number: int) -> Optional[Dict[str, Any]]:
    """Enhanced recipe parsing with comprehensive security validation"""

    try:
        # Sanitize the entire recipe text first
        clean_recipe_text = sanitize_string(recipe_text, max_length=10000, field_name="recipe text")
    except ValidationError as e:
        logger.warning(f"Recipe {recipe_number} failed validation: {e}")
        return None

    # Extract recipe name
    recipe_name_match = re.search(r'RECIPE\s*\d*:?\s*(.+)', clean_recipe_text)
    if not recipe_name_match:
        logger.warning(f"No name found for recipe {recipe_number}")
        return None

    try:
        recipe_name = sanitize_string(recipe_name_match.group(1).strip(), max_length=200, field_name="recipe name")
    except ValidationError:
        logger.warning(f"Invalid recipe name for recipe {recipe_number}")
        return None

    # Parse ingredients with enhanced validation
    parsed_ingredients = []
    ingredients_match = re.search(r'Ingredients:\s*\n(.*?)(?=\n\s*Directions:|\n\s*Nutrition|\Z)',
                                  clean_recipe_text, re.DOTALL | re.IGNORECASE)

    if ingredients_match:
        ingredients_text = ingredients_match.group(1)
        for line in ingredients_text.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                line = re.sub(r'^[-•*]\s*', '', line).strip()

                ingredient = parse_ingredient_line_fixed(line)
                if ingredient:
                    parsed_ingredients.append(ingredient)

    # Parse directions with validation
    parsed_directions = []
    directions_match = re.search(r'Directions:\s*\n(.*?)(?=\n\s*Nutrition|\n\s*Tags:|\Z)',
                                 clean_recipe_text, re.DOTALL | re.IGNORECASE)

    if directions_match:
        directions_text = directions_match.group(1)
        for line in directions_text.strip().split('\n'):
            line = line.strip()
            if line and (re.match(r'^\d+\.', line) or line.startswith('-')):
                line = re.sub(r'^\d+\.\s*', '', line)
                line = re.sub(r'^[-•*]\s*', '', line)
                if line.strip():
                    try:
                        clean_direction = sanitize_string(line.strip(), max_length=1000, field_name="direction")
                        parsed_directions.append(clean_direction)
                    except ValidationError:
                        continue

    # Validate minimum requirements
    if not recipe_name or len(parsed_ingredients) < 2 or len(parsed_directions) < 2:
        logger.warning(f"Recipe {recipe_number} missing essential components")
        return None

    # Parse nutrition with validation
    macros = {"calories": 0.0, "protein": "0g", "carbs": "0g", "fat": "0g", "fiber": "0g"}
    nutrition_match = re.search(r'Nutrition Facts:\s*\n(.*?)(?=\n\s*Tags:|\n\s*Cuisine:|\Z)',
                                clean_recipe_text, re.DOTALL | re.IGNORECASE)

    if nutrition_match:
        nutrition_text = nutrition_match.group(1)
        for line in nutrition_text.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace('-', '').replace('•', '').replace('*', '').strip()
                value = value.strip()

                if key == 'calories':
                    try:
                        calories_val = float(re.search(r'([\d.]+)', value).group(1))
                        macros['calories'] = max(0, min(5000, calories_val))  # Reasonable bounds
                    except:
                        macros['calories'] = 0.0
                elif key in ['protein', 'carbs', 'fat', 'fiber']:
                    # Validate nutrition values
                    try:
                        clean_value = sanitize_string(value, max_length=20, field_name=f"nutrition {key}")
                        macros[key] = clean_value
                    except ValidationError:
                        macros[key] = "0g"

    # Parse metadata with validation
    def extract_safe_text(pattern: str, field_name: str, max_length: int = 100, default: str = "") -> str:
        match = re.search(pattern, clean_recipe_text, re.IGNORECASE)
        if match:
            try:
                return sanitize_string(match.group(1).strip(), max_length=max_length, field_name=field_name)
            except ValidationError:
                return default
        return default

    def extract_safe_time(pattern: str, field_name: str) -> str:
        match = re.search(pattern, clean_recipe_text, re.IGNORECASE)
        if match:
            time_str = match.group(1).strip()
            # Extract just the number and unit
            time_match = re.search(r'(\d+)\s*(minutes?|mins?|hours?|hrs?)', time_str, re.IGNORECASE)
            if time_match:
                return f"{time_match.group(1)} {time_match.group(2)}"
        return ""

    # Extract metadata safely
    tags = []
    tag_match = re.search(r'Tags:\s*(.+)', clean_recipe_text, re.IGNORECASE)
    if tag_match:
        raw_tags = tag_match.group(1)
        for tag in raw_tags.split(","):
            try:
                clean_tag = sanitize_string(tag.strip(), max_length=50, field_name="tag").lower()
                if clean_tag and clean_tag not in tags:
                    tags.append(clean_tag)
            except ValidationError:
                continue

    # Extract other fields
    cuisine = extract_safe_text(r'Cuisine:\s*(.+)', "cuisine", 100, "Unknown")
    diet = extract_safe_text(r'Diet:\s*(.+)', "diet", 100, "Unknown")
    prep_time = extract_safe_time(r'Prep Time:\s*(.+)', "prep time")
    cook_time = extract_safe_time(r'Cook Time:\s*(.+)', "cook time")
    difficulty = extract_safe_text(r'Difficulty:\s*(.+)', "difficulty", 50, "Intermediate")

    # Parse cost estimate with validation
    cost_estimate = 5.0  # Default
    cost_match = re.search(r'Cost Estimate:\s*\$?([\d.]+)', clean_recipe_text)
    if cost_match:
        try:
            cost_val = float(cost_match.group(1))
            cost_estimate = max(0.01, min(1000.0, cost_val))  # Reasonable bounds
        except ValueError:
            cost_estimate = 5.0
    else:
        # Estimate from ingredients
        try:
            estimated_cost = sum(
                ingredient_prices.get(i["name"], 1.00) * i["quantity"]
                for i in parsed_ingredients
            )
            cost_estimate = max(0.01, min(1000.0, round(estimated_cost, 2)))
        except:
            cost_estimate = 5.0

    # Build grocery list
    grocery_list = estimate_grocery_list(parsed_ingredients)

    return {
        "recipe_text": clean_recipe_text,
        "recipe_name": recipe_name,
        "ingredients": parsed_ingredients,
        "directions": parsed_directions,
        "macros": macros,
        "tags": tags[:10],  # Limit tags
        "cuisine": cuisine,
        "diet": diet,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "difficulty": difficulty,
        "cost_estimate": cost_estimate,
        "grocery_list": grocery_list
    }


def estimate_grocery_list(ingredients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enhanced grocery list estimation with validation"""
    fallback_price = 1.00
    grocery_list = []

    for item in ingredients:
        if not isinstance(item, dict):
            continue

        name = item.get("name", "").lower()
        quantity = item.get("quantity", 1)

        # Validate quantity
        try:
            quantity = max(0.001, min(1000.0, float(quantity)))
        except (ValueError, TypeError):
            quantity = 1.0

        # Get price safely
        unit_price = ingredient_prices.get(name, fallback_price)
        try:
            unit_price = max(0.01, min(1000.0, float(unit_price)))
        except (ValueError, TypeError):
            unit_price = fallback_price

        estimated_cost = round(unit_price * quantity, 2)

        grocery_list.append({
            "item": name,
            "quantity": quantity,
            "estimated_cost": estimated_cost
        })

    return grocery_list


async def save_recipe_to_database_enhanced(user_id: str, recipe_data: Dict[str, Any]) -> Optional[str]:
    """Enhanced recipe saving with comprehensive error handling"""

    try:
        # Validate user ID
        validated_user_id = validate_user_id(user_id)

        # Prepare sanitized data for database
        sanitized_data = {
            "user_id": validated_user_id,
            "title": recipe_data["recipe_name"],
            "ingredients": json.dumps(recipe_data["ingredients"]),
            "directions": json.dumps(recipe_data["directions"]),
            "tags": json.dumps(recipe_data["tags"]),
            "cuisine": recipe_data["cuisine"],
            "diet": recipe_data["diet"],
            "macro_estimate": json.dumps(recipe_data["macros"]),
            "cost_estimate": recipe_data["cost_estimate"],
            "prep_time": recipe_data.get("prep_time", ""),
            "cook_time": recipe_data.get("cook_time", ""),
            "difficulty": recipe_data.get("difficulty", ""),
            "preference_score": recipe_data.get("preference_score", 0),
            "validation_issues": json.dumps(recipe_data.get("validation_issues", [])),
            "macro_compliance": json.dumps(recipe_data.get("macro_compliance", {}))
        }

        async with DatabaseErrorContext("save_recipe", "recipes"):
            # Ensure database is initialized
            if not supabase:
                await init_supabase_compatibility()

            insert_result = await supabase.table("recipes").insert(sanitized_data).execute()

            if insert_result.data and len(insert_result.data) > 0:
                recipe_id = insert_result.data[0]["id"]
                logger.info(f"✅ Saved recipe '{recipe_data['recipe_name']}' with ID: {recipe_id}")
                return recipe_id
            else:
                logger.warning("⚠️ Recipe insert returned no data")
                return None

    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"❌ Error saving recipe to database: {e}")
        raise DatabaseError(f"Failed to save recipe: {str(e)}")


# Enhanced API Endpoints

@router.post("/generate-recipe-with-advanced-preferences")
@safe_operation("generate_recipe_with_advanced_preferences")
async def generate_recipe_with_advanced_preferences(req: AdvancedRecipeRequest):
    """Generate recipes using advanced user preferences with full P0/P1 security"""

    import time
    start_time = time.time()

    logger.info(f"Advanced recipe generation for user {req.user_id[:8]}...: '{req.title}'")

    try:
        # Get comprehensive user preferences
        user_prefs = await get_advanced_user_preferences(req.user_id)

        # Override with request-specific preferences
        if req.budget is not None:
            user_prefs['budget'] = req.budget
        if req.allergies is not None:
            user_prefs['allergies'] = req.allergies
        if req.diet is not None:
            user_prefs['diet'] = req.diet
        if req.dietary_restrictions:
            user_prefs['dietary_restrictions'].update(req.dietary_restrictions)
        if req.cooking_constraints:
            user_prefs['cooking_constraints'].update(req.cooking_constraints)
        if req.cuisine_preferences:
            user_prefs['cuisine_preferences'].update(req.cuisine_preferences)
        if req.macro_targets:
            user_prefs['macro_targets'].update(req.macro_targets)

        logger.debug(
            f"Active dietary restrictions: {[k for k, v in user_prefs.get('dietary_restrictions', {}).items() if v]}")
        logger.debug(f"Preferred cuisines: {user_prefs.get('cuisine_preferences', {}).get('preferred', [])}")
        logger.debug(f"Macro targets enabled: {user_prefs.get('macro_targets', {}).get('enableTargets', False)}")

        # Build enhanced prompt
        prompt = await build_advanced_prompt(req.title, user_prefs, req.num_recipes)

        # Generate using async OpenAI service
        async with ExternalServiceErrorContext("openai", "advanced_recipe_generation", req.user_id):
            content = await openai_service.generate_recipe(
                user_preferences=user_prefs,
                recipe_title=req.title,
                num_recipes=req.num_recipes,
                use_advanced=True
            )

        if not content:
            raise ExternalServiceError("AI service returned empty response", service="openai")

        logger.debug("✅ Received OpenAI response, parsing recipes...")

        # Parse recipes with enhanced security
        raw_recipes = [blk.strip() for blk in content.split("---") if blk.strip()]
        if len(raw_recipes) < req.num_recipes:
            raw_recipes = re.split(r'(?=RECIPE\s*\d+:)', content)
            raw_recipes = [blk.strip() for blk in raw_recipes if blk.strip()]

        parsed_recipes = []
        for idx, recipe_text in enumerate(raw_recipes[:req.num_recipes]):
            try:
                # Parse with enhanced validation
                recipe_data = parse_single_recipe_enhanced(recipe_text, idx + 1)

                if recipe_data:
                    # Enhance with preference data
                    recipe_data = enhance_recipe_with_preferences(recipe_data, user_prefs)

                    # Save to database
                    recipe_id = await save_recipe_to_database_enhanced(req.user_id, recipe_data)
                    if recipe_id:
                        recipe_data["recipe_id"] = recipe_id

                    parsed_recipes.append(recipe_data)
                    logger.debug(
                        f"✅ Generated recipe {idx + 1}: {recipe_data.get('recipe_name')} (Score: {recipe_data.get('preference_score', 0)})")

            except Exception as e:
                logger.warning(f"Failed to parse recipe {idx + 1}: {e}")
                continue

        if not parsed_recipes:
            raise BusinessLogicError("No valid recipes could be generated")

        # Sort recipes by preference score (highest first)
        parsed_recipes.sort(key=lambda x: x.get('preference_score', 0), reverse=True)

        generation_time = time.time() - start_time

        logger.info(
            f"🎉 Successfully generated {len(parsed_recipes)} recipes with advanced preferences in {generation_time:.2f}s")

        return {
            "recipes": parsed_recipes,
            "generation_time": generation_time,
            "preferences_applied": {
                "dietary_restrictions": len([k for k, v in user_prefs.get('dietary_restrictions', {}).items() if v]),
                "macro_targets_enabled": user_prefs.get('macro_targets', {}).get('enableTargets', False),
                "cuisine_preferences": len(user_prefs.get('cuisine_preferences', {}).get('preferred', [])),
                "cooking_constraints": len([k for k, v in user_prefs.get('cooking_constraints', {}).items() if v])
            },
            "total_recipes": len(parsed_recipes)
        }

    except ValidationError:
        raise  # Re-raise validation errors
    except ExternalServiceError:
        raise  # Re-raise service errors  
    except BusinessLogicError:
        raise  # Re-raise business logic errors
    except Exception as e:
        logger.error(f"❌ Unexpected error in advanced recipe generation: {e}")
        raise ExternalServiceError(f"Advanced recipe generation failed: {str(e)}")


@router.get("/user-preference-insights/{user_id}")
@safe_operation("get_user_preference_insights")
async def get_user_preference_insights(user_id: str):
    """Get insights about user's preference usage and compliance with enhanced security"""

    # Validate user ID
    validated_user_id = validate_user_id(user_id)

    try:
        async with DatabaseErrorContext("get_preference_insights", "recipes"):
            # Ensure database is initialized
            if not supabase:
                await init_supabase_compatibility()

            # Get user's recipes with preference scores
            recipes_result = await supabase.table("recipes") \
                .select("preference_score, macro_compliance, validation_issues, cuisine, tags") \
                .eq("user_id", validated_user_id) \
                .execute()

            recipes = recipes_result.data or []

            if not recipes:
                return {
                    "insights": {
                        "total_recipes": 0,
                        "avg_preference_score": 0,
                        "top_compliant_cuisines": [],
                        "common_validation_issues": [],
                        "macro_compliance_avg": {}
                    }
                }

            # Calculate insights safely
            total_recipes = len(recipes)
            avg_score = sum(r.get("preference_score", 0) for r in recipes) / total_recipes

            # Cuisine compliance analysis
            cuisine_scores = {}
            for recipe in recipes:
                cuisine = recipe.get("cuisine", "Unknown")
                score = recipe.get("preference_score", 0)

                # Validate cuisine value
                try:
                    clean_cuisine = sanitize_string(str(cuisine), max_length=100, field_name="cuisine")
                    if clean_cuisine not in cuisine_scores:
                        cuisine_scores[clean_cuisine] = []
                    cuisine_scores[clean_cuisine].append(float(score))
                except (ValidationError, ValueError, TypeError):
                    continue

            top_cuisines = [
                {"cuisine": cuisine, "avg_score": round(sum(scores) / len(scores), 1)}
                for cuisine, scores in cuisine_scores.items()
            ]
            top_cuisines.sort(key=lambda x: x["avg_score"], reverse=True)

            # Common validation issues (safely)
            all_issues = []
            for recipe in recipes:
                issues = recipe.get("validation_issues", [])
                if isinstance(issues, str):
                    try:
                        issues = json.loads(issues)
                    except:
                        issues = []
                elif not isinstance(issues, list):
                    issues = []

                for issue in issues:
                    if isinstance(issue, str):
                        try:
                            clean_issue = sanitize_string(issue, max_length=200, field_name="validation issue")
                            all_issues.append(clean_issue)
                        except ValidationError:
                            continue

            issue_counts = {}
            for issue in all_issues:
                issue_counts[issue] = issue_counts.get(issue, 0) + 1

            common_issues = [
                {"issue": issue, "count": count}
                for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            ]

            # Macro compliance averages (safely)
            macro_compliance_totals = {}
            macro_count = 0

            for recipe in recipes:
                compliance = recipe.get("macro_compliance", {})
                if isinstance(compliance, str):
                    try:
                        compliance = json.loads(compliance)
                    except:
                        compliance = {}
                elif not isinstance(compliance, dict):
                    compliance = {}

                if compliance:
                    macro_count += 1
                    for macro, score in compliance.items():
                        if isinstance(macro, str) and isinstance(score, (int, float)):
                            if macro not in macro_compliance_totals:
                                macro_compliance_totals[macro] = []
                            macro_compliance_totals[macro].append(float(score))

            macro_compliance_avg = {}
            for macro, scores in macro_compliance_totals.items():
                if scores:
                    macro_compliance_avg[macro] = round(sum(scores) / len(scores), 1)

            return {
                "insights": {
                    "total_recipes": total_recipes,
                    "avg_preference_score": round(avg_score, 1),
                    "top_compliant_cuisines": top_cuisines[:5],
                    "common_validation_issues": common_issues,
                    "macro_compliance_avg": macro_compliance_avg,
                    "recipes_with_issues": len([r for r in recipes if r.get("validation_issues")])
                }
            }

    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"❌ Error getting preference insights: {e}")
        raise DatabaseError(f"Failed to get insights: {str(e)}")


@router.patch("/update-user-preferences/{user_id}")
@safe_operation("update_user_preferences_from_feedback")
async def update_user_preferences_from_feedback(user_id: str, feedback_data: UserPreferenceFeedback):
    """Update user preferences based on recipe feedback with enhanced security"""

    # Validate user ID
    validated_user_id = validate_user_id(user_id)

    try:
        async with DatabaseErrorContext("update_user_preferences", "user_preferences"):
            # Get current preferences
            current_prefs = await get_advanced_user_preferences(validated_user_id)

            # Update preferences based on validated feedback
            recipe_rating = feedback_data.rating
            recipe_cuisine = feedback_data.cuisine or ""
            feedback_reason = feedback_data.feedback_reason or ""

            # Adjust cuisine preferences based on ratings
            if recipe_rating >= 4 and recipe_cuisine:
                # Add to preferred if not already there
                preferred_cuisines = current_prefs.get("cuisine_preferences", {}).get("preferred", [])
                if recipe_cuisine not in preferred_cuisines:
                    preferred_cuisines.append(recipe_cuisine)
                    if "cuisine_preferences" not in current_prefs:
                        current_prefs["cuisine_preferences"] = {}
                    current_prefs["cuisine_preferences"]["preferred"] = preferred_cuisines[:10]  # Limit

            elif recipe_rating <= 2 and recipe_cuisine:
                # Add to disliked if feedback indicates cuisine issues
                if "cuisine" in feedback_reason.lower():
                    disliked_cuisines = current_prefs.get("cuisine_preferences", {}).get("disliked", [])
                    if recipe_cuisine not in disliked_cuisines:
                        disliked_cuisines.append(recipe_cuisine)
                        if "cuisine_preferences" not in current_prefs:
                            current_prefs["cuisine_preferences"] = {}
                        current_prefs["cuisine_preferences"]["disliked"] = disliked_cuisines[:10]  # Limit

            # Ensure database is initialized
            if not supabase:
                await init_supabase_compatibility()

            # Update preferences in database
            update_result = await supabase.table("user_preferences") \
                .update(current_prefs) \
                .eq("user_id", validated_user_id) \
                .execute()

            logger.info(f"✅ Updated preferences for user {validated_user_id[:8]}... based on feedback")

            return {
                "success": True,
                "message": "Preferences updated based on feedback",
                "updated_preferences": current_prefs
            }

    except ValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"❌ Error updating preferences: {e}")
        raise DatabaseError(f"Failed to update preferences: {str(e)}")


# Backward compatibility endpoint
@router.post("/generate-recipe-with-grocery")
@safe_operation("generate_recipe_with_grocery")
async def generate_recipe_with_grocery(req: RecipeRequest):
    """Backward compatibility endpoint - converts to advanced request"""

    # Convert old request to new format
    advanced_req = AdvancedRecipeRequest(
        title=req.title,
        user_id=req.user_id,
        num_recipes=3  # Default
    )

    # Use the advanced endpoint
    return await generate_recipe_with_advanced_preferences(advanced_req)


# Add these new routes to recipes.py

@router.post("/optimize-meal-plan")
async def optimize_meal_plan(request: MealPlanRequest):
    """Generate AI-optimized weekly meal plan"""
    try:
        user_id = validate_user_id(request.user_id)

        # Get user preferences
        user_prefs = await get_advanced_user_preferences(user_id)

        # Merge with request requirements
        requirements = {
            **user_prefs,
            **request.dict(exclude={'user_id'})
        }

        # Generate optimized plan
        plan = await openai_service.optimize_meal_plan(
            requirements=requirements,
            duration_days=request.days,
            optimization_goals=request.goals
        )

        # Save to database if requested
        if request.save_to_calendar:
            await save_meal_plan_to_calendar(user_id, plan)

        return {"status": "success", "meal_plan": plan}

    except Exception as e:
        logger.error(f"Meal plan optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-recipe-image")
async def analyze_recipe_image(
        image_url: str = Query(..., description="URL of recipe image"),
        user_id: str = Query(..., description="User ID")
):
    """Analyze recipe from image using AI vision"""
    try:
        user_id = validate_user_id(user_id)

        # Analyze image
        analysis = await openai_service.analyze_recipe_image(
            image_url=image_url,
            analysis_type="comprehensive"
        )

        # Convert to recipe format if successful
        if analysis.get("recipe_detected"):
            recipe = await convert_image_analysis_to_recipe(analysis, user_id)
            return {"status": "success", "analysis": analysis, "recipe": recipe}

        return {"status": "success", "analysis": analysis}

    except Exception as e:
        logger.error(f"Recipe image analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# Export router
__all__ = ['router']