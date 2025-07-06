import os
import json
import re
from fractions import Fraction
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict
from models.recipeModels import RecipeRequest, SingleRecipeRequest
from datetime import datetime
from dotenv import load_dotenv
from database import supabase
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize router and OpenAI client
router = APIRouter()
openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None

# Load ingredient prices
ingredient_prices = {}
try:
    with open("/Users/sravankundurthi/NutritionApp/nutrition-backend/Data/ingredient_prices.json") as f:
        ingredient_prices = json.load(f)
except FileNotFoundError:
    ingredient_prices = {}

def get_advanced_user_preferences(user_id: str) -> Dict:
    """Get comprehensive user preferences including advanced dietary restrictions"""
    if not supabase:
        return get_default_preferences()
    
    try:
        pref_resp = supabase.table("user_preferences") \
            .select("*") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        if pref_resp.data and len(pref_resp.data) > 0:
            prefs = pref_resp.data[0]
            
            # Parse advanced preferences with defaults
            result = {
                'budget': float(prefs.get("budget", "20.0").replace('$', '').split('-')[0] or 20.0),
                'allergies': prefs.get("allergies", ""),
                'diet': prefs.get("diet", ""),
                'dietary_restrictions': prefs.get("dietary_restrictions", {}),
                'macro_targets': prefs.get("macro_targets", {}),
                'cuisine_preferences': prefs.get("cuisine_preferences", {"preferred": [], "disliked": []}),
                'cooking_constraints': prefs.get("cooking_constraints", {})
            }
            
            print(f"Loaded advanced preferences for user {user_id}")
            return result
        else:
            return get_default_preferences()
            
    except Exception as e:
        print(f"Error loading advanced preferences: {e}")
        return get_default_preferences()

def get_default_preferences() -> Dict:
    """Return default preferences when none are found"""
    return {
        'budget': 20.0,
        'allergies': "",
        'diet': "",
        'dietary_restrictions': {},
        'macro_targets': {},
        'cuisine_preferences': {"preferred": [], "disliked": []},
        'cooking_constraints': {}
    }

