# nutrition-backend/services/openai_service.py
import asyncio
import openai
from typing import Dict, Any, Optional, List
import logging
from functools import wraps
import time
import json

from config import config
from exceptions import ExternalServiceError, ValidationError

logger = logging.getLogger(__name__)


class OpenAIServiceError(ExternalServiceError):
    """OpenAI-specific service error"""
    pass


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying OpenAI calls on failure"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except openai.RateLimitError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(
                            f"OpenAI rate limit hit, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                    else:
                        raise OpenAIServiceError("OpenAI rate limit exceeded after retries")
                except openai.APITimeoutError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"OpenAI timeout, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                    else:
                        raise OpenAIServiceError("OpenAI service timeout after retries")
                except openai.APIConnectionError as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = delay * (2 ** attempt)
                        logger.warning(
                            f"OpenAI connection error, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(wait_time)
                    else:
                        raise OpenAIServiceError("OpenAI connection failed after retries")
                except Exception as e:
                    # Don't retry on other exceptions
                    logger.error(f"OpenAI service error (no retry): {e}")
                    raise OpenAIServiceError(f"OpenAI service error: {str(e)}")

            # This shouldn't be reached, but just in case
            raise OpenAIServiceError(f"OpenAI service failed after {max_retries} retries: {last_exception}")

        return wrapper

    return decorator


class AsyncOpenAIService:
    """Async OpenAI service with proper error handling and monitoring"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=config.openai_api_key,
            timeout=config.openai_timeout,
            max_retries=0  # We handle retries manually
        )

        # Service statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens_used': 0,
            'total_cost_estimate': 0.0,
            'average_response_time': 0.0
        }

        # Token costs (approximate, as of 2024)
        self.token_costs = {
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002},  # per 1K tokens
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03}
        }

    @retry_on_failure(max_retries=3, delay=1.0)
    async def generate_recipe(self,
                              user_preferences: Dict[str, Any],
                              recipe_title: str,
                              num_recipes: int = 3) -> Optional[str]:
        """Generate recipes with comprehensive user preferences"""

        # Validate inputs
        if not recipe_title or not isinstance(recipe_title, str):
            raise ValidationError("Recipe title is required and must be a string")

        if not 1 <= num_recipes <= 10:
            raise ValidationError("Number of recipes must be between 1 and 10")

        try:
            prompt = self._build_recipe_prompt(user_preferences, recipe_title, num_recipes)

            start_time = time.time()

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional chef and nutritionist. Create detailed, practical recipes that follow food safety guidelines and use realistic ingredients and measurements."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=3000,
                    presence_penalty=0.1,
                    frequency_penalty=0.1
                ),
                timeout=config.openai_timeout
            )

            response_time = time.time() - start_time

            # Update statistics
            self._update_stats(response, response_time, success=True)

            content = response.choices[0].message.content
            if not content:
                raise OpenAIServiceError("OpenAI returned empty response")

            logger.info(f"Recipe generation successful: {len(content)} chars, {response_time:.2f}s")
            return content

        except asyncio.TimeoutError:
            self._update_stats(None, config.openai_timeout, success=False)
            logger.error(f"OpenAI request timed out after {config.openai_timeout}s")
            raise OpenAIServiceError("Recipe generation timed out")
        except openai.AuthenticationError:
            self._update_stats(None, 0, success=False)
            logger.error("OpenAI authentication failed - check API key")
            raise OpenAIServiceError("Authentication failed")
        except openai.BadRequestError as e:
            self._update_stats(None, 0, success=False)
            logger.error(f"OpenAI bad request: {e}")
            raise OpenAIServiceError("Invalid request to AI service")
        except Exception as e:
            self._update_stats(None, 0, success=False)
            logger.error(f"Unexpected error in recipe generation: {e}")
            raise OpenAIServiceError(f"Recipe generation failed: {str(e)}")

    @retry_on_failure(max_retries=3, delay=1.0)
    async def generate_nutrition_advice(self,
                                        user_profile: Dict[str, Any],
                                        specific_goals: List[str] = None) -> Optional[str]:
        """Generate personalized nutrition advice"""

        try:
            prompt = self._build_nutrition_prompt(user_profile, specific_goals)

            start_time = time.time()

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a certified nutritionist and dietitian. Provide evidence-based, safe nutrition advice. Always recommend consulting healthcare professionals for medical conditions."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.5,  # Lower temperature for more consistent advice
                    max_tokens=2000,
                    presence_penalty=0.0,
                    frequency_penalty=0.0
                ),
                timeout=config.openai_timeout
            )

            response_time = time.time() - start_time
            self._update_stats(response, response_time, success=True)

            content = response.choices[0].message.content
            if not content:
                raise OpenAIServiceError("OpenAI returned empty nutrition advice")

            logger.info(f"Nutrition advice generation successful: {response_time:.2f}s")
            return content

        except Exception as e:
            self._update_stats(None, 0, success=False)
            logger.error(f"Error generating nutrition advice: {e}")
            raise OpenAIServiceError(f"Nutrition advice generation failed: {str(e)}")

    @retry_on_failure(max_retries=2, delay=0.5)
    async def generate_recipe_alternatives(self,
                                           original_recipe: str,
                                           alternative_types: List[str]) -> Optional[str]:
        """Generate recipe alternatives (healthier, budget, quick, etc.)"""

        try:
            prompt = self._build_alternatives_prompt(original_recipe, alternative_types)

            start_time = time.time()

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a creative chef specializing in recipe modifications. Create practical alternatives that maintain the essence of the original recipe."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.8,
                    max_tokens=2500
                ),
                timeout=config.openai_timeout
            )

            response_time = time.time() - start_time
            self._update_stats(response, response_time, success=True)

            content = response.choices[0].message.content
            logger.info(f"Recipe alternatives generated: {response_time:.2f}s")
            return content

        except Exception as e:
            self._update_stats(None, 0, success=False)
            logger.error(f"Error generating recipe alternatives: {e}")
            raise OpenAIServiceError(f"Recipe alternatives generation failed: {str(e)}")

    def _build_recipe_prompt(self,
                             user_preferences: Dict[str, Any],
                             recipe_title: str,
                             num_recipes: int) -> str:
        """Build comprehensive recipe generation prompt"""

        prompt_parts = [
            f"Generate exactly {num_recipes} distinct recipes for: '{recipe_title}'",
            "",
            "CONSTRAINTS:"
        ]

        # Budget constraint
        budget = user_preferences.get('budget', 20.0)
        prompt_parts.append(f"• Budget: ${budget:.2f} per recipe maximum")

        # Dietary restrictions
        if user_preferences.get('allergies'):
            prompt_parts.append(f"• Allergies/Avoid: {user_preferences['allergies']}")

        if user_preferences.get('diet'):
            prompt_parts.append(f"• Diet Type: {user_preferences['diet']}")

        # Advanced dietary restrictions
        dietary_restrictions = user_preferences.get('dietary_restrictions', {})
        active_restrictions = [
            key.replace('_', ' ').title()
            for key, value in dietary_restrictions.items()
            if value
        ]
        if active_restrictions:
            prompt_parts.append(f"• Dietary Restrictions: {', '.join(active_restrictions)}")

        # Macro targets
        macro_targets = user_preferences.get('macro_targets', {})
        if macro_targets.get('enableTargets'):
            prompt_parts.append("• NUTRITIONAL TARGETS:")
            if macro_targets.get('calories'):
                prompt_parts.append(f"  - Calories: ~{macro_targets['calories']} per recipe")
            if macro_targets.get('protein'):
                prompt_parts.append(f"  - Protein: ~{macro_targets['protein']}g")
            if macro_targets.get('carbs'):
                prompt_parts.append(f"  - Carbohydrates: ~{macro_targets['carbs']}g")
            if macro_targets.get('fat'):
                prompt_parts.append(f"  - Fat: ~{macro_targets['fat']}g")
            if macro_targets.get('fiber'):
                prompt_parts.append(f"  - Fiber: ~{macro_targets['fiber']}g")

        # Cuisine preferences
        cuisine_prefs = user_preferences.get('cuisine_preferences', {})
        if cuisine_prefs.get('preferred'):
            prompt_parts.append(f"• PREFERRED Cuisines: {', '.join(cuisine_prefs['preferred'])}")
        if cuisine_prefs.get('disliked'):
            prompt_parts.append(f"• AVOID Cuisines: {', '.join(cuisine_prefs['disliked'])}")

        # Cooking constraints
        cooking_constraints = user_preferences.get('cooking_constraints', {})
        if cooking_constraints.get('maxCookTime'):
            prompt_parts.append(f"• Max Cooking Time: {cooking_constraints['maxCookTime']} minutes")
        if cooking_constraints.get('maxPrepTime'):
            prompt_parts.append(f"• Max Prep Time: {cooking_constraints['maxPrepTime']} minutes")
        if cooking_constraints.get('maxIngredients'):
            prompt_parts.append(f"• Max Ingredients: {cooking_constraints['maxIngredients']} items")
        if cooking_constraints.get('difficultyLevel'):
            prompt_parts.append(f"• Difficulty Level: {cooking_constraints['difficultyLevel']}")
        if cooking_constraints.get('kitchenEquipment'):
            prompt_parts.append(f"• Available Equipment: {', '.join(cooking_constraints['kitchenEquipment'])}")

        # Format requirements
        prompt_parts.extend([
            "",
            "FORMAT REQUIREMENTS:",
            "For each recipe, provide exactly this structure:",
            "",
            "RECIPE [NUMBER]: [Recipe Name]",
            "",
            "Ingredients:",
            "• [quantity] [unit] [ingredient name]",
            "",
            "Directions:",
            "1. [Step-by-step instructions]",
            "",
            "Nutrition Facts:",
            "• Calories: [number]",
            "• Protein: [number]g",
            "• Carbs: [number]g",
            "• Fat: [number]g",
            "• Fiber: [number]g",
            "",
            "Prep Time: [number] minutes",
            "Cook Time: [number] minutes",
            "Servings: [number]",
            "Cost Estimate: $[amount]",
            "Difficulty: [Beginner/Intermediate/Advanced]",
            "",
            "Make recipes practical, delicious, and nutritionally balanced."
        ])

        return "\n".join(prompt_parts)

    def _build_nutrition_prompt(self,
                                user_profile: Dict[str, Any],
                                specific_goals: List[str] = None) -> str:
        """Build nutrition advice prompt"""

        prompt_parts = [
            "Provide personalized nutrition advice based on this profile:",
            "",
            f"• Age: {user_profile.get('age', 'Not specified')}",
            f"• Gender: {user_profile.get('gender', 'Not specified')}",
            f"• Height: {user_profile.get('height', 'Not specified')} cm",
            f"• Current Weight: {user_profile.get('current_weight', 'Not specified')} kg",
            f"• Target Weight: {user_profile.get('target_weight', 'Not specified')} kg",
            f"• Activity Level: {user_profile.get('activity_level', 'Not specified')}",
            f"• Primary Goal: {user_profile.get('primary_goal', 'Not specified')}",
        ]

        if user_profile.get('current_injuries'):
            prompt_parts.append(f"• Current Injuries: {', '.join(user_profile['current_injuries'])}")

        if specific_goals:
            prompt_parts.extend([
                "",
                "Specific Goals:",
                *[f"• {goal}" for goal in specific_goals]
            ])

        prompt_parts.extend([
            "",
            "Provide advice on:",
            "1. Daily calorie targets",
            "2. Macronutrient distribution",
            "3. Meal timing recommendations",
            "4. Supplement suggestions (if appropriate)",
            "5. Hydration guidelines",
            "6. Any special considerations",
            "",
            "Keep advice evidence-based and practical. Always recommend consulting healthcare professionals for medical conditions."
        ])

        return "\n".join(prompt_parts)

    def _build_alternatives_prompt(self,
                                   original_recipe: str,
                                   alternative_types: List[str]) -> str:
        """Build recipe alternatives prompt"""

        alternatives_desc = {
            'healthier': 'Lower calories, more nutrients, less processed ingredients',
            'budget': 'Lower cost ingredients while maintaining flavor',
            'quick': 'Faster preparation and cooking time',
            'vegan': 'Plant-based ingredients only',
            'keto': 'Very low carb, high fat',
            'gluten_free': 'No gluten-containing ingredients'
        }

        prompt_parts = [
            "Create alternative versions of this recipe:",
            "",
            original_recipe,
            "",
            "Generate these alternative versions:",
        ]

        for alt_type in alternative_types:
            desc = alternatives_desc.get(alt_type, f"Modified for {alt_type}")
            prompt_parts.append(f"• {alt_type.title()}: {desc}")

        prompt_parts.extend([
            "",
            "For each alternative, provide:",
            "• Recipe name (indicating the modification)",
            "• Complete ingredient list with quantities",
            "• Step-by-step directions",
            "• Brief explanation of changes made",
            "",
            "Maintain the essence and appeal of the original recipe."
        ])

        return "\n".join(prompt_parts)

    def _update_stats(self, response, response_time: float, success: bool):
        """Update service statistics"""
        self.stats['total_requests'] += 1

        if success:
            self.stats['successful_requests'] += 1

            if response and hasattr(response, 'usage'):
                tokens_used = response.usage.total_tokens
                self.stats['total_tokens_used'] += tokens_used

                # Estimate cost (approximate)
                model = "gpt-3.5-turbo"  # Default assumption
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens

                if model in self.token_costs:
                    cost = (
                            (input_tokens / 1000) * self.token_costs[model]['input'] +
                            (output_tokens / 1000) * self.token_costs[model]['output']
                    )
                    self.stats['total_cost_estimate'] += cost

            # Update average response time
            total_successful = self.stats['successful_requests']
            current_avg = self.stats['average_response_time']
            self.stats['average_response_time'] = (
                    (current_avg * (total_successful - 1) + response_time) / total_successful
            )
        else:
            self.stats['failed_requests'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return {
            **self.stats,
            'success_rate': (
                                    self.stats['successful_requests'] / max(self.stats['total_requests'], 1)
                            ) * 100,
            'estimated_monthly_cost': self.stats['total_cost_estimate'] * 30  # Rough estimate
        }

    async def health_check(self) -> Dict[str, Any]:
        """Check if OpenAI service is healthy"""
        try:
            start_time = time.time()

            # Simple test request
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": "Say 'OK' if you can hear me."}],
                    max_tokens=10,
                    temperature=0
                ),
                timeout=10
            )

            response_time = time.time() - start_time

            return {
                'status': 'healthy',
                'response_time': response_time,
                'model_available': True,
                'service_stats': self.get_stats()
            }

        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'model_available': False,
                'service_stats': self.get_stats()
            }


# Global service instance
openai_service = AsyncOpenAIService()


# Convenience functions
async def generate_recipe(user_preferences: Dict[str, Any],
                          recipe_title: str,
                          num_recipes: int = 3) -> Optional[str]:
    """Convenience function for recipe generation"""
    return await openai_service.generate_recipe(user_preferences, recipe_title, num_recipes)


async def generate_nutrition_advice(user_profile: Dict[str, Any],
                                    specific_goals: List[str] = None) -> Optional[str]:
    """Convenience function for nutrition advice"""
    return await openai_service.generate_nutrition_advice(user_profile, specific_goals)


async def generate_recipe_alternatives(original_recipe: str,
                                       alternative_types: List[str]) -> Optional[str]:
    """Convenience function for recipe alternatives"""
    return await openai_service.generate_recipe_alternatives(original_recipe, alternative_types)


# Export all
__all__ = [
    'AsyncOpenAIService', 'OpenAIServiceError', 'openai_service',
    'generate_recipe', 'generate_nutrition_advice', 'generate_recipe_alternatives'
]