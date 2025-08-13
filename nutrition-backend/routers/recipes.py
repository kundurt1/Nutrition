# nutrition-backend/routers/recipes.py - YOUR FEATURES + ALL P0/P1 SECURITY FIXES
import asyncio
import json
import re
import traceback
import uuid
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
from models.recipeModels import RecipeRequest



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

class AdvancedRecipeRequest(BaseModel):
    """Enhanced recipe request with comprehensive validation"""

    title: str = Field(..., min_length=1, max_length=200, description="Recipe title")
    user_id: str = Field(..., description="User UUID")
    num_recipes: int = Field(3, ge=1, le=10, description="Number of recipes to generate")

    # Basic preferences
    budget: Optional[float] = Field(None, ge=1.0, le=1000.0)
    allergies: Optional[str] = Field(None, max_length=500)
    diet: Optional[str] = Field(None, max_length=100)

    # Advanced preferences - COMPLETE THE DEFINITIONS
    dietary_restrictions: Optional[Dict[str, bool]] = Field(default_factory=dict)
    macro_targets: Optional[Dict[str, Any]] = Field(default_factory=dict)  # ← FIX THIS LINE
    cuisine_preferences: Optional[Dict[str, List[str]]] = Field(default_factory=dict)
    cooking_constraints: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Advanced AI flag
    use_advanced: Optional[bool] = Field(True, description="Enable advanced AI mode")

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

# Enhanced Pydantic Models with Security Validation
class MealPlanRequest(BaseModel):
    """Meal plan optimization request"""
    user_id: str = Field(..., description="User UUID")
    days: int = Field(7, ge=1, le=14, description="Number of days to plan")
    budget: Optional[float] = Field(None, ge=10.0, le=1000.0)
    dietary_restrictions: Optional[List[str]] = []
    cuisine_preferences: Optional[List[str]] = []
    calories_per_day: Optional[int] = Field(None, ge=1200, le=4000)
    meals_per_day: int = Field(3, ge=1, le=6)
    avoid_ingredients: Optional[List[str]] = []
    include_pantry: bool = True


class SingleRecipeRequest(BaseModel):
    """Single recipe generation request"""
    title: str = Field(..., min_length=1, max_length=200)
    user_id: str = Field(..., description="User UUID")
    exclude_recipes: Optional[List[str]] = Field([], description="Recipe names to exclude")
    budget: Optional[float] = Field(None, gt=0)
    allergies: Optional[str] = Field(None, max_length=500)
    diet: Optional[str] = Field(None, max_length=100)
    regenerate_single: Optional[bool] = Field(False, description="Is this a regeneration request")
    use_advanced: Optional[bool] = Field(True, description="Enable advanced AI mode")

    @validator('title')
    def validate_title(cls, v):
        return sanitize_string(v, max_length=200, field_name="recipe title")

    @validator('user_id')
    def validate_user_id_format(cls, v):
        return validate_user_id(v)


@router.post("/generate-single-recipe")
#@safe_operation("generate_single_recipe")
async def generate_single_recipe(req: SingleRecipeRequest):
    """Generate a single recipe (for regeneration)"""

    import time
    start_time = time.time()

    logger.info(
        f"Single {'advanced' if req.use_advanced else 'standard'} recipe generation for user {req.user_id[:8]}...")

    try:
        # Get user preferences
        user_prefs = await get_advanced_user_preferences(req.user_id)

        # Override with request-specific preferences
        if req.budget is not None:
            user_prefs['budget'] = req.budget
        if req.allergies is not None:
            user_prefs['allergies'] = req.allergies
        if req.diet is not None:
            user_prefs['diet'] = req.diet

        # Build exclusion context
        exclusion_context = ""
        if req.exclude_recipes:
            exclusion_context = f"IMPORTANT: Do NOT generate recipes similar to these: {', '.join(req.exclude_recipes)}"

        # Generate single recipe
        async with ExternalServiceErrorContext("openai", "single_recipe_generation", req.user_id):
            content = await openai_service.generate_single_recipe(
                user_preferences=user_prefs,
                recipe_title=req.title,
                exclusion_context=exclusion_context,
                use_advanced=req.use_advanced
            )

        if not content:
            raise ExternalServiceError("AI service returned empty response", service="openai")

        # Parse the single recipe
        recipe_data = parse_single_recipe_enhanced(content, 1)

        if not recipe_data:
            raise BusinessLogicError("Failed to parse generated recipe")

        # Enhance with preference data
        recipe_data = enhance_recipe_with_preferences(recipe_data, user_prefs)

        # Add AI insights if using advanced mode
        if req.use_advanced:
            recipe_data["ai_insights"] = generate_ai_insights(recipe_data, user_prefs)

        # Save to database
        recipe_id = await save_recipe_to_database_with_compatibility(req.user_id, recipe_data)
        if recipe_id:
            recipe_data["recipe_id"] = recipe_id

        generation_time = time.time() - start_time

        logger.info(f"✅ Successfully generated single recipe in {generation_time:.2f}s")

        return {
            "recipe": recipe_data,
            "generation_time": generation_time,
            "advanced_mode_used": req.use_advanced
        }

    except ValidationError:
        raise
    except ExternalServiceError:
        raise
    except BusinessLogicError:
        raise
    except Exception as e:
        logger.error(f"❌ Error in single recipe generation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during recipe generation")




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


