# nutrition-backend/services/advanced_prompt_service.py
"""
Advanced Prompt Engineering Service for Nutrition App
Implements sophisticated prompt strategies for optimal AI responses
"""

import json
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
import asyncio
from dataclasses import dataclass
import logging

from config import config
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class PromptStrategy(Enum):
    """Different prompt strategies for various use cases"""
    CHAIN_OF_THOUGHT = "chain_of_thought"
    FEW_SHOT = "few_shot"
    ROLE_BASED = "role_based"
    STRUCTURED_OUTPUT = "structured_output"
    ITERATIVE_REFINEMENT = "iterative_refinement"
    MULTI_PERSPECTIVE = "multi_perspective"
    SOCRATIC = "socratic"
    TREE_OF_THOUGHTS = "tree_of_thoughts"


class ResponseFormat(Enum):
    """Expected response formats"""
    JSON = "json"
    STRUCTURED_TEXT = "structured_text"
    CONVERSATIONAL = "conversational"
    STEP_BY_STEP = "step_by_step"
    ANALYTICAL = "analytical"


@dataclass
class PromptContext:
    """Context for prompt generation"""
    user_preferences: Dict[str, Any]
    conversation_history: List[Dict[str, str]]
    domain_knowledge: Dict[str, Any]
    constraints: Dict[str, Any]
    output_requirements: Dict[str, Any]
    strategy: PromptStrategy
    format: ResponseFormat


class AdvancedPromptService:
    """Advanced prompt engineering service with multiple strategies"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=config.openai_api_key)
        self.prompt_templates = self._initialize_templates()
        self.example_library = self._initialize_examples()
        self.domain_knowledge = self._initialize_domain_knowledge()

    def _initialize_templates(self) -> Dict[str, str]:
        """Initialize sophisticated prompt templates"""
        return {
            "recipe_generation_advanced": """
You are NutriChef AI, an expert culinary AI with deep knowledge in:
- Nutritional science and dietary requirements
- Global cuisine traditions and modern fusion techniques
- Food science and ingredient interactions
- Budget optimization and meal planning
- Health conditions and therapeutic diets

THINKING PROCESS:
1. Analyze the request comprehensively
2. Consider nutritional balance and health goals
3. Optimize for taste, texture, and visual appeal
4. Ensure practical preparation methods
5. Calculate accurate costs and nutritional data

USER CONTEXT:
{user_context}

CONSTRAINTS:
{constraints}

TASK: {task_description}

Please think through this step-by-step:
1. What are the key requirements and constraints?
2. What nutritional goals should be prioritized?
3. Which ingredients best meet these criteria?
4. How can we maximize flavor while meeting constraints?
5. What cooking techniques will work best?

Now generate the recipe(s) following this exact structure:
{output_structure}
""",

            "nutrition_coaching_advanced": """
You are Dr. NutriCoach, a certified nutritionist and fitness expert with expertise in:
- Clinical nutrition and dietetics
- Sports nutrition and performance optimization
- Behavioral psychology for habit formation
- Metabolic health and body composition
- Evidence-based supplementation

ANALYTICAL FRAMEWORK:
1. Assess current status and goals
2. Calculate metabolic requirements
3. Design progressive nutrition strategy
4. Address potential obstacles
5. Create actionable implementation plan

CLIENT PROFILE:
{client_profile}

GOALS & TIMELINE:
{goals}

Provide comprehensive coaching using this approach:
1. Current Assessment: Analyze the client's starting point
2. Goal Analysis: Break down goals into achievable milestones
3. Metabolic Calculations: Show your work for TDEE, macros, etc.
4. Strategy Design: Create phase-based progression plan
5. Implementation Guide: Practical daily/weekly actions
6. Monitoring Plan: How to track and adjust

Format your response as:
{response_format}
""",

            "meal_plan_optimization": """
You are MealPlan Pro, specializing in creating optimized meal plans that balance:
- Nutritional completeness and variety
- Budget constraints and ingredient availability
- Preparation time and cooking skills
- Personal preferences and cultural considerations
- Sustainability and food waste reduction

OPTIMIZATION PARAMETERS:
{parameters}

USER REQUIREMENTS:
{requirements}

Create a meal plan using multi-criteria optimization:
1. Nutritional Score (40%): Meeting macro/micro targets
2. Variety Score (20%): Diverse ingredients and cuisines
3. Practicality Score (20%): Prep time and complexity
4. Cost Score (10%): Budget optimization
5. Preference Score (10%): Alignment with tastes

