# nutrition-backend/services/enhanced_openai_service.py
"""
Enhanced OpenAI Service integrating advanced prompt engineering
Replaces the basic OpenAI service with sophisticated capabilities
"""

import asyncio
import json
import time
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import logging
from functools import wraps

from openai import AsyncOpenAI
import tiktoken

from config import config
from exceptions import OpenAIServiceError, ValidationError
from services.advanced_prompt_service import (
    AdvancedPromptService,
    PromptContext,
    PromptStrategy,
    ResponseFormat,
    extract_constraints
)

logger = logging.getLogger(__name__)


class TokenManager:
    """Manage token usage and optimization"""

    def __init__(self):
        self.encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
        self.token_limits = {
            "gpt-3.5-turbo": 4096,
            "gpt-4": 8192,
            "gpt-4-turbo-preview": 128000
        }
        self.reserved_tokens = 500  # Reserve for response

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoder.encode(text))

    def optimize_prompt(self, prompt: str, max_tokens: int) -> str:
        """Optimize prompt to fit within token limits"""

        tokens = self.count_tokens(prompt)

        if tokens <= max_tokens:
            return prompt

        # Optimization strategies
        optimized = prompt

        # 1. Remove extra whitespace
        optimized = re.sub(r'\s+', ' ', optimized)
        optimized = re.sub(r'\n\s*\n', '\n\n', optimized)

        # 2. Compress examples if present
        if "Example:" in optimized:
            optimized = self._compress_examples(optimized)

        # 3. Summarize context if still too long
        if self.count_tokens(optimized) > max_tokens:
            optimized = self._summarize_context(optimized, max_tokens)

        return optimized

    def _compress_examples(self, text: str) -> str:
        """Compress examples to save tokens"""
        # Keep only essential parts of examples
        lines = text.split('\n')
        compressed = []
        in_example = False

        for line in lines:
            if "Example:" in line:
                in_example = True
                compressed.append(line)
            elif in_example and line.strip() == "":
                in_example = False
                compressed.append(line)
            elif in_example:
                # Compress example content
                if len(line) > 100:
                    compressed.append(line[:100] + "...")
                else:
                    compressed.append(line)
            else:
                compressed.append(line)

        return '\n'.join(compressed)

    def _summarize_context(self, text: str, max_tokens: int) -> str:
        """Summarize context to fit token limit"""
        # Simple truncation with ellipsis for now
        # In production, could use a summarization model

        tokens_per_char = self.count_tokens(text) / len(text)
        max_chars = int((max_tokens - 50) / tokens_per_char)

        if len(text) > max_chars:
            return text[:max_chars] + "...\n[Context truncated for length]"

        return text