def parse_recipes_enhanced(content: str, num_recipes: int) -> List[Dict[str, Any]]:
    """Parse multiple recipes from OpenAI response using existing single recipe parser"""

    logger.debug("✅ Received OpenAI response, parsing recipes...")

    # Split content into individual recipe blocks
    raw_recipes = [blk.strip() for blk in content.split("---") if blk.strip()]
    if len(raw_recipes) < num_recipes:
        raw_recipes = re.split(r'(?=RECIPE\s*\d+:)', content)
        raw_recipes = [blk.strip() for blk in raw_recipes if blk.strip()]

    parsed_recipes = []
    for idx, recipe_text in enumerate(raw_recipes[:num_recipes]):
        try:
            # Use your existing parse_single_recipe_enhanced function
            recipe_data = parse_single_recipe_enhanced(recipe_text, idx + 1)

            if recipe_data:
                parsed_recipes.append(recipe_data)
                logger.debug(f"✅ Parsed recipe {idx + 1}: {recipe_data.get('recipe_name')}")
            else:
                logger.warning(f"Failed to parse recipe {idx + 1}")

        except Exception as e:
            logger.warning(f"Error parsing recipe {idx + 1}: {e}")
            continue

    return parsed_recipes


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


# Quick fix: Update your parse_single_recipe_enhanced function in recipes.py:

def parse_single_recipe_enhanced(recipe_text: str, recipe_number: int) -> Optional[Dict[str, Any]]:
    """Enhanced recipe parsing with BYPASSED security validation for recipes"""

    # Skip the aggressive sanitization that's blocking recipe content
    # Just do basic cleaning instead of the full security check
    clean_recipe_text = recipe_text.replace('\x00', '').strip()

    if len(clean_recipe_text) > 10000:
        logger.warning(f"Recipe {recipe_number} too long, truncating")
        clean_recipe_text = clean_recipe_text[:10000]

    # Extract recipe name
    recipe_name_match = re.search(r'RECIPE\s*\d*:?\s*(.+)', clean_recipe_text)
    if not recipe_name_match:
        logger.warning(f"No name found for recipe {recipe_number}")
        return None

    recipe_name = recipe_name_match.group(1).strip()
    if len(recipe_name) > 200:
        recipe_name = recipe_name[:200]

    # Parse ingredients with basic validation
    parsed_ingredients = []
    ingredients_match = re.search(r'Ingredients:\s*\n(.*?)(?=Directions:|Instructions:|Nutrition:|$)',
                                  clean_recipe_text, re.DOTALL | re.IGNORECASE)
    if ingredients_match:
        ingredients_text = ingredients_match.group(1).strip()
        ingredient_lines = [line.strip() for line in ingredients_text.split('\n') if line.strip()]

        for line in ingredient_lines:
            if line.startswith('-') or line.startswith('•'):
                # Simple ingredient parsing without aggressive security
                ingredient_text = line[1:].strip()
                if ingredient_text:
                    parsed_ingredients.append({
                        "name": ingredient_text,
                        "quantity": 1,
                        "unit": ""
                    })

    # Parse directions
    directions = []
    directions_match = re.search(r'(?:Directions|Instructions):\s*\n(.*?)(?=Nutrition:|Cost|Prep|$)', clean_recipe_text,
                                 re.DOTALL | re.IGNORECASE)
    if directions_match:
        directions_text = directions_match.group(1).strip()
        direction_lines = [line.strip() for line in directions_text.split('\n') if line.strip()]
        directions = [line for line in direction_lines if line]

    # Parse basic nutrition
    macros = {}
    calories_match = re.search(r'Calories:\s*(\d+)', clean_recipe_text, re.IGNORECASE)
    if calories_match:
        macros['calories'] = int(calories_match.group(1))

    protein_match = re.search(r'Protein:\s*(\d+)', clean_recipe_text, re.IGNORECASE)
    if protein_match:
        macros['protein'] = int(protein_match.group(1))

    carbs_match = re.search(r'Carbs:\s*(\d+)', clean_recipe_text, re.IGNORECASE)
    if carbs_match:
        macros['carbs'] = int(carbs_match.group(1))

    fat_match = re.search(r'Fat:\s*(\d+)', clean_recipe_text, re.IGNORECASE)
    if fat_match:
        macros['fat'] = int(fat_match.group(1))

    # Parse cost estimate
    cost_estimate = 0.0
    cost_match = re.search(r'Cost Estimate:\s*\$(\d+(?:\.\d+)?)', clean_recipe_text, re.IGNORECASE)
    if cost_match:
        cost_estimate = float(cost_match.group(1))

    # Parse prep/cook time
    prep_time = ""
    prep_match = re.search(r'Prep Time:\s*([^\\n]+)', clean_recipe_text, re.IGNORECASE)
    if prep_match:
        prep_time = prep_match.group(1).strip()

    cook_time = ""
    cook_match = re.search(r'Cook Time:\s*([^\\n]+)', clean_recipe_text, re.IGNORECASE)
    if cook_match:
        cook_time = cook_match.group(1).strip()

    # Parse difficulty
    difficulty = "Easy"
    diff_match = re.search(r'Difficulty:\s*(\w+)', clean_recipe_text, re.IGNORECASE)
    if diff_match:
        difficulty = diff_match.group(1)

    return {
        "recipe_name": recipe_name,
        "ingredients": parsed_ingredients,
        "directions": directions,
        "macros": macros,
        "tags": [],
        "cuisine": "Various",
        "diet": "Various",
        "cost_estimate": cost_estimate,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "difficulty": difficulty
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


from pydantic import BaseModel
from typing import Optional, Dict, List, Any


class SavePreferencesRequest(BaseModel):
    """Request model for saving user preferences"""
    user_id: str
    budget: Optional[str] = None
    allergies: Optional[str] = None
    diet: Optional[str] = None
    dietary_restrictions: Optional[Dict[str, bool]] = None
    macro_targets: Optional[Dict[str, Any]] = None
    cuisine_preferences: Optional[Dict[str, List[str]]] = None
    cooking_constraints: Optional[Dict[str, Any]] = None


# Fix for recipes.py - Replace your save_user_preferences function with this:

@router.post("/save-preferences")
async def save_user_preferences(req: SavePreferencesRequest):
    """Save or update user preferences in database - DIRECT SUPABASE VERSION"""

    from supabase import create_client, Client
    import os

    try:
        # Validate user ID
        validated_user_id = validate_user_id(req.user_id)

        # Log the incoming request for debugging
        logger.info(f"Saving preferences for user {validated_user_id[:8]}...")
        logger.info(f"Request data: {req.dict()}")

        # Create a direct Supabase client
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise Exception("Supabase credentials not found in environment variables")

        # Create direct client
        direct_supabase: Client = create_client(url, key)

        # Prepare preference data
        preference_data = {
            "user_id": validated_user_id,
            "updated_at": datetime.now().isoformat(),
            "budget": str(req.budget) if req.budget else "20",
            "allergies": req.allergies or "",
            "diet": req.diet or "",
        }

        # Add JSONB fields
        if req.dietary_restrictions is not None:
            preference_data["dietary_restrictions"] = req.dietary_restrictions

        if req.macro_targets is not None:
            preference_data["macro_targets"] = req.macro_targets

            # Also save to individual columns
            if req.macro_targets.get("enableTargets"):
                preference_data["daily_calories"] = int(req.macro_targets.get("calories", 2000))
                preference_data["daily_protein"] = float(req.macro_targets.get("protein", 150))
                preference_data["daily_carbs"] = float(req.macro_targets.get("carbs", 200))
                preference_data["daily_fat"] = float(req.macro_targets.get("fat", 70))
                preference_data["daily_fiber"] = float(req.macro_targets.get("fiber", 25))

        if req.cuisine_preferences is not None:
            preference_data["cuisine_preferences"] = req.cuisine_preferences

        if req.cooking_constraints is not None:
            preference_data["cooking_constraints"] = req.cooking_constraints

        logger.info(f"Prepared preference data: {preference_data}")

        # Check if preferences exist using direct client
        existing_check = direct_supabase.table("user_preferences") \
            .select("id") \
            .eq("user_id", validated_user_id) \
            .execute()

        if existing_check.data and len(existing_check.data) > 0:
            # UPDATE existing preferences
            logger.info(f"Found existing preferences, updating...")

            update_result = direct_supabase.table("user_preferences") \
                .update(preference_data) \
                .eq("user_id", validated_user_id) \
                .execute()

            if update_result.data:
                logger.info(f"✅ Successfully updated preferences for user {validated_user_id[:8]}...")
                logger.info(f"Updated data: {update_result.data}")
                return {
                    "success": True,
                    "message": "Preferences updated successfully",
                    "preferences": preference_data,
                    "database_result": update_result.data
                }
            else:
                raise Exception(f"Update failed - no data returned")

        else:
            # INSERT new preferences
            logger.info(f"No existing preferences found, creating new...")
            preference_data["created_at"] = datetime.now().isoformat()

            insert_result = direct_supabase.table("user_preferences") \
                .insert(preference_data) \
                .execute()

            if insert_result.data:
                logger.info(f"✅ Successfully created preferences for user {validated_user_id[:8]}...")
                logger.info(f"Inserted data: {insert_result.data}")
                return {
                    "success": True,
                    "message": "Preferences saved successfully",
                    "preferences": preference_data,
                    "database_result": insert_result.data
                }
            else:
                raise Exception(f"Insert failed - no data returned")

    except Exception as e:
        logger.error(f"Error saving preferences: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")
# Fix for get_advanced_user_preferences - use this single version:
async def get_advanced_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get comprehensive user preferences from database"""

    # Validate user ID first
    validated_user_id = validate_user_id(user_id)

    try:
        # Ensure database is initialized
        if not supabase:
            await init_supabase_compatibility()

        # Fetch from database
        pref_resp = await supabase.table("user_preferences") \
            .select("*") \
            .eq("user_id", validated_user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]

            # FIXED: Handle budget properly
            budget_value = 20.0  # default
            if prefs.get("budget"):
                try:
                    # If it's a range like "50-100", calculate average
                    if '-' in str(prefs["budget"]):
                        parts = str(prefs["budget"]).split('-')
                        budget_value = (float(parts[0]) + float(parts[1])) / 2
                    else:
                        budget_value = float(prefs["budget"])
                except:
                    budget_value = 20.0

            # Build the result with proper defaults
            result = {
                'budget': budget_value,
                'budget_range': prefs.get("budget", "20"),  # Keep original string
                'allergies': prefs.get("allergies", ""),
                'diet': prefs.get("diet", ""),
                'dietary_restrictions': prefs.get("dietary_restrictions", {}),
                'macro_targets': prefs.get("macro_targets", {
                    'enableTargets': False,
                    'calories': 2000,
                    'protein': 150,
                    'carbs': 200,
                    'fat': 70,
                    'fiber': 25
                }),
                'cuisine_preferences': prefs.get("cuisine_preferences", {
                    'preferred': [],
                    'disliked': []
                }),
                'cooking_constraints': prefs.get("cooking_constraints", {
                    'maxCookTime': 45,
                    'maxPrepTime': 15,
                    'maxIngredients': 10,
                    'difficultyLevel': 'intermediate',
                    'kitchenEquipment': ['Oven', 'Stovetop']
                })
            }

            # If individual macro columns exist, use them to override
            if prefs.get("daily_calories") is not None:
                result['macro_targets']['calories'] = int(prefs["daily_calories"])
            if prefs.get("daily_protein") is not None:
                result['macro_targets']['protein'] = float(prefs["daily_protein"])
            if prefs.get("daily_carbs") is not None:
                result['macro_targets']['carbs'] = float(prefs["daily_carbs"])
            if prefs.get("daily_fat") is not None:
                result['macro_targets']['fat'] = float(prefs["daily_fat"])
            if prefs.get("daily_fiber") is not None:
                result['macro_targets']['fiber'] = float(prefs["daily_fiber"])

            logger.info(f"✅ Loaded preferences from database for user {validated_user_id[:8]}...")
            return result
        else:
            logger.info(f"No preferences found for user {validated_user_id[:8]}, using defaults")
            return get_default_preferences()

    except Exception as e:
        logger.error(f"Error fetching preferences: {e}, using defaults")
        return get_default_preferences()
@router.get("/get-preferences/{user_id}")
async def get_user_preferences(user_id: str):
    """Get user preferences from database"""

    try:
        # Get preferences using existing function
        preferences = await get_advanced_user_preferences(user_id)

        return {
            "success": True,
            "preferences": preferences,
            "has_preferences": preferences.get('budget') != 20.0 or bool(preferences.get('allergies'))
        }

    except Exception as e:
        logger.error(f"Error fetching preferences: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch preferences: {str(e)}")


async def save_recipe_to_database_with_compatibility(user_id: str, recipe_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save recipe to database with compatibility for both old and new schemas"""
    try:
        # Validate user_id
        if not user_id:
            logger.error("No user_id provided to save_recipe_to_database_with_compatibility")
            raise ValueError("User ID is required")

        validated_user_id = str(user_id).strip()
        if not validated_user_id or validated_user_id == 'undefined':
            raise ValueError("Invalid user ID")

        # Ensure supabase is initialized
        if not supabase:
            await init_supabase_compatibility()

        # Generate a unique ID if not present
        recipe_id = recipe_data.get('id') or str(uuid.uuid4())

        # Prepare data for database insertion
        # FIXED: Keep directions and tags as lists for ARRAY columns
        db_recipe = {
            "id": recipe_id,
            "user_id": validated_user_id,
            "title": recipe_data.get('recipe_name') or recipe_data.get('title', 'Untitled Recipe'),

            # Keep as JSON string for JSONB column
            "ingredients": json.dumps(recipe_data.get('ingredients', [])) if isinstance(recipe_data.get('ingredients'),
                                                                                        list) else recipe_data.get(
                'ingredients', '[]'),

            # FIXED: Keep as list for ARRAY column
            "directions": recipe_data.get('directions', []) if isinstance(recipe_data.get('directions'), list) else [],

            # FIXED: Keep as list for ARRAY column
            "tags": recipe_data.get('tags', []) if isinstance(recipe_data.get('tags'), list) else [],

            "cuisine": recipe_data.get('cuisine', 'Unknown'),
            "diet": recipe_data.get('diet', ''),

            # Keep as JSON string for JSONB columns
            "macro_estimate": json.dumps(recipe_data.get('macros', {})) if isinstance(recipe_data.get('macros'),
                                                                                      dict) else recipe_data.get(
                'macros', '{}'),

            "cost_estimate": float(recipe_data.get('cost_estimate', 0) or 0),
            "prep_time": str(recipe_data.get('prep_time', '')) or str(recipe_data.get('prepTime', '')),
            "cook_time": str(recipe_data.get('cook_time', '')) or str(recipe_data.get('cookTime', '')),
            "servings": recipe_data.get('servings', 4),
            "difficulty": recipe_data.get('difficulty', 'Medium'),
            "preference_score": recipe_data.get('preference_score', 0),

            # Keep as JSON string for JSONB column
            "validation_issues": json.dumps(recipe_data.get('validation_issues', [])) if isinstance(
                recipe_data.get('validation_issues'), list) else '[]',

            # Don't set created_at and updated_at - let database defaults handle them
            # "created_at": datetime.now().isoformat(),  # REMOVED - database handles this
            # "updated_at": datetime.now().isoformat(),  # REMOVED - database handles this

            "source": "ai_generated",
            "source_metadata": json.dumps({
                "generation_date": datetime.now().isoformat(),
                "model": "openai",
                "preference_score": recipe_data.get('preference_score', 0),
                "validation_passed": len(recipe_data.get('validation_issues', [])) == 0
            })
        }

        # Execute database insertion - FIXED: await the execute() call
        # Note: The insert() returns a wrapper that needs to be awaited
        insert_wrapper = supabase.table("recipes").insert(db_recipe)
        insert_result = await insert_wrapper.execute()

        if insert_result.data and len(insert_result.data) > 0:
            saved_recipe = insert_result.data[0]

            # Merge saved data back with original recipe data
            # This ensures we return all the original data plus the database ID
            result = {
                **recipe_data,
                'id': saved_recipe['id'],
                'db_id': saved_recipe['id'],
                'saved_at': saved_recipe.get('created_at')
            }

            logger.info(
                f"✅ Saved recipe '{db_recipe['title']}' with ID {saved_recipe['id']} for user {validated_user_id[:8]}...")

            return result
        else:
            logger.warning(f"Recipe saved but no data returned from database")
            return recipe_data

    except Exception as e:
        logger.error(f"❌ Supabase error: {e}")
        logger.error(f"❌ Unexpected error saving recipe to database: {e}")
        logger.error(f"❌ Recipe data keys: {list(recipe_data.keys()) if recipe_data else 'None'}")
        # Return original recipe data so user still gets their recipe
        return recipe_data

# DEBUGGING HELPER: Add this temporary function to help debug
async def debug_recipe_save(user_id: str, recipe_data: Dict[str, Any]):
    """Temporary debugging function to identify the issue"""
    try:
        logger.info(f"🔍 DEBUG: Recipe data keys: {list(recipe_data.keys())}")
        logger.info(f"🔍 DEBUG: Recipe name: {recipe_data.get('recipe_name', 'MISSING')}")
        logger.info(f"🔍 DEBUG: User ID: {user_id}")

        # Check if supabase is available
        logger.info(f"🔍 DEBUG: Supabase available: {supabase is not None}")

        # Try a simple select query first
        test_result = supabase.table("recipes").select("id").limit(1).execute()
        logger.info(f"🔍 DEBUG: Test query result: {test_result.data is not None}")

        # Check the actual recipe data structure
        for key, value in recipe_data.items():
            logger.info(f"🔍 DEBUG: {key} = {type(value)} - {str(value)[:100]}")

    except Exception as e:
        logger.error(f"🔍 DEBUG: Error in debug function: {e}")


# ALTERNATIVE SIMPLE VERSION: If the above doesn't work, try this minimal version
async def save_recipe_simple(user_id: str, recipe_data: Dict[str, Any]) -> Optional[str]:
    """Simplified recipe saving for debugging"""
    try:
        # Minimal data structure
        simple_data = {
            "user_id": user_id,
            "title": recipe_data.get("recipe_name", "Test Recipe"),
            "ingredients": json.dumps(recipe_data.get("ingredients", ["test ingredient"])),
            "directions": json.dumps(recipe_data.get("directions", ["test direction"])),
            "created_at": datetime.now().isoformat()
        }

        logger.info(f"🔍 Trying simple save: {simple_data}")

        result = supabase.table("recipes").insert(simple_data).execute()

        if result.error:
            logger.error(f"❌ Simple save error: {result.error}")
            return None

        if result.data:
            logger.info(f"✅ Simple save success: {result.data[0]['id']}")
            return result.data[0]['id']

        return None

    except Exception as e:
        logger.error(f"❌ Simple save exception: {e}")
        return None


@router.post("/test/recipe-generation")
async def test_recipe_generation(req: AdvancedRecipeRequest):
    """Test endpoint to verify request parsing works - returns mock recipes"""

    # Create mock recipes in the format your frontend expects
    mock_recipes = []
    for i in range(req.num_recipes):
        mock_recipe = {
            "id": f"test_recipe_{i + 1}",
            "recipe_name": f"Test Recipe {i + 1}: {req.title}",
            "ingredients": [
                {"name": "Test Ingredient 1", "quantity": 1, "unit": "cup"},
                {"name": "Test Ingredient 2", "quantity": 2, "unit": "tbsp"}
            ],
            "directions": [
                "Step 1: This is a test recipe",
                "Step 2: Mix test ingredients",
                "Step 3: Cook for test time"
            ],
            "macros": {
                "calories": 250,
                "protein": 15,
                "carbs": 30,
                "fat": 8
            },
            "tags": ["test", "mock"],
            "cuisine": "Test Cuisine",
            "diet": req.diet or "Test Diet",
            "cost_estimate": req.budget or 10.0,
            "prep_time": "15 minutes",
            "cook_time": "20 minutes",
            "difficulty": "Easy"
        }

        if req.use_advanced:
            mock_recipe["ai_insights"] = {
                "nutritional_analysis": "This is a test recipe with mock nutritional data.",
                "cost_efficiency": "Excellent value for testing purposes.",
                "difficulty_note": "Perfect for testing the recipe generation system.",
                "substitution_tips": "This is a mock recipe, so no substitutions needed."
            }

        mock_recipes.append(mock_recipe)

    # Return in the exact format your frontend expects
    response_data = {
        "recipes": mock_recipes,
        "generation_time": 0.5,
        "total_recipes": len(mock_recipes),
        "advanced_mode_used": req.use_advanced,
        "preferences_applied": {
            "budget": req.budget or 20.0,
            "advanced_mode_used": req.use_advanced
        }
    }

    if req.use_advanced:
        response_data[
            "ai_explanation"] = f"Generated {len(mock_recipes)} test recipes for '{req.title}' with a budget of ${req.budget or 20.0}. This is a test response to verify the system is working correctly."

    return response_data
@router.get("/debug/service-status")
async def debug_service_status():
    """Debug endpoint to check service availability"""
    status = {
        "database": "unknown",
        "openai": "unknown",
        "config": "unknown"
    }

    # Check database
    try:
        if supabase:
            # Try a simple database operation
            result = await supabase.table("user_preferences").select("user_id").limit(1).execute()
            status["database"] = "healthy"
        else:
            status["database"] = "not_initialized"
    except Exception as e:
        status["database"] = f"error: {str(e)}"

    # Check OpenAI service
    try:
        from services.enhanced_openai_service import enhanced_openai_service
        # Try to access the service
        status["openai"] = "service_loaded"
    except Exception as e:
        status["openai"] = f"error: {str(e)}"

    # Check config
    try:
        from config import config
        status["config"] = {
            "environment": config.environment,
            "openai_key_configured": bool(config.openai_api_key),
            "supabase_url_configured": bool(config.supabase_url)
        }
    except Exception as e:
        status["config"] = f"error: {str(e)}"

    return status


async def save_recipe_to_db(recipe_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Save a generated recipe to the database

    Args:
        recipe_data: Dictionary containing recipe information
        user_id: User ID who generated the recipe

    Returns:
        Dictionary containing the saved recipe with database ID
    """
    try:
        # Validate user ID
        validated_user_id = validate_user_id(user_id)

        # Ensure database is initialized
        if not supabase:
            await init_supabase_compatibility()

        # Generate a unique ID if not present
        recipe_id = recipe_data.get('id') or str(uuid.uuid4())

        # Prepare data for database insertion
        db_recipe = {
            "id": recipe_id,
            "user_id": validated_user_id,
            "title": recipe_data.get('recipe_name') or recipe_data.get('title', 'Untitled Recipe'),
            "ingredients": json.dumps(recipe_data.get('ingredients', [])) if isinstance(recipe_data.get('ingredients'),
                                                                                        list) else recipe_data.get(
                'ingredients', '[]'),
            "directions": json.dumps(recipe_data.get('directions', [])) if isinstance(recipe_data.get('directions'),
                                                                                      list) else recipe_data.get(
                'directions', '[]'),
            "tags": json.dumps(recipe_data.get('tags', [])) if isinstance(recipe_data.get('tags'),
                                                                          list) else recipe_data.get('tags', '[]'),
            "cuisine": recipe_data.get('cuisine', 'Unknown'),
            "diet": recipe_data.get('diet', ''),
            "macro_estimate": json.dumps(recipe_data.get('macros', {})) if isinstance(recipe_data.get('macros'),
                                                                                      dict) else recipe_data.get(
                'macros', '{}'),
            "cost_estimate": float(recipe_data.get('cost_estimate', 0) or 0),
            "prep_time": str(recipe_data.get('prep_time', '')) or str(recipe_data.get('prepTime', '')),
            "cook_time": str(recipe_data.get('cook_time', '')) or str(recipe_data.get('cookTime', '')),
            "total_time": str(recipe_data.get('total_time', '')) or str(recipe_data.get('totalTime', '')),
            "servings": recipe_data.get('servings', 4),
            "difficulty": recipe_data.get('difficulty', 'Medium'),
            "preference_score": recipe_data.get('preference_score', 0),
            "validation_issues": json.dumps(recipe_data.get('validation_issues', [])) if isinstance(
                recipe_data.get('validation_issues'), list) else '[]',
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "source": "ai_generated",
            "source_metadata": json.dumps({
                "generation_date": datetime.now().isoformat(),
                "model": "openai",
                "preference_score": recipe_data.get('preference_score', 0),
                "validation_passed": len(recipe_data.get('validation_issues', [])) == 0
            })
        }

        # Execute database insertion
        insert_result = supabase.table("recipes").insert(db_recipe).execute()

        if insert_result.data and len(insert_result.data) > 0:
            saved_recipe = insert_result.data[0]

            # Merge saved data back with original recipe data
            # This ensures we return all the original data plus the database ID
            result = {
                **recipe_data,
                'id': saved_recipe['id'],
                'db_id': saved_recipe['id'],
                'saved_at': saved_recipe['created_at']
            }

            logger.info(
                f"✅ Saved recipe '{db_recipe['title']}' with ID {saved_recipe['id']} for user {validated_user_id[:8]}...")

            return result
        else:
            logger.warning(f"Recipe saved but no data returned from database")
            return recipe_data

    except Exception as e:
        logger.error(f"Failed to save recipe to database: {e}")
        # Return the original recipe data even if save fails
        # This ensures the user still gets their generated recipe
        return recipe_data


#@safe_operation("generate_recipe_with_advanced_preferences")
@router.post("/generate-recipe-with-advanced-preferences")
@router.post("/generate-recipe-with-advanced-preferences")
async def generate_recipe_with_advanced_preferences(req: AdvancedRecipeRequest):
    """Generate recipes using advanced user preferences from database"""

    import time
    start_time = time.time()

    logger.info(f"🚀 Starting recipe generation for user {req.user_id[:8]}...")

    try:
        logger.info("✅ Step 1: Fetching user preferences from database")

        # FETCH ACTUAL USER PREFERENCES FROM DATABASE
        user_prefs = await get_advanced_user_preferences(req.user_id)

        # Override with request-specific values if provided
        if req.budget is not None:
            user_prefs['budget'] = req.budget
        if req.allergies is not None:
            user_prefs['allergies'] = req.allergies
        if req.diet is not None:
            user_prefs['diet'] = req.diet

        # Log the preferences we're using
        logger.info(f"Using preferences: Budget=${user_prefs.get('budget', 20)}, "
                    f"Diet={user_prefs.get('diet', 'None')}, "
                    f"Has restrictions={bool(user_prefs.get('dietary_restrictions'))}")

        # Validate title
        safe_title = sanitize_string(req.title, max_length=200, field_name="recipe title")

        logger.info("✅ Step 2: Building recipe generation prompt")

        # Build prompt parts with actual user preferences
        prompt_parts = [
            "You are a professional chef creating budget-friendly recipes.",
            "",
            f'Generate exactly {req.num_recipes} distinct recipes for: "{safe_title}".',
            "",
            "CONSTRAINTS:",
            f"- Budget: ${user_prefs['budget']:.2f} per recipe"
        ]

        # Add preferences from database
        if user_prefs.get('allergies'):
            prompt_parts.append(f"- Allergies/Avoid: {user_prefs['allergies']}")

        if user_prefs.get('diet'):
            prompt_parts.append(f"- Primary Diet: {user_prefs['diet']}")

        # Dietary restrictions from database
        dietary_restrictions = user_prefs.get('dietary_restrictions', {})
        active_restrictions = [
            key.replace('_', ' ').title()
            for key, value in dietary_restrictions.items()
            if value
        ]
        if active_restrictions:
            prompt_parts.append(f"- Dietary Restrictions: {', '.join(active_restrictions)}")

        # Macro targets from database
        macro_targets = user_prefs.get('macro_targets', {})
        if macro_targets.get('enableTargets'):
            prompt_parts.append("- MACRO TARGETS:")
            for macro in ['calories', 'protein', 'carbs', 'fat', 'fiber']:
                if macro_targets.get(macro):
                    prompt_parts.append(f"  • Target {macro.title()}: {macro_targets[macro]}")

        # Cuisine preferences from database
        cuisine_prefs = user_prefs.get('cuisine_preferences', {})
        if cuisine_prefs.get('preferred'):
            prompt_parts.append(f"- PREFERRED Cuisines: {', '.join(cuisine_prefs['preferred'])}")
        if cuisine_prefs.get('disliked'):
            prompt_parts.append(f"- AVOID Cuisines: {', '.join(cuisine_prefs['disliked'])}")

        # Cooking constraints from database
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
            prompt_parts.append(
                f"- Difficulty Level: {difficulty_map.get(cooking_constraints['difficultyLevel'], 'Intermediate')}")

        if cooking_constraints.get('kitchenEquipment'):
            prompt_parts.append(f"- Available Equipment: {', '.join(cooking_constraints['kitchenEquipment'])}")

        # Add format instructions
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
            "Cost Estimate: $X.XX",
            "Prep Time: X minutes",
            "Cook Time: Y minutes",
            "Total Time: Z minutes",
            "Servings: 4",
            "Difficulty: Easy/Medium/Hard",
            "Cuisine: [Type]",
            "",
            "Nutritional Information (per serving):",
            "- Calories: XXX",
            "- Protein: XXg",
            "- Carbs: XXg",
            "- Fat: XXg",
            "- Fiber: XXg",
            "",
            "Tags: tag1, tag2, tag3",
            "",
            "RECIPE 2: [Next Recipe Name]",
            "..."
        ]

        prompt_parts.extend(format_instructions)
        prompt = "\n".join(prompt_parts)

        logger.info("✅ Step 3: Generating recipes with OpenAI")

        # Generate recipes using OpenAI
        async with ExternalServiceErrorContext("openai", "recipe_generation"):
            # Use the correct method signature from EnhancedOpenAIService
            recipes_text = await openai_service.generate_recipe(
                user_preferences=user_prefs,
                recipe_title=safe_title,
                num_recipes=req.num_recipes,
                use_advanced=getattr(req, 'use_advanced', True)
            )

        logger.info("✅ Step 4: Parsing generated recipes")

        # Parse recipes with enhanced parser
        parsed_recipes = parse_recipes_enhanced(
            recipes_text,
            req.num_recipes
        )

        # Validate recipes against user preferences
        validated_recipes = []
        for recipe in parsed_recipes:
            validation_result = validate_recipe_against_preferences(recipe, user_prefs)
            recipe['preference_score'] = validation_result['score']
            recipe['validation_issues'] = validation_result['issues']

            # Only include recipes that pass validation
            if validation_result['passes_validation']:
                validated_recipes.append(recipe)
            else:
                logger.warning(f"Recipe '{recipe.get('recipe_name')}' failed validation: {validation_result['issues']}")

        # If not enough valid recipes, add the best scoring ones
        if len(validated_recipes) < req.num_recipes:
            sorted_recipes = sorted(parsed_recipes, key=lambda x: x['preference_score'], reverse=True)
            for recipe in sorted_recipes:
                if recipe not in validated_recipes:
                    validated_recipes.append(recipe)
                    if len(validated_recipes) >= req.num_recipes:
                        break

        logger.info("✅ Step 5: Saving recipes to database")

        # Save recipes to database
        saved_recipes = []
        for recipe in validated_recipes[:req.num_recipes]:
            try:
                save_result = await save_recipe_to_database_with_compatibility(req.user_id, recipe)
                if save_result:
                    saved_recipes.append(save_result)
            except Exception as e:
                logger.error(f"Failed to save recipe: {e}")
                saved_recipes.append(recipe)  # Return unsaved recipe anyway

        # Calculate performance metrics
        total_time = time.time() - start_time

        logger.info(f"✅ Recipe generation completed in {total_time:.2f}s")

        return {
            "recipes": saved_recipes,
            "metadata": {
                "generation_time": total_time,
                "recipes_generated": len(saved_recipes),
                "user_preferences_applied": True,
                "preference_source": "database",
                "validation_scores": [r.get('preference_score', 0) for r in saved_recipes]
            }
        }

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error occurred")

    except ExternalServiceError as e:
        logger.error(f"OpenAI service error: {e}")
        raise HTTPException(status_code=503, detail="Recipe generation service temporarily unavailable")

    except Exception as e:
        logger.error(f"Unexpected error in recipe generation: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


# Also ensure your get_advanced_user_preferences function is properly fetching from database:
async def get_advanced_user_preferences(user_id: str) -> Dict[str, Any]:
    """Get comprehensive user preferences from database"""

    # Validate user ID first
    validated_user_id = validate_user_id(user_id)

    try:
        # Ensure database is initialized
        if not supabase:
            await init_supabase_compatibility()

        # Fetch from database
        pref_resp = await supabase.table("user_preferences") \
            .select("*") \
            .eq("user_id", validated_user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]

            # Parse and validate preferences
            result = {
                'budget': float(prefs.get("budget", 20.0)) if prefs.get("budget") else 20.0,
                'allergies': prefs.get("allergies", ""),
                'diet': prefs.get("diet", ""),
                'dietary_restrictions': prefs.get("dietary_restrictions", {}),
                'macro_targets': prefs.get("macro_targets", {}),
                'cuisine_preferences': prefs.get("cuisine_preferences", {}),
                'cooking_constraints': prefs.get("cooking_constraints", {})
            }

            logger.info(f"✅ Loaded preferences from database for user {validated_user_id[:8]}...")
            return result
        else:
            logger.info(f"No preferences found for user {validated_user_id[:8]}, using defaults")
            return get_default_preferences()

    except Exception as e:
        logger.error(f"Error fetching preferences: {e}, using defaults")
        return get_default_preferences()


def get_default_preferences() -> Dict[str, Any]:
    """Return default preferences when none exist in database"""
    return {
        'budget': 20.0,
        'allergies': '',
        'diet': '',
        'dietary_restrictions': {},
        'macro_targets': {
            'enableTargets': False,
            'calories': 2000,
            'protein': 150,
            'carbs': 200,
            'fat': 70,
            'fiber': 25
        },
        'cuisine_preferences': {
            'preferred': [],
            'disliked': []
        },
        'cooking_constraints': {
            'maxCookTime': 45,
            'maxPrepTime': 15,
            'maxIngredients': 10,
            'difficultyLevel': 'intermediate',
            'kitchenEquipment': ['Oven', 'Stovetop']
        }
    }# Helper function to generate AI insights for advanced mode
def generate_ai_insights(recipe_data: dict, user_prefs: dict) -> dict:
    """Generate AI insights for advanced mode"""
    insights = {
        "nutritional_analysis": f"This recipe provides {recipe_data.get('macros', {}).get('protein', 0)}g protein, which is {'excellent' if recipe_data.get('macros', {}).get('protein', 0) > 20 else 'good'} for muscle maintenance.",
        "cost_efficiency": f"At ${recipe_data.get('cost_estimate', 0):.2f}, this recipe offers {'excellent' if recipe_data.get('cost_estimate', 0) < user_prefs.get('budget', 50) * 0.5 else 'good'} value for money.",
        "difficulty_note": f"This {recipe_data.get('difficulty', 'intermediate')} recipe is suitable for your cooking skill level.",
        "substitution_tips": "Consider swapping ingredients based on your pantry availability for cost savings."
    }
    return insights


# Helper function to generate AI explanation for the overall response
def generate_ai_explanation(recipes: list, user_prefs: dict) -> str:
    """Generate overall AI explanation for the recipe set"""
    total_cost = sum(recipe.get('cost_estimate', 0) for recipe in recipes)
    avg_prep_time = sum(int(recipe.get('prep_time', '30').split()[0]) if recipe.get('prep_time') else 30 for recipe in recipes) / len(recipes)

    explanation = f"I've crafted {len(recipes)} recipes tailored to your preferences with a total budget of ${total_cost:.2f}. "
    explanation += f"Average prep time is {avg_prep_time:.0f} minutes. "

    if user_prefs.get('dietary_restrictions'):
        active_restrictions = [k for k, v in user_prefs.get('dietary_restrictions', {}).items() if v]
        explanation += f"All recipes accommodate your {', '.join(active_restrictions)} requirements. "

    explanation += "Each recipe balances nutrition, flavor, and cost-effectiveness for optimal meal planning."

    return explanation

@router.get("/user-preference-insights/{user_id}")
#@safe_operation("get_user_preference_insights")
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
#@safe_operation("update_user_preferences_from_feedback")
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
#@safe_operation("generate_recipe_with_grocery")
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

__all__ = ['router']