def build_advanced_prompt(title: str, user_prefs: Dict, num_recipes: int = 3) -> str:
    """Build an enhanced prompt using advanced user preferences"""
    
    # Base prompt
    prompt = f"""You are a world class chef that understands flavor, texture, and different cuisines who is exceptional at curating recipes with budget, calories, different cuisines, and macro nutrients.

Generate exactly {num_recipes} distinct recipes for: "{title}".

CONSTRAINTS:
- Budget: ${user_prefs['budget']:.2f} per recipe"""
    
    # Add allergies if specified
    if user_prefs['allergies']:
        prompt += f"\n- Allergies/Avoid: {user_prefs['allergies']}"
    
    # Add primary diet if specified
    if user_prefs['diet']:
        prompt += f"\n- Primary Diet: {user_prefs['diet']}"
    
    # Add dietary restrictions
    dietary_restrictions = user_prefs.get('dietary_restrictions', {})
    active_restrictions = [key.replace('_', ' ').title() for key, value in dietary_restrictions.items() if value]
    if active_restrictions:
        prompt += f"\n- Dietary Restrictions: {', '.join(active_restrictions)}"
    
    # Add macro targets if enabled
    macro_targets = user_prefs.get('macro_targets', {})
    if macro_targets.get('enableTargets'):
        prompt += "\n- MACRO TARGETS:"
        if macro_targets.get('calories'):
            prompt += f"\n  • Target Calories: {macro_targets['calories']} per recipe"
        if macro_targets.get('protein'):
            prompt += f"\n  • Target Protein: {macro_targets['protein']}g"
        if macro_targets.get('carbs'):
            prompt += f"\n  • Target Carbs: {macro_targets['carbs']}g"
        if macro_targets.get('fat'):
            prompt += f"\n  • Target Fat: {macro_targets['fat']}g"
        if macro_targets.get('fiber'):
            prompt += f"\n  • Target Fiber: {macro_targets['fiber']}g"
    
    # Add cuisine preferences
    cuisine_prefs = user_prefs.get('cuisine_preferences', {})
    if cuisine_prefs.get('preferred'):
        prompt += f"\n- PREFERRED Cuisines: {', '.join(cuisine_prefs['preferred'])}"
    if cuisine_prefs.get('disliked'):
        prompt += f"\n- AVOID Cuisines: {', '.join(cuisine_prefs['disliked'])}"
    
    # Add cooking constraints
    cooking_constraints = user_prefs.get('cooking_constraints', {})
    if cooking_constraints.get('maxCookTime'):
        prompt += f"\n- Max Cooking Time: {cooking_constraints['maxCookTime']} minutes"
    if cooking_constraints.get('maxPrepTime'):
        prompt += f"\n- Max Prep Time: {cooking_constraints['maxPrepTime']} minutes"
    if cooking_constraints.get('maxIngredients'):
        prompt += f"\n- Max Ingredients: {cooking_constraints['maxIngredients']} items"
    if cooking_constraints.get('difficultyLevel'):
        difficulty_map = {
            'beginner': 'Beginner (simple techniques)',
            'intermediate': 'Intermediate (moderate techniques)',
            'advanced': 'Advanced (complex techniques)'
        }
        prompt += f"\n- Difficulty Level: {difficulty_map.get(cooking_constraints['difficultyLevel'], cooking_constraints['difficultyLevel'])}"
    if cooking_constraints.get('kitchenEquipment'):
        prompt += f"\n- Available Equipment: {', '.join(cooking_constraints['kitchenEquipment'])}"
    
    # Add format instructions
    prompt += f"""

Format each recipe EXACTLY like this:

RECIPE 1: [Recipe Name]

Ingredients:
- 1 cup ingredient1
- 2 tbsp ingredient2
- 3 pieces ingredient3

Directions:
1. First step
2. Second step
3. Third step

Nutrition Facts:
- Calories: 450
- Protein: 25g
- Carbs: 35g
- Fat: 15g
- Fiber: 5g

Tags: tag1, tag2, tag3
Cuisine: Italian
Diet: Balanced
Prep Time: 15 minutes
Cook Time: 30 minutes
Difficulty: Intermediate
Cost Estimate: $8.50

---

RECIPE 2: [Recipe Name]
[Same format as above]

---

RECIPE 3: [Recipe Name]
[Same format as above]

IMPORTANT NOTES:
- Ensure recipes meet ALL specified constraints and targets
- If macro targets are specified, prioritize hitting those numbers
- Respect all dietary restrictions absolutely
- Stay within the specified time and difficulty constraints
- Use only available kitchen equipment
- Make each recipe unique and flavorful
"""
    
    return prompt.strip()

def validate_recipe_against_preferences(recipe_data: Dict, user_prefs: Dict) -> Dict:
    """Validate and score a recipe against user preferences"""
    validation_score = 100
    issues = []
    
    # Check dietary restrictions
    dietary_restrictions = user_prefs.get('dietary_restrictions', {})
    recipe_text = str(recipe_data).lower()
    
    restriction_checks = {
        'glutenFree': ['wheat', 'flour', 'bread', 'pasta'],
        'dairyFree': ['milk', 'cheese', 'butter', 'cream'],
        'nutFree': ['nuts', 'peanut', 'almond', 'walnut'],
        'vegetarian': ['meat', 'chicken', 'beef', 'pork', 'fish'],
        'vegan': ['meat', 'chicken', 'beef', 'pork', 'fish', 'milk', 'cheese', 'butter', 'egg']
    }
    
    for restriction, forbidden_items in restriction_checks.items():
        if dietary_restrictions.get(restriction):
            for item in forbidden_items:
                if item in recipe_text:
                    validation_score -= 20
                    issues.append(f"Contains {item} (violates {restriction})")
    
    # Check cuisine preferences
    cuisine_prefs = user_prefs.get('cuisine_preferences', {})
    recipe_cuisine = recipe_data.get('cuisine', '').lower()
    
    if cuisine_prefs.get('disliked') and recipe_cuisine in [c.lower() for c in cuisine_prefs['disliked']]:
        validation_score -= 15
        issues.append(f"Uses disliked cuisine: {recipe_cuisine}")
    
    if cuisine_prefs.get('preferred') and recipe_cuisine in [c.lower() for c in cuisine_prefs['preferred']]:
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