Generate the optimized plan with:
{output_specifications}
""",

            "ingredient_substitution_advanced": """
You are SubstituteChef, an expert in ingredient science and culinary adaptation:
- Chemical and physical properties of ingredients
- Flavor profiles and sensory characteristics
- Nutritional equivalencies and improvements
- Allergy and dietary restriction accommodations
- Global ingredient availability

ORIGINAL RECIPE:
{original_recipe}

SUBSTITUTION NEEDS:
{substitution_requirements}

Analyze each substitution using this framework:
1. Functional Role: What does the ingredient do?
2. Sensory Impact: Taste, texture, appearance
3. Nutritional Comparison: Improvements or trade-offs
4. Preparation Adjustments: Changes needed in method
5. Expected Outcome: How will it affect the final dish?

Provide substitutions with confidence scores:
{substitution_format}
""",

            "recipe_adaptation_chain": """
Let's adapt this recipe through careful analysis:

ORIGINAL RECIPE:
{recipe}

ADAPTATION GOALS:
{goals}

Step 1 - Ingredient Analysis:
- List each ingredient's purpose
- Identify critical vs. flexible components
- Note nutritional contributions

Step 2 - Goal Mapping:
- Map each goal to specific changes needed
- Identify potential conflicts between goals
- Prioritize adaptations

Step 3 - Adaptation Strategy:
- Propose specific substitutions/modifications
- Calculate nutritional impact
- Adjust cooking methods if needed

Step 4 - Validation:
- Will it still taste good?
- Does it meet all goals?
- Is it practical to make?