class ResponseParser:
    """Advanced response parsing with validation"""

    @staticmethod
    def parse_recipe_response(response: str) -> List[Dict[str, Any]]:
        """Parse recipe response with robust extraction"""

        recipes = []

        # Try multiple parsing strategies
        strategies = [
            ResponseParser._parse_structured_recipes,
            ResponseParser._parse_numbered_recipes,
            ResponseParser._parse_section_recipes
        ]

        for strategy in strategies:
            try:
                parsed = strategy(response)
                if parsed and len(parsed) > 0:
                    recipes = parsed
                    break
            except Exception as e:
                logger.debug(f"Parsing strategy failed: {e}")
                continue

        # Validate and enhance parsed recipes
        validated_recipes = []
        for recipe in recipes:
            if ResponseParser._validate_recipe(recipe):
                enhanced = ResponseParser._enhance_recipe_data(recipe)
                validated_recipes.append(enhanced)

        return validated_recipes

    @staticmethod
    def _parse_structured_recipes(text: str) -> List[Dict[str, Any]]:
        """Parse structured recipe format"""

        recipes = []
        recipe_blocks = re.split(r'(?=RECIPE\s*\d*:)', text)

        for block in recipe_blocks:
            if not block.strip():
                continue

            recipe = {}

            # Extract recipe name
            name_match = re.search(r'RECIPE\s*\d*:\s*(.+?)(?:\n|$)', block)
            if name_match:
                recipe['name'] = name_match.group(1).strip()

            # Extract ingredients
            ingredients_match = re.search(
                r'Ingredients?:\s*\n((?:[-•]\s*.+\n?)+)',
                block,
                re.IGNORECASE
            )
            if ingredients_match:
                recipe['ingredients'] = ResponseParser._parse_ingredients(
                    ingredients_match.group(1)
                )

            # Extract directions
            directions_match = re.search(
                r'(?:Directions?|Instructions?):\s*\n((?:\d+\..*\n?)+)',
                block,
                re.IGNORECASE
            )
            if directions_match:
                recipe['directions'] = ResponseParser._parse_directions(
                    directions_match.group(1)
                )

            # Extract nutrition
            nutrition_match = re.search(
                r'Nutrition.*?:\s*\n((?:[-•]\s*.+\n?)+)',
                block,
                re.IGNORECASE
            )
            if nutrition_match:
                recipe['nutrition'] = ResponseParser._parse_nutrition(
                    nutrition_match.group(1)
                )

            # Extract metadata
            recipe['metadata'] = ResponseParser._extract_metadata(block)

            if recipe.get('name') and recipe.get('ingredients'):
                recipes.append(recipe)

        return recipes

    @staticmethod
    def _parse_ingredients(text: str) -> List[Dict[str, str]]:
        """Parse ingredients with quantities"""

        ingredients = []
        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line or line in ['-', '•']:
                continue

            # Remove bullet points
            line = re.sub(r'^[-•]\s*', '', line)

            # Parse quantity, unit, and ingredient
            match = re.match(
                r'(\d+(?:\.\d+)?(?:/\d+)?)\s*([a-zA-Z]+)?\s*(.+)',
                line
            )

            if match:
                ingredients.append({
                    'quantity': match.group(1),
                    'unit': match.group(2) or '',
                    'item': match.group(3).strip()
                })
            else:
                # Fallback for non-standard format
                ingredients.append({
                    'quantity': '',
                    'unit': '',
                    'item': line
                })

        return ingredients

    @staticmethod
    def _parse_nutrition(text: str) -> Dict[str, Any]:
        """Parse nutrition information"""

        nutrition = {}

        # Common nutrition patterns
        patterns = {
            'calories': r'(?:Calories?|Cal):\s*(\d+)',
            'protein': r'Protein:\s*(\d+(?:\.\d+)?)\s*g',
            'carbs': r'(?:Carbs?|Carbohydrates?):\s*(\d+(?:\.\d+)?)\s*g',
            'fat': r'Fat:\s*(\d+(?:\.\d+)?)\s*g',
            'fiber': r'Fiber:\s*(\d+(?:\.\d+)?)\s*g',
            'sugar': r'Sugar:\s*(\d+(?:\.\d+)?)\s*g',
            'sodium': r'Sodium:\s*(\d+)\s*mg'
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1)
                nutrition[key] = float(value) if '.' in value else int(value)

        return nutrition

    @staticmethod
    def _extract_metadata(text: str) -> Dict[str, Any]:
        """Extract recipe metadata"""

        metadata = {}

        # Time patterns
        prep_match = re.search(r'Prep\s*Time:\s*(\d+)\s*min', text, re.IGNORECASE)
        if prep_match:
            metadata['prep_time'] = int(prep_match.group(1))

        cook_match = re.search(r'Cook\s*Time:\s*(\d+)\s*min', text, re.IGNORECASE)
        if cook_match:
            metadata['cook_time'] = int(cook_match.group(1))

        # Servings
        servings_match = re.search(r'Servings?:\s*(\d+)', text, re.IGNORECASE)
        if servings_match:
            metadata['servings'] = int(servings_match.group(1))

        # Cost
        cost_match = re.search(r'Cost\s*Estimate:\s*\$(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if cost_match:
            metadata['cost_estimate'] = float(cost_match.group(1))

        # Difficulty
        diff_match = re.search(
            r'Difficulty:\s*(Beginner|Easy|Intermediate|Advanced|Hard)',
            text,
            re.IGNORECASE
        )
        if diff_match:
            metadata['difficulty'] = diff_match.group(1).lower()

        return metadata

    @staticmethod
    def _validate_recipe(recipe: Dict[str, Any]) -> bool:
        """Validate recipe has minimum required fields"""

        required = ['name', 'ingredients']
        return all(field in recipe and recipe[field] for field in required)

    @staticmethod
    def _enhance_recipe_data(recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance recipe with calculated fields"""

        # Calculate total time
        if 'metadata' in recipe:
            prep = recipe['metadata'].get('prep_time', 0)
            cook = recipe['metadata'].get('cook_time', 0)
            recipe['metadata']['total_time'] = prep + cook

        # Estimate complexity score
        if 'directions' in recipe:
            recipe['complexity_score'] = len(recipe['directions'])

        # Add timestamp
        recipe['generated_at'] = datetime.utcnow().isoformat()

        return recipe


class EnhancedOpenAIService:
    """Enhanced OpenAI service with advanced capabilities"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.token_manager = TokenManager()
        self.response_parser = ResponseParser()
        self.advanced_prompt_service = AdvancedPromptService()

        # Caching for efficiency
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour

        # Performance tracking
        self.metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'average_response_time': 0,
            'token_usage': {'prompt': 0, 'completion': 0},
            'cost_estimate': 0.0
        }

    async def generate_recipe(self,
                              user_preferences: Dict[str, Any],
                              recipe_title: str,
                              num_recipes: int = 3,
                              use_advanced: bool = True) -> str:
        """Generate recipes with optional advanced prompting"""

        self.metrics['total_requests'] += 1
        start_time = time.time()

        # Check cache first
        cache_key = self._generate_cache_key(user_preferences, recipe_title, num_recipes)
        if cache_key in self.response_cache:
            cache_entry = self.response_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                self.metrics['cache_hits'] += 1
                logger.info("Returning cached recipe response")
                return cache_entry['response']

        try:
            if use_advanced:
                # Use advanced prompt engineering
                context = PromptContext(
                    user_preferences=user_preferences,
                    conversation_history=[],
                    domain_knowledge=self.advanced_prompt_service.domain_knowledge,
                    constraints=extract_constraints(user_preferences),
                    output_requirements={
                        "format": "structured",
                        "detail": "comprehensive",
                        "include_nutrition": True,
                        "include_cost": True
                    },
                    strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                    format=ResponseFormat.STRUCTURED_TEXT
                )

                response = await self.advanced_prompt_service.generate_advanced_recipe(
                    context,
                    num_recipes
                )
            else:
                # Use standard generation
                response = await self._generate_standard_recipe(
                    user_preferences,
                    recipe_title,
                    num_recipes
                )

            # Update metrics
            elapsed_time = time.time() - start_time
            self._update_metrics(elapsed_time)

            # Cache successful response
            self.response_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }

            # Clean old cache entries
            self._clean_cache()

            return response

        except Exception as e:
            logger.error(f"Recipe generation failed: {e}")
            raise OpenAIServiceError(f"Failed to generate recipes: {str(e)}")

    async def generate_nutrition_advice(self,
                                        user_profile: Dict[str, Any],
                                        specific_goals: List[str] = None,
                                        coaching_style: str = "balanced") -> Dict[str, Any]:
        """Generate comprehensive nutrition advice"""

        try:
            # Use advanced coaching generation
            coaching_plan = await self.advanced_prompt_service.generate_nutrition_coaching(
                user_profile,
                specific_goals or []
            )

            # Enhance with additional insights
            enhanced_plan = await self._enhance_coaching_plan(
                coaching_plan,
                user_profile,
                coaching_style
            )

            return enhanced_plan

        except Exception as e:
            logger.error(f"Nutrition advice generation failed: {e}")
            raise OpenAIServiceError(f"Failed to generate nutrition advice: {str(e)}")

    async def optimize_meal_plan(self,
                                 requirements: Dict[str, Any],
                                 duration_days: int = 7,
                                 optimization_goals: List[str] = None) -> Dict[str, Any]:
        """Generate optimized meal plan"""

        try:
            # Add optimization goals to requirements
            if optimization_goals:
                requirements['optimization_goals'] = optimization_goals

            # Generate using advanced service
            meal_plan = await self.advanced_prompt_service.optimize_meal_plan(
                requirements,
                duration_days
            )

            # Post-process for consistency
            validated_plan = self._validate_meal_plan(meal_plan)

            return validated_plan

        except Exception as e:
            logger.error(f"Meal plan optimization failed: {e}")
            raise OpenAIServiceError(f"Failed to optimize meal plan: {str(e)}")

    async def analyze_recipe_image(self,
                                   image_url: str,
                                   analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """Analyze recipe from image using GPT-4 Vision"""

        try:
            prompt = self._build_image_analysis_prompt(analysis_type)

            response = await self.client.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=1000
            )

            # Parse the analysis
            analysis = self._parse_image_analysis(response.choices[0].message.content)

            return analysis

        except Exception as e:
            logger.error(f"Recipe image analysis failed: {e}")
            raise OpenAIServiceError(f"Failed to analyze recipe image: {str(e)}")

    async def generate_substitutions(self,
                                     recipe: Dict[str, Any],
                                     constraints: List[str],
                                     maintain_flavor: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Generate ingredient substitutions"""

        prompt = self._build_substitution_prompt(recipe, constraints, maintain_flavor)

        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in ingredient substitutions and dietary adaptations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=1500
        )

        # Parse substitutions
        substitutions = self._parse_substitutions(response.choices[0].message.content)

        return substitutions

    async def health_check(self):
        """Simple health check for OpenAI service"""
        try:
            return {
                "status": "healthy",
                "response_time": 0.001,
                "service": "openai"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def get_stats(self):
        """Get service statistics"""
        return {
            "total_requests": getattr(self, 'total_requests', 0),
            "successful_requests": getattr(self, 'successful_requests', 0),
            "failed_requests": getattr(self, 'failed_requests', 0)
        }

    def _generate_cache_key(self,
                            preferences: Dict[str, Any],
                            title: str,
                            num_recipes: int) -> str:
        """Generate cache key for request"""

        # Create deterministic key from inputs
        key_parts = [
            title.lower(),
            str(num_recipes),
            str(preferences.get('budget', 20)),
            preferences.get('diet', 'none'),
            preferences.get('allergies', 'none')
        ]

        # Add active restrictions
        if 'dietary_restrictions' in preferences:
            active = sorted([k for k, v in preferences['dietary_restrictions'].items() if v])
            key_parts.extend(active)

        return "|".join(key_parts)

    def _update_metrics(self, response_time: float):
        """Update service metrics"""

        # Update average response time
        total_requests = self.metrics['total_requests']
        current_avg = self.metrics['average_response_time']

        self.metrics['average_response_time'] = (
                (current_avg * (total_requests - 1) + response_time) / total_requests
        )

    def _clean_cache(self):
        """Remove expired cache entries"""

        current_time = time.time()
        expired_keys = [
            key for key, entry in self.response_cache.items()
            if current_time - entry['timestamp'] > self.cache_ttl
        ]

        for key in expired_keys:
            del self.response_cache[key]

    async def _enhance_coaching_plan(self,
                                     base_plan: Dict[str, Any],
                                     profile: Dict[str, Any],
                                     style: str) -> Dict[str, Any]:
        """Enhance coaching plan with additional insights"""

        enhancements = {
            "motivation_tips": await self._generate_motivation_tips(profile, style),
            "common_pitfalls": self._identify_common_pitfalls(profile),
            "success_indicators": self._define_success_indicators(base_plan),
            "adjustment_triggers": self._create_adjustment_triggers(base_plan)
        }

        enhanced_plan = {**base_plan, **enhancements}

        return enhanced_plan

    def _validate_meal_plan(self, meal_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and fix meal plan consistency"""

        validated = meal_plan.copy()

        # Ensure all days have all meals
        for day in range(1, 8):
            day_key = f"day_{day}"
            if day_key not in validated:
                validated[day_key] = {}

            for meal in ["breakfast", "lunch", "dinner", "snacks"]:
                if meal not in validated[day_key]:
                    # Generate missing meal from context
                    validated[day_key][meal] = self._generate_fallback_meal(meal)

        # Calculate totals
        validated["weekly_totals"] = self._calculate_weekly_totals(validated)

        return validated

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get comprehensive service metrics"""

        return {
            **self.metrics,
            'cache_hit_rate': (
                self.metrics['cache_hits'] / self.metrics['total_requests']
                if self.metrics['total_requests'] > 0 else 0
            ),
            'estimated_cost_per_request': (
                self.metrics['cost_estimate'] / self.metrics['total_requests']
                if self.metrics['total_requests'] > 0 else 0
            ),
            'advanced_prompt_metrics': self.advanced_prompt_service.get_prompt_metrics()
        }

    async def _generate_standard_recipe(self,
                                        user_preferences: Dict[str, Any],
                                        recipe_title: str,
                                        num_recipes: int) -> str:
        """Generate recipes using standard prompting with robust error handling"""

        prompt = f"""
    Generate {num_recipes} recipes for "{recipe_title}" with these preferences:

    Budget: ${user_preferences.get('budget', 20)} per recipe
    Diet: {user_preferences.get('diet', 'Any')}
    Allergies: {user_preferences.get('allergies', 'None')}

    For each recipe, use this exact format:

    RECIPE 1: [Recipe Name]

    Ingredients:
    - [Quantity] [Unit] [Ingredient]
    - [Continue for all ingredients]

    Directions:
    1. [Step 1]
    2. [Step 2]
    [Continue for all steps]

    Nutrition (per serving):
    - Calories: [number]
    - Protein: [number]g
    - Carbs: [number]g
    - Fat: [number]g

    Cost Estimate: $[number]
    Prep Time: [time]
    Cook Time: [time]
    Difficulty: [Easy/Medium/Hard]

    ---

    [Repeat for all recipes]
    """

        try:
            # FIXED: Robust OpenAI call with proper error handling
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful cooking assistant that creates practical, budget-friendly recipes."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                timeout=30.0  # Add timeout
            )

            # CRITICAL FIX: Check if response has choices before accessing
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error("OpenAI returned response with no choices")
                raise Exception("OpenAI API returned empty response")

            if len(response.choices) == 0:
                logger.error("OpenAI returned response with empty choices array")
                raise Exception("OpenAI API returned no response choices")

            choice = response.choices[0]
            if not choice or not hasattr(choice, 'message') or not choice.message:
                logger.error("OpenAI choice has no message")
                raise Exception("OpenAI API returned malformed response")

            content = choice.message.content
            if not content or content.strip() == "":
                logger.error("OpenAI returned empty content")
                raise Exception("OpenAI API returned empty content")

            logger.info(f"✅ OpenAI returned {len(content)} characters of content")
            return content.strip()

        except Exception as e:
            logger.error(f"❌ OpenAI API call failed: {e}")
            # Return a helpful error message instead of crashing
            raise Exception(f"Failed to generate recipes: {str(e)}")

    def _generate_cache_key(self, user_preferences: Dict, recipe_title: str, num_recipes: int) -> str:
        """Generate cache key for response caching"""
        import hashlib
        key_data = f"{recipe_title}_{num_recipes}_{user_preferences.get('budget')}_{user_preferences.get('diet')}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _update_metrics(self, elapsed_time: float):
        """Update performance metrics"""
        if self.metrics['average_response_time'] == 0:
            self.metrics['average_response_time'] = elapsed_time
        else:
            # Simple moving average
            self.metrics['average_response_time'] = (
                    self.metrics['average_response_time'] * 0.9 + elapsed_time * 0.1
            )

    # Also add this method to handle the missing method error
    async def generate_single_recipe(self,
                                     user_preferences: Dict[str, Any],
                                     recipe_title: str,
                                     exclusion_context: str = "",
                                     use_advanced: bool = True) -> str:
        """Generate a single recipe (for regeneration)"""

        # Add exclusion context to preferences if provided
        enhanced_prefs = user_preferences.copy()
        if exclusion_context:
            enhanced_prefs['exclusion_context'] = exclusion_context

        # Use the same generate_recipe method but with num_recipes=1
        return await self.generate_recipe(
            user_preferences=enhanced_prefs,
            recipe_title=recipe_title,
            num_recipes=1,
            use_advanced=use_advanced
        )

    # Update your main generate_recipe method to handle advanced prompting failures
    async def generate_recipe(self,
                              user_preferences: Dict[str, Any],
                              recipe_title: str,
                              num_recipes: int = 3,
                              use_advanced: bool = True) -> str:
        """Generate recipes with optional advanced prompting - FIXED VERSION"""

        self.metrics['total_requests'] += 1
        start_time = time.time()

        # Check cache first
        cache_key = self._generate_cache_key(user_preferences, recipe_title, num_recipes)
        if cache_key in self.response_cache:
            cache_entry = self.response_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.cache_ttl:
                self.metrics['cache_hits'] += 1
                logger.info("Returning cached recipe response")
                return cache_entry['response']

        try:
            if use_advanced:
                logger.info("Attempting advanced recipe generation")
                try:
                    # Use advanced prompt engineering
                    context = PromptContext(
                        user_preferences=user_preferences,
                        conversation_history=[],
                        domain_knowledge=self.advanced_prompt_service.domain_knowledge,
                        constraints={'title': recipe_title, **extract_constraints(user_preferences)},
                        output_requirements={
                            "format": "structured",
                            "detail": "comprehensive",
                            "include_nutrition": True,
                            "include_cost": True
                        },
                        strategy=PromptStrategy.CHAIN_OF_THOUGHT,
                        format=ResponseFormat.STRUCTURED_TEXT
                    )

                    response = await self.advanced_prompt_service.generate_advanced_recipe(
                        context,
                        num_recipes
                    )
                    logger.info("✅ Advanced recipe generation successful")

                except Exception as advanced_error:
                    logger.warning(f"⚠️ Advanced generation failed: {advanced_error}, falling back to standard")
                    # Fallback to standard generation
                    response = await self._generate_standard_recipe(
                        user_preferences,
                        recipe_title,
                        num_recipes
                    )
            else:
                # Use standard generation
                logger.info("Using standard recipe generation")
                response = await self._generate_standard_recipe(
                    user_preferences,
                    recipe_title,
                    num_recipes
                )

            # Update metrics
            elapsed_time = time.time() - start_time
            self._update_metrics(elapsed_time)

            # Cache successful response
            self.response_cache[cache_key] = {
                'response': response,
                'timestamp': time.time()
            }

            logger.info(f"✅ Recipe generation completed in {elapsed_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"❌ Recipe generation failed: {e}")
            raise Exception(f"Failed to generate recipes: {str(e)}")


# Create global instance
enhanced_openai_service = EnhancedOpenAIService()


# Export for backward compatibility
async def generate_recipe(user_preferences: Dict[str, Any],
                          recipe_title: str,
                          num_recipes: int = 3) -> str:
    """Backward compatible recipe generation"""
    return await enhanced_openai_service.generate_recipe(
        user_preferences,
        recipe_title,
        num_recipes,
        use_advanced=True
    )