def enhance_recipe_with_preferences(recipe_data: Dict, user_prefs: Dict) -> Dict:
    """Enhance recipe data with preference-based metadata"""
    
    # Add preference compliance score
    validation = validate_recipe_against_preferences(recipe_data, user_prefs)
    recipe_data['preference_score'] = validation['score']
    recipe_data['validation_issues'] = validation['issues']
    
    # Add preference tags
    preference_tags = []
    dietary_restrictions = user_prefs.get('dietary_restrictions', {})
    
    for restriction, active in dietary_restrictions.items():
        if active:
            preference_tags.append(restriction.replace('_', '-'))
    
    if preference_tags:
        existing_tags = recipe_data.get('tags', [])
        recipe_data['tags'] = list(set(existing_tags + preference_tags))
    
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
                    actual_val = float(str(actual).replace('g', ''))
                    compliance = 100 - abs((actual_val - target_val) / target_val * 100)
                    macro_compliance[macro] = max(0, min(100, compliance))
                except:
                    macro_compliance[macro] = 0
        
        recipe_data['macro_compliance'] = macro_compliance
    
    return recipe_data

@router.post("/generate-recipe-with-advanced-preferences")
def generate_recipe_with_advanced_preferences(req: RecipeRequest):
    """Generate recipes using advanced user preferences"""
    try:
        if not client:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Get comprehensive user preferences
        user_prefs = get_advanced_user_preferences(req.user_id)
        
        print(f"Generating recipes with advanced preferences for: {req.title}")
        print(f"Active dietary restrictions: {[k for k, v in user_prefs.get('dietary_restrictions', {}).items() if v]}")
        print(f"Preferred cuisines: {user_prefs.get('cuisine_preferences', {}).get('preferred', [])}")
        print(f"Macro targets enabled: {user_prefs.get('macro_targets', {}).get('enableTargets', False)}")

        # Build enhanced prompt
        prompt = build_advanced_prompt(req.title, user_prefs)
        
        print("Calling OpenAI with advanced prompt...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=3000
        )
        content = response.choices[0].message.content

        print("✅ Received OpenAI response, parsing recipes...")

        # Parse recipes using existing logic (simplified for this example)
        raw_recipes = [blk.strip() for blk in content.split("---") if blk.strip()]
        if len(raw_recipes) < 3:
            raw_recipes = re.split(r'(?=RECIPE\s*\d+:)', content)
            raw_recipes = [blk.strip() for blk in raw_recipes if blk.strip()]

        parsed_recipes = []
        for idx, recipe_text in enumerate(raw_recipes[:3]):
            # Parse recipe (using your existing parsing logic)
            recipe_data = parse_single_recipe(recipe_text, idx + 1)
            
            # Enhance with preference data
            recipe_data = enhance_recipe_with_preferences(recipe_data, user_prefs)
            
            # Save to database
            recipe_id = save_recipe_to_database(req.user_id, recipe_data)
            if recipe_id:
                recipe_data["recipe_id"] = recipe_id

            parsed_recipes.append(recipe_data)
            print(f"✅ Generated recipe {idx + 1}: {recipe_data.get('recipe_name')} (Score: {recipe_data.get('preference_score', 0)})")

        # Sort recipes by preference score (highest first)
        parsed_recipes.sort(key=lambda x: x.get('preference_score', 0), reverse=True)

        print(f"🎉 Successfully generated {len(parsed_recipes)} recipes with advanced preferences")
        return {
            "recipes": parsed_recipes,
            "preferences_applied": {
                "dietary_restrictions": len([k for k, v in user_prefs.get('dietary_restrictions', {}).items() if v]),
                "macro_targets_enabled": user_prefs.get('macro_targets', {}).get('enableTargets', False),
                "cuisine_preferences": len(user_prefs.get('cuisine_preferences', {}).get('preferred', [])),
                "cooking_constraints": len([k for k, v in user_prefs.get('cooking_constraints', {}).items() if v])
            }
        }

    except Exception as e:
        print(f"❌ Error in generate_recipe_with_advanced_preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate recipes: {str(e)}")

def parse_single_recipe(recipe_text: str, recipe_number: int) -> Dict:
    """Parse a single recipe from OpenAI response text"""
    
    # Extract recipe name
    recipe_name_match = re.search(r'RECIPE\s*\d*:?\s*(.+)', recipe_text)
    recipe_name = recipe_name_match.group(1).strip() if recipe_name_match else f"Recipe {recipe_number}"

    # Parse ingredients
    parsed_ingredients = []
    ingredients_match = re.search(r'Ingredients:\s*\n(.*?)(?=\n\s*Directions:|\n\s*Nutrition|\Z)', recipe_text,
                                  re.DOTALL | re.IGNORECASE)

    if ingredients_match:
        ingredients_text = ingredients_match.group(1)
        for line in ingredients_text.strip().split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith('*')):
                line = re.sub(r'^[-•*]\s*', '', line).strip()
                parts = line.split(' ', 2)
                
                if len(parts) >= 2:
                    try:
                        quantity_str = parts[0]
                        quantity = float(Fraction(quantity_str))
                        if len(parts) == 3:
                            unit, name = parts[1], parts[2]
                        else:
                            unit, name = "", parts[1]
                    except:
                        quantity = 1.0
                        unit, name = parts[0], ' '.join(parts[1:])
                else:
                    quantity, unit, name = 1.0, "", line

                parsed_ingredients.append({
                    "name": name.strip().lower(),
                    "unit": unit.strip(),
                    "quantity": quantity
                })

    # Parse directions
    parsed_directions = []
    directions_match = re.search(r'Directions:\s*\n(.*?)(?=\n\s*Nutrition|\n\s*Tags:|\Z)', recipe_text,
                                 re.DOTALL | re.IGNORECASE)

    if directions_match:
        directions_text = directions_match.group(1)
        for line in directions_text.strip().split('\n'):
            line = line.strip()
            if line and (re.match(r'^\d+\.', line) or line.startswith('-')):
                line = re.sub(r'^\d+\.\s*', '', line)
                line = re.sub(r'^[-•*]\s*', '', line)
                if line.strip():
                    parsed_directions.append(line.strip())

    # Parse nutrition macros
    macros = {"calories": 0.0, "protein": "0g", "carbs": "0g", "fat": "0g", "fiber": "0g"}
    nutrition_match = re.search(r'Nutrition Facts:\s*\n(.*?)(?=\n\s*Tags:|\n\s*Cuisine:|\Z)', recipe_text,
                                re.DOTALL | re.IGNORECASE)

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
                        macros['calories'] = float(re.search(r'([\d.]+)', value).group(1))
                    except:
                        macros['calories'] = 0.0
                elif key in ['protein', 'carbs', 'fat', 'fiber']:
                    macros[key] = value

    # Parse additional metadata
    tags = []
    tag_match = re.search(r'Tags:\s*(.+)', recipe_text, re.IGNORECASE)
    if tag_match:
        raw_tags = tag_match.group(1)
        tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]

    cuisine = "Unknown"
    cuisine_match = re.search(r'Cuisine:\s*(.+)', recipe_text, re.IGNORECASE)
    if cuisine_match:
        cuisine = cuisine_match.group(1).strip()

    diet = "Unknown"
    diet_match = re.search(r'Diet:\s*(.+)', recipe_text, re.IGNORECASE)
    if diet_match:
        diet = diet_match.group(1).strip()

    # Parse time information
    prep_time = ""
    prep_match = re.search(r'Prep Time:\s*(.+)', recipe_text, re.IGNORECASE)
    if prep_match:
        prep_time = prep_match.group(1).strip()

    cook_time = ""
    cook_match = re.search(r'Cook Time:\s*(.+)', recipe_text, re.IGNORECASE)
    if cook_match:
        cook_time = cook_match.group(1).strip()

    difficulty = ""
    difficulty_match = re.search(r'Difficulty:\s*(.+)', recipe_text, re.IGNORECASE)
    if difficulty_match:
        difficulty = difficulty_match.group(1).strip()

    # Parse cost estimate
    cost_estimate = 0.0
    cost_match = re.search(r'Cost Estimate:\s*\$?([\d.]+)', recipe_text)
    if cost_match:
        cost_estimate = float(cost_match.group(1))
    else:
        cost_estimate = round(
            sum(ingredient_prices.get(i["name"], 1.00) * i["quantity"]
                for i in parsed_ingredients),
            2
        )

    # Build grocery list
    grocery_list = estimate_grocery_list(parsed_ingredients)

    return {
        "recipe_text": recipe_text,
        "recipe_name": recipe_name,
        "ingredients": parsed_ingredients,
        "directions": parsed_directions,
        "macros": macros,
        "tags": tags,
        "cuisine": cuisine,
        "diet": diet,
        "prep_time": prep_time,
        "cook_time": cook_time,
        "difficulty": difficulty,
        "cost_estimate": round(cost_estimate, 2),
        "grocery_list": grocery_list
    }

def estimate_grocery_list(ingredients: List[Dict]) -> List[Dict]:
    """Estimate grocery list with costs"""
    fallback_price = 1.00
    grocery_list = []
    for item in ingredients:
        name = item.get("name", "").lower()
        quantity = item.get("quantity", 1)
        unit_price = ingredient_prices.get(name, fallback_price)
        estimated_cost = round(unit_price * quantity, 2)
        grocery_list.append({
            "item": name,
            "quantity": quantity,
            "estimated_cost": estimated_cost
        })
    return grocery_list

def save_recipe_to_database(user_id: str, recipe_data: Dict):
    """Save recipe to Supabase database with enhanced metadata"""
    if not supabase:
        print("Supabase not available, skipping recipe save")
        return None
        
    try:
        insert_result = supabase.table("recipes").insert({
            "user_id": user_id,
            "title": recipe_data["recipe_name"],
            "ingredients": recipe_data["ingredients"],
            "directions": recipe_data["directions"],
            "tags": recipe_data["tags"],
            "cuisine": recipe_data["cuisine"],
            "diet": recipe_data["diet"],
            "macro_estimate": recipe_data["macros"],
            "cost_estimate": recipe_data["cost_estimate"],
            "prep_time": recipe_data.get("prep_time", ""),
            "cook_time": recipe_data.get("cook_time", ""),
            "difficulty": recipe_data.get("difficulty", ""),
            "preference_score": recipe_data.get("preference_score", 0),
            "validation_issues": recipe_data.get("validation_issues", []),
            "macro_compliance": recipe_data.get("macro_compliance", {})
        }).execute()

        if insert_result.data and len(insert_result.data) > 0:
            recipe_id = insert_result.data[0]["id"]
            print(f"✅ Saved recipe '{recipe_data['recipe_name']}' to database with ID: {recipe_id}")
            return recipe_id
        else:
            print("⚠️ Recipe insert returned no data")
            return None
            
    except Exception as e:
        print(f"❌ Error saving recipe to database: {e}")
        return None