Final Adapted Recipe:
{output_format}
"""
        }

    def _initialize_examples(self) -> Dict[str, List[Dict[str, str]]]:
        """Initialize few-shot learning examples"""
        return {
            "healthy_transformations": [
                {
                    "original": "Fried Chicken - 450 cal, 25g fat",
                    "transformed": "Air-Fried Chicken with Herb Crust - 280 cal, 12g fat",
                    "changes": "Air frying instead of deep frying, whole wheat panko crust with herbs"
                },
                {
                    "original": "Creamy Pasta Carbonara - 650 cal, 35g fat",
                    "transformed": "Lightened Carbonara with Cauliflower - 380 cal, 18g fat",
                    "changes": "Greek yogurt base, turkey bacon, cauliflower rice blend"
                }
            ],
            "budget_optimizations": [
                {
                    "expensive": "Salmon Fillet with Asparagus - $18",
                    "budget": "Seasoned Tilapia with Green Beans - $7",
                    "strategy": "White fish substitution, seasonal vegetables"
                }
            ],
            "cultural_adaptations": [
                {
                    "original": "Italian Risotto",
                    "adapted": "Mexican-Style Cilantro Lime Rice",
                    "elements": "Similar creamy texture, localized flavors"
                }
            ]
        }

    def _initialize_domain_knowledge(self) -> Dict[str, Any]:
        """Initialize domain-specific knowledge base"""
        return {
            "nutritional_interactions": {
                "iron_absorption": {
                    "enhancers": ["vitamin C", "citrus", "tomatoes"],
                    "inhibitors": ["calcium", "tannins", "phytates"]
                },
                "protein_combinations": {
                    "complete_proteins": [
                        ["rice", "beans"],
                        ["hummus", "whole grain pita"],
                        ["peanut butter", "whole grain bread"]
                    ]
                }
            },
            "cooking_science": {
                "maillard_reaction": {
                    "temp_range": "280-330°F",
                    "enhancers": ["dry surface", "alkaline pH"],
                    "flavor_development": "savory, roasted notes"
                },
                "emulsification": {
                    "agents": ["lecithin", "mustard", "egg yolk"],
                    "techniques": ["slow addition", "constant whisking"]
                }
            },
            "dietary_patterns": {
                "mediterranean": {
                    "key_foods": ["olive oil", "fish", "vegetables", "whole grains"],
                    "macro_distribution": {"carbs": 45, "protein": 20, "fat": 35}
                },
                "dash": {
                    "focus": "blood pressure reduction",
                    "limits": {"sodium": 2300, "saturated_fat": 6}
                }
            }
        }

    async def generate_advanced_recipe(self,
                                       context: PromptContext,
                                       num_recipes: int = 3) -> str:
        """Generate recipes using advanced prompt engineering"""

        # Select optimal strategy based on context
        strategy = self._select_strategy(context)

        # Build multi-stage prompt
        prompts = self._build_recipe_prompts(context, strategy, num_recipes)

        # Execute prompt chain
        results = []
        for i, prompt in enumerate(prompts):
            response = await self._execute_prompt(
                prompt,
                temperature=0.7 if i == 0 else 0.8,
                max_tokens=3000
            )
            results.append(response)

            # Refine next prompt based on previous response
            if i < len(prompts) - 1:
                prompts[i + 1] = self._refine_prompt(prompts[i + 1], response)

        # Combine and format results
        return self._format_recipe_output(results, context)

    async def generate_nutrition_coaching(self,
                                          profile: Dict[str, Any],
                                          goals: List[str]) -> Dict[str, Any]:
        """Generate advanced nutrition coaching plan"""

        # Build comprehensive context
        context = self._build_coaching_context(profile, goals)

        # Use tree-of-thoughts for complex planning
        thought_branches = await self._tree_of_thoughts_coaching(context)

        # Synthesize best path
        coaching_plan = self._synthesize_coaching_plan(thought_branches)

        return coaching_plan

    async def optimize_meal_plan(self,
                                 requirements: Dict[str, Any],
                                 duration_days: int = 7) -> Dict[str, Any]:
        """Generate optimized meal plan using advanced techniques"""

        # Multi-perspective generation
        perspectives = [
            "nutritionist focusing on balanced macros",
            "chef prioritizing flavor and variety",
            "budget analyst minimizing costs",
            "busy parent needing quick meals"
        ]

        plans = []
        for perspective in perspectives:
            plan = await self._generate_perspective_plan(
                requirements,
                duration_days,
                perspective
            )
            plans.append(plan)

        # Merge best aspects of each plan
        optimized_plan = self._merge_meal_plans(plans, requirements)

        return optimized_plan

    def _select_strategy(self, context: PromptContext) -> PromptStrategy:
        """Select optimal prompt strategy based on context"""

        # Complex multi-constraint scenarios
        if len(context.constraints) > 5:
            return PromptStrategy.TREE_OF_THOUGHTS

        # Learning from examples
        if context.conversation_history:
            return PromptStrategy.FEW_SHOT

        # Analytical tasks
        if context.format == ResponseFormat.ANALYTICAL:
            return PromptStrategy.CHAIN_OF_THOUGHT

        # Creative generation
        if "creative" in context.output_requirements:
            return PromptStrategy.MULTI_PERSPECTIVE

        return PromptStrategy.STRUCTURED_OUTPUT

    def _build_recipe_prompts(self,
                              context: PromptContext,
                              strategy: PromptStrategy,
                              num_recipes: int) -> List[str]:
        """Build multi-stage prompts for recipe generation"""

        prompts = []

        if strategy == PromptStrategy.CHAIN_OF_THOUGHT:
            # Stage 1: Analysis
            prompts.append(self._build_analysis_prompt(context))
            # Stage 2: Generation with analysis
            prompts.append(self._build_generation_prompt(context, num_recipes))

        elif strategy == PromptStrategy.TREE_OF_THOUGHTS:
            # Multiple exploration paths
            for i in range(3):
                prompts.append(self._build_exploration_prompt(context, i))
            # Synthesis prompt
            prompts.append(self._build_synthesis_prompt(context))

        elif strategy == PromptStrategy.FEW_SHOT:
            # Include examples
            prompts.append(self._build_few_shot_prompt(context, num_recipes))

        else:
            # Default structured
            prompts.append(self._build_structured_prompt(context, num_recipes))

        return prompts

    async def _execute_prompt(self,
                              prompt: str,
                              temperature: float = 0.7,
                              max_tokens: int = 2000) -> str:
        """Execute a single prompt with error handling"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",  # Use GPT-4 for better reasoning
                messages=[
                    {
                        "role": "system",
                        "content": "You are an advanced AI assistant with expertise in nutrition, cooking, and health optimization."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Prompt execution failed: {e}")
            # Fallback to simpler prompt
            return await self._execute_fallback_prompt(prompt)

    def _build_analysis_prompt(self, context: PromptContext) -> str:
        """Build analysis phase prompt"""

        template = """
        Analyze this recipe request step by step:

        USER PREFERENCES:
        {preferences}

        CONSTRAINTS:
        {constraints}

        Please analyze:
        1. Key nutritional requirements based on the user's goals
        2. Ingredient categories that best fit the constraints
        3. Cooking methods that preserve nutrients and flavor
        4. Potential challenges and how to address them
        5. Optimization opportunities for health and taste

        Provide your analysis in a structured format.
        """

        return template.format(
            preferences=json.dumps(context.user_preferences, indent=2),
            constraints=json.dumps(context.constraints, indent=2)
        )

    def _build_generation_prompt(self,
                                 context: PromptContext,
                                 num_recipes: int) -> str:
        """Build generation phase prompt with context"""

        template = self.prompt_templates["recipe_generation_advanced"]

        return template.format(
            user_context=self._format_user_context(context),
            constraints=self._format_constraints(context),
            task_description=f"Generate {num_recipes} unique, optimized recipes",
            output_structure=self._get_output_structure(context.format)
        )

    def _format_user_context(self, context: PromptContext) -> str:
        """Format user context for prompt"""

        sections = []

        # User preferences
        if context.user_preferences:
            prefs = context.user_preferences
            sections.append(f"Dietary Preferences: {prefs.get('diet', 'Flexible')}")
            sections.append(f"Budget: ${prefs.get('budget', 20)} per recipe")

            if prefs.get('allergies'):
                sections.append(f"Allergies: {prefs['allergies']}")

            if prefs.get('dietary_restrictions'):
                active = [k for k, v in prefs['dietary_restrictions'].items() if v]
                if active:
                    sections.append(f"Restrictions: {', '.join(active)}")

        # Health goals
        if 'health_goals' in context.domain_knowledge:
            sections.append(f"Health Goals: {context.domain_knowledge['health_goals']}")

        return "\n".join(sections)

    def _format_constraints(self, context: PromptContext) -> str:
        """Format constraints for prompt"""

        constraints = []

        for category, details in context.constraints.items():
            if isinstance(details, dict):
                constraint_items = [f"{k}: {v}" for k, v in details.items()]
                constraints.append(f"{category}:\n  " + "\n  ".join(constraint_items))
            else:
                constraints.append(f"{category}: {details}")

        return "\n".join(constraints)

    async def _tree_of_thoughts_coaching(self,
                                         context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Implement tree of thoughts for complex coaching plans"""

        # Generate multiple thought branches
        branches = []

        # Branch 1: Aggressive approach
        aggressive = await self._generate_coaching_branch(
            context,
            "aggressive progression for fastest results"
        )
        branches.append({"approach": "aggressive", "plan": aggressive})

        # Branch 2: Moderate approach
        moderate = await self._generate_coaching_branch(
            context,
            "balanced progression for sustainability"
        )
        branches.append({"approach": "moderate", "plan": moderate})

        # Branch 3: Conservative approach
        conservative = await self._generate_coaching_branch(
            context,
            "conservative progression for injury prevention"
        )
        branches.append({"approach": "conservative", "plan": conservative})

        # Evaluate each branch
        for branch in branches:
            branch["evaluation"] = await self._evaluate_coaching_branch(
                branch["plan"],
                context
            )

        return branches

    def _synthesize_coaching_plan(self,
                                  branches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synthesize best coaching plan from multiple branches"""

        # Find best scoring branch
        best_branch = max(branches, key=lambda x: x["evaluation"]["score"])

        # Extract key elements from other branches
        valuable_elements = []
        for branch in branches:
            if branch != best_branch:
                elements = self._extract_valuable_elements(branch)
                valuable_elements.extend(elements)

        # Merge into final plan
        final_plan = best_branch["plan"].copy()
        final_plan["additional_strategies"] = valuable_elements
        final_plan["approach_rationale"] = self._generate_rationale(branches)

        return final_plan

    async def _generate_perspective_plan(self,
                                         requirements: Dict[str, Any],
                                         duration_days: int,
                                         perspective: str) -> Dict[str, Any]:
        """Generate meal plan from specific perspective"""

        prompt = f"""
        As a {perspective}, create a {duration_days}-day meal plan.

        Requirements:
        {json.dumps(requirements, indent=2)}

        Focus on your perspective's priorities while meeting all requirements.

        Format as:
        {{
            "day_1": {{
                "breakfast": {{}},
                "lunch": {{}},
                "dinner": {{}},
                "snacks": []
            }},
            ...
        }}
        """

        response = await self._execute_prompt(prompt, temperature=0.8)

        try:
            return json.loads(response)
        except:
            # Parse structured text if JSON fails
            return self._parse_meal_plan_text(response)

    def _merge_meal_plans(self,
                          plans: List[Dict[str, Any]],
                          requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple meal plans optimally"""

        merged_plan = {}

        for day in range(1, 8):
            day_key = f"day_{day}"
            merged_plan[day_key] = {}

            # Score each meal option
            for meal in ["breakfast", "lunch", "dinner"]:
                options = []

                for plan in plans:
                    if day_key in plan and meal in plan[day_key]:
                        meal_data = plan[day_key][meal]
                        score = self._score_meal(meal_data, requirements)
                        options.append((meal_data, score))

                # Select best scoring meal
                if options:
                    best_meal = max(options, key=lambda x: x[1])[0]
                    merged_plan[day_key][meal] = best_meal

            # Merge snacks
            all_snacks = []
            for plan in plans:
                if day_key in plan and "snacks" in plan[day_key]:
                    all_snacks.extend(plan[day_key]["snacks"])

            # Deduplicate and select best snacks
            merged_plan[day_key]["snacks"] = self._select_best_snacks(
                all_snacks,
                requirements
            )

        # Add optimization metadata
        merged_plan["optimization_report"] = self._generate_optimization_report(
            merged_plan,
            requirements
        )

        return merged_plan

    def _score_meal(self,
                    meal_data: Dict[str, Any],
                    requirements: Dict[str, Any]) -> float:
        """Score a meal based on requirements"""

        score = 0.0

        # Nutritional alignment
        if "nutrition" in meal_data and "macro_targets" in requirements:
            nutrition_score = self._calculate_nutrition_score(
                meal_data["nutrition"],
                requirements["macro_targets"]
            )
            score += nutrition_score * 0.4

        # Cost efficiency
        if "cost" in meal_data and "budget" in requirements:
            cost_score = min(requirements["budget"] / meal_data["cost"], 1.0)
            score += cost_score * 0.2

        # Preparation time
        if "prep_time" in meal_data and "max_prep_time" in requirements:
            time_score = min(requirements["max_prep_time"] / meal_data["prep_time"], 1.0)
            score += time_score * 0.2

        # Variety and appeal
        variety_score = self._calculate_variety_score(meal_data)
        score += variety_score * 0.2

        return score

    def _format_recipe_output(self,
                              results: List[str],
                              context: PromptContext) -> str:
        """Format final recipe output"""

        # Combine results based on strategy
        if context.strategy == PromptStrategy.TREE_OF_THOUGHTS:
            # Results are explorations + synthesis
            synthesis = results[-1]
            return self._enhance_with_explorations(synthesis, results[:-1])

        elif context.strategy == PromptStrategy.CHAIN_OF_THOUGHT:
            # Results are analysis + generation
            analysis = results[0]
            recipes = results[1]
            return self._enhance_with_analysis(recipes, analysis)

        else:
            # Single result
            return results[0]

    def get_prompt_metrics(self) -> Dict[str, Any]:
        """Get metrics about prompt performance"""

        return {
            "strategies_used": {
                strategy.value: count
                for strategy, count in self.strategy_usage.items()
            },
            "average_prompt_length": self.calculate_avg_prompt_length(),
            "success_rate": self.calculate_success_rate(),
            "optimization_stats": self.get_optimization_stats()
        }


# Global instance
advanced_prompt_service = AdvancedPromptService()


# Convenience functions
async def generate_advanced_recipe(user_preferences: Dict[str, Any],
                                   recipe_title: str,
                                   num_recipes: int = 3) -> str:
    """Generate recipes using advanced prompt engineering"""

    context = PromptContext(
        user_preferences=user_preferences,
        conversation_history=[],
        domain_knowledge={},
        constraints=extract_constraints(user_preferences),
        output_requirements={"format": "structured", "detail": "comprehensive"},
        strategy=PromptStrategy.CHAIN_OF_THOUGHT,
        format=ResponseFormat.STRUCTURED_TEXT
    )

    return await advanced_prompt_service.generate_advanced_recipe(
        context,
        num_recipes
    )


def extract_constraints(preferences: Dict[str, Any]) -> Dict[str, Any]:
    """Extract constraints from user preferences"""

    constraints = {}

    if "budget" in preferences:
        constraints["budget"] = {"max": preferences["budget"], "currency": "USD"}

    if "dietary_restrictions" in preferences:
        active_restrictions = [
            k for k, v in preferences["dietary_restrictions"].items() if v
        ]
        if active_restrictions:
            constraints["dietary"] = active_restrictions

    if "cooking_constraints" in preferences:
        constraints["cooking"] = preferences["cooking_constraints"]

    if "macro_targets" in preferences and preferences["macro_targets"].get("enableTargets"):
        constraints["nutrition"] = preferences["macro_targets"]

    return constraints