@router.get("/user-preference-insights/{user_id}")
def get_user_preference_insights(user_id: str):
    """Get insights about user's preference usage and compliance"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get user's recipes with preference scores
        recipes_result = supabase.table("recipes") \
            .select("preference_score, macro_compliance, validation_issues, cuisine, tags") \
            .eq("user_id", user_id) \
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

        # Calculate insights
        total_recipes = len(recipes)
        avg_score = sum(r.get("preference_score", 0) for r in recipes) / total_recipes

        # Cuisine compliance analysis
        cuisine_scores = {}
        for recipe in recipes:
            cuisine = recipe.get("cuisine", "Unknown")
            score = recipe.get("preference_score", 0)
            if cuisine not in cuisine_scores:
                cuisine_scores[cuisine] = []
            cuisine_scores[cuisine].append(score)

        top_cuisines = [
            {"cuisine": cuisine, "avg_score": sum(scores) / len(scores)}
            for cuisine, scores in cuisine_scores.items()
        ]
        top_cuisines.sort(key=lambda x: x["avg_score"], reverse=True)

        # Common validation issues
        all_issues = []
        for recipe in recipes:
            issues = recipe.get("validation_issues", [])
            all_issues.extend(issues)

        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

        common_issues = [
            {"issue": issue, "count": count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        ]

        # Macro compliance averages
        macro_compliance_totals = {}
        macro_count = 0
        
        for recipe in recipes:
            compliance = recipe.get("macro_compliance", {})
            if compliance:
                macro_count += 1
                for macro, score in compliance.items():
                    if macro not in macro_compliance_totals:
                        macro_compliance_totals[macro] = []
                    macro_compliance_totals[macro].append(score)

        macro_compliance_avg = {}
        for macro, scores in macro_compliance_totals.items():
            macro_compliance_avg[macro] = sum(scores) / len(scores) if scores else 0

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

    except Exception as e:
        print(f"❌ Error getting preference insights: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")

@router.patch("/update-user-preferences/{user_id}")
def update_user_preferences_from_feedback(user_id: str, feedback_data: Dict):
    """Update user preferences based on recipe feedback and ratings"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        # Get current preferences
        current_prefs = get_advanced_user_preferences(user_id)
        
        # Update preferences based on feedback
        # This is a simplified example - you could make this much more sophisticated
        
        recipe_rating = feedback_data.get("rating", 0)
        recipe_cuisine = feedback_data.get("cuisine", "")
        feedback_reason = feedback_data.get("feedback_reason", "")
        
        # Adjust cuisine preferences based on ratings
        if recipe_rating >= 4 and recipe_cuisine:
            # Add to preferred if not already there
            preferred_cuisines = current_prefs.get("cuisine_preferences", {}).get("preferred", [])
            if recipe_cuisine not in preferred_cuisines:
                preferred_cuisines.append(recipe_cuisine)
                current_prefs["cuisine_preferences"]["preferred"] = preferred_cuisines
        
        elif recipe_rating <= 2 and recipe_cuisine:
            # Add to disliked if feedback indicates cuisine issues
            if "cuisine" in feedback_reason.lower():
                disliked_cuisines = current_prefs.get("cuisine_preferences", {}).get("disliked", [])
                if recipe_cuisine not in disliked_cuisines:
                    disliked_cuisines.append(recipe_cuisine)
                    current_prefs["cuisine_preferences"]["disliked"] = disliked_cuisines

        # Update preferences in database
        update_result = supabase.table("user_preferences") \
            .update(current_prefs) \
            .eq("user_id", user_id) \
            .execute()

        print(f"✅ Updated preferences for user {user_id} based on feedback")
        
        return {
            "success": True,
            "message": "Preferences updated based on feedback",
            "updated_preferences": current_prefs
        }

    except Exception as e:
        print(f"❌ Error updating preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update preferences: {str(e)}")

# Update the existing endpoint to use advanced preferences
@router.post("/generate-recipe-with-grocery")
def generate_recipe_with_grocery(req: RecipeRequest):
    """Updated to use advanced preferences - maintains backward compatibility"""
    return generate_recipe_with_advanced_preferences(req)