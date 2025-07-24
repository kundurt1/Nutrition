# nutrition-backend/services/nutrition_coach.py

import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from openai import OpenAI
import os

from database import supabase


class FitnessGoal(Enum):
    STRENGTH_BUILDING = "strength_building"
    FAT_LOSS = "fat_loss"
    MUSCLE_GAIN = "muscle_gain"
    BODY_RECOMPOSITION = "body_recomposition"
    ENDURANCE = "endurance"
    MAINTENANCE = "maintenance"
    CUTTING = "cutting"
    BULKING = "bulking"


class ActivityLevel(Enum):
    SEDENTARY = "sedentary"  # 1.2
    LIGHTLY_ACTIVE = "lightly_active"  # 1.375
    MODERATELY_ACTIVE = "moderately_active"  # 1.55
    VERY_ACTIVE = "very_active"  # 1.725
    EXTREMELY_ACTIVE = "extremely_active"  # 1.9


class TrainingPhase(Enum):
    FOUNDATION = "foundation"  # Weeks 1-4
    PROGRESSION = "progression"  # Weeks 5-8
    INTENSIFICATION = "intensification"  # Weeks 9-12
    DELOAD = "deload"  # Recovery week


@dataclass
class UserProfile:
    user_id: str
    age: int
    gender: str
    height_cm: float
    current_weight: float
    target_weight: float
    body_fat_percentage: Optional[float]
    target_body_fat: Optional[float]
    activity_level: ActivityLevel
    primary_goal: FitnessGoal
    timeline_weeks: int
    training_days_per_week: int
    experience_level: str
    current_phase: TrainingPhase
    week_in_phase: int


@dataclass
class MacroTargets:
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: float
    protein_priority: str
    carb_timing: str
    meal_distribution: Dict[str, float]


@dataclass
class ProgressMetrics:
    weight_change: float
    bf_change: Optional[float]
    adherence_rate: float
    energy_level: float
    strength_trend: str
    plateau_detected: bool
    weeks_at_plateau: int


class NutritionCoachService:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Activity multipliers for TDEE calculation
        self.activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9
        }

    async def assess_user_goals(self, user_id: str, assessment_data: Dict) -> Dict:
        """Complete fitness goal assessment and profile creation"""

        # Calculate initial metrics
        profile = self._create_user_profile(user_id, assessment_data)
        macro_targets = self.calculate_personalized_macros(profile)

        # Save to database
        await self._save_fitness_profile(profile)
        await self._save_macro_targets(user_id, macro_targets)

        # Generate initial coaching plan
        coaching_plan = await self._generate_initial_coaching_plan(profile, macro_targets)

        return {
            "profile": profile.__dict__,
            "macro_targets": macro_targets.__dict__,
            "coaching_plan": coaching_plan,
            "estimated_timeline": self._estimate_goal_timeline(profile),
            "success_probability": self._calculate_success_probability(profile)
        }

    def calculate_personalized_macros(self, profile: UserProfile) -> MacroTargets:
        """Calculate personalized macro and calorie targets based on goals"""

        # Calculate BMR using Mifflin-St Jeor equation
        if profile.gender.lower() == 'male':
            bmr = (10 * profile.current_weight) + (6.25 * profile.height_cm) - (5 * profile.age) + 5
        else:
            bmr = (10 * profile.current_weight) + (6.25 * profile.height_cm) - (5 * profile.age) - 161

        # Calculate TDEE
        tdee = bmr * self.activity_multipliers[profile.activity_level]

        # Goal-specific calorie adjustment
        target_calories = self._adjust_calories_for_goal(tdee, profile)

        # Goal-specific macro distribution
        macros = self._distribute_macros(target_calories, profile)

        return macros

    def _adjust_calories_for_goal(self, tdee: float, profile: UserProfile) -> int:
        """Adjust calories based on specific fitness goals"""

        goal_adjustments = {
            FitnessGoal.FAT_LOSS: -0.20,  # 20% deficit
            FitnessGoal.CUTTING: -0.25,  # 25% deficit (more aggressive)
            FitnessGoal.MUSCLE_GAIN: +0.15,  # 15% surplus
            FitnessGoal.BULKING: +0.20,  # 20% surplus
            FitnessGoal.STRENGTH_BUILDING: +0.10,  # 10% surplus
            FitnessGoal.BODY_RECOMPOSITION: 0.0,  # Maintenance with cycling
            FitnessGoal.MAINTENANCE: 0.0,
            FitnessGoal.ENDURANCE: +0.05  # Small surplus for recovery
        }

        adjustment = goal_adjustments.get(profile.primary_goal, 0.0)

        # Adjust based on experience level
        if profile.experience_level == "beginner" and adjustment > 0:
            adjustment *= 0.8  # Smaller surplus for beginners
        elif profile.experience_level == "advanced" and adjustment < 0:
            adjustment *= 1.2  # More aggressive deficit for advanced

        # Timeline adjustment
        if profile.timeline_weeks < 12 and adjustment < 0:
            adjustment *= 1.3  # More aggressive for shorter timelines

        return int(tdee * (1 + adjustment))

    def _distribute_macros(self, calories: int, profile: UserProfile) -> MacroTargets:
        """Intelligent macro distribution based on goals"""

        # Base protein calculation (higher for strength/muscle goals)
        protein_per_kg = self._get_protein_requirement(profile)
        protein_grams = profile.current_weight * protein_per_kg
        protein_calories = protein_grams * 4

        # Goal-specific fat percentage
        fat_percentage = self._get_fat_percentage(profile)
        fat_calories = calories * fat_percentage
        fat_grams = fat_calories / 9

        # Remaining calories go to carbs
        carb_calories = calories - protein_calories - fat_calories
        carb_grams = max(carb_calories / 4, 50)  # Minimum 50g carbs

        # Adjust if carbs are too low
        if carb_grams < 100 and profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
            carb_grams = 100
            carb_calories = carb_grams * 4
            fat_calories = calories - protein_calories - carb_calories
            fat_grams = fat_calories / 9

        # Fiber target
        fiber_grams = max(25, calories / 80)  # ~1g fiber per 80 calories

        # Determine priorities and timing
        protein_priority = self._get_protein_priority(profile)
        carb_timing = self._get_carb_timing_strategy(profile)
        meal_distribution = self._get_meal_distribution(profile)

        return MacroTargets(
            calories=calories,
            protein=round(protein_grams, 1),
            carbs=round(carb_grams, 1),
            fat=round(fat_grams, 1),
            fiber=round(fiber_grams, 1),
            protein_priority=protein_priority,
            carb_timing=carb_timing,
            meal_distribution=meal_distribution
        )

    def _get_protein_requirement(self, profile: UserProfile) -> float:
        """Get protein requirement in g/kg bodyweight"""

        base_requirements = {
            FitnessGoal.STRENGTH_BUILDING: 2.2,
            FitnessGoal.MUSCLE_GAIN: 2.4,
            FitnessGoal.BODY_RECOMPOSITION: 2.6,
            FitnessGoal.CUTTING: 2.8,
            FitnessGoal.FAT_LOSS: 2.2,
            FitnessGoal.BULKING: 2.0,
            FitnessGoal.MAINTENANCE: 1.8,
            FitnessGoal.ENDURANCE: 1.6
        }

        base = base_requirements.get(profile.primary_goal, 2.0)

        # Adjust for experience level
        if profile.experience_level == "advanced":
            base *= 1.1
        elif profile.experience_level == "beginner":
            base *= 0.95

        return base

    def _get_fat_percentage(self, profile: UserProfile) -> float:
        """Get fat percentage of total calories"""

        base_percentages = {
            FitnessGoal.STRENGTH_BUILDING: 0.25,
            FitnessGoal.MUSCLE_GAIN: 0.25,
            FitnessGoal.BODY_RECOMPOSITION: 0.30,
            FitnessGoal.CUTTING: 0.20,
            FitnessGoal.FAT_LOSS: 0.25,
            FitnessGoal.BULKING: 0.30,
            FitnessGoal.MAINTENANCE: 0.30,
            FitnessGoal.ENDURANCE: 0.25
        }

        return base_percentages.get(profile.primary_goal, 0.25)

    def _get_protein_priority(self, profile: UserProfile) -> str:
        """Get protein timing priority"""

        if profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
            return "Post-workout within 2 hours, evenly distributed throughout day"
        elif profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            return "High protein breakfast and evening meals for satiety"
        else:
            return "Evenly distributed across all meals"

    def _get_carb_timing_strategy(self, profile: UserProfile) -> str:
        """Get carbohydrate timing strategy"""

        if profile.training_days_per_week >= 4:
            return "Higher carbs around training sessions, lower on rest days"
        elif profile.primary_goal == FitnessGoal.FAT_LOSS:
            return "Moderate carbs early in day, minimal evening carbs"
        else:
            return "Evenly distributed with slight emphasis pre/post workout"

    def _get_meal_distribution(self, profile: UserProfile) -> Dict[str, float]:
        """Get optimal meal distribution percentages"""

        if profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
            return {
                "breakfast": 0.25,
                "lunch": 0.30,
                "pre_workout": 0.15,
                "post_workout": 0.20,
                "dinner": 0.10
            }
        elif profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            return {
                "breakfast": 0.30,
                "lunch": 0.35,
                "snack": 0.10,
                "dinner": 0.25
            }
        else:
            return {
                "breakfast": 0.25,
                "lunch": 0.35,
                "snack": 0.15,
                "dinner": 0.25
            }

    async def weekly_progress_analysis(self, user_id: str) -> Dict:
        """Perform weekly progress analysis and generate adaptive recommendations"""

        # Get user profile and recent progress
        profile = await self._get_user_profile(user_id)
        progress = await self._analyze_recent_progress(user_id)
        adherence = await self._calculate_adherence_metrics(user_id)

        # Generate AI-powered insights
        insights = await self._generate_ai_insights(profile, progress, adherence)

        # Determine if adjustments are needed
        adjustments = self._calculate_macro_adjustments(profile, progress, adherence)

        # Generate coaching recommendations
        recommendations = await self._generate_coaching_recommendations(
            profile, progress, adherence, insights
        )

        # Save insights to database
        await self._save_coaching_insights(user_id, {
            "progress": progress.__dict__,
            "insights": insights,
            "adjustments": adjustments,
            "recommendations": recommendations
        })

        return {
            "progress_summary": self._format_progress_summary(progress),
            "key_insights": insights,
            "macro_adjustments": adjustments,
            "recommendations": recommendations,
            "next_week_focus": recommendations.get("focus_areas", []),
            "motivation_message": insights.get("motivation", "Keep up the great work!")
        }

    async def generate_goal_oriented_recipes(self, user_id: str, meal_type: str,
                                             training_day: bool = False) -> Dict:
        """Generate recipes optimized for user's specific goals and meal timing"""

        profile = await self._get_user_profile(user_id)
        macro_targets = await self._get_current_macro_targets(user_id)

        # Adjust macros for meal type and training day
        meal_macros = self._calculate_meal_specific_macros(
            macro_targets, meal_type, training_day, profile
        )

        # Build enhanced prompt for OpenAI
        coaching_prompt = self._build_coaching_recipe_prompt(
            profile, meal_macros, meal_type, training_day
        )

        # Generate recipe using existing OpenAI service
        recipe_response = await self._call_openai_for_recipe(coaching_prompt)

        # Parse and enhance with coaching insights
        recipe = self._parse_and_enhance_recipe(recipe_response, meal_macros, profile)

        return {
            "recipe": recipe,
            "coaching_notes": self._generate_recipe_coaching_notes(profile, meal_type),
            "meal_macros": meal_macros,
            "goal_alignment": self._assess_recipe_goal_alignment(recipe, profile)
        }

    def _build_coaching_recipe_prompt(self, profile: UserProfile, meal_macros: Dict,
                                      meal_type: str, training_day: bool) -> str:
        """Build enhanced prompt for goal-oriented recipe generation"""

        goal_descriptions = {
            FitnessGoal.STRENGTH_BUILDING: "building strength and muscle mass",
            FitnessGoal.FAT_LOSS: "losing body fat while preserving muscle",
            FitnessGoal.MUSCLE_GAIN: "maximizing muscle growth",
            FitnessGoal.BODY_RECOMPOSITION: "losing fat and gaining muscle simultaneously",
            FitnessGoal.CUTTING: "achieving a lean, defined physique",
            FitnessGoal.BULKING: "gaining weight and muscle mass efficiently"
        }

        training_context = "TRAINING DAY" if training_day else "REST DAY"
        goal_description = goal_descriptions.get(profile.primary_goal, "maintaining health and fitness")

        prompt = f"""You are an expert sports nutritionist and chef creating a {meal_type} recipe for someone focused on {goal_description}.

USER PROFILE:
- Primary Goal: {profile.primary_goal.value}
- Training Phase: {profile.current_phase.value} (Week {profile.week_in_phase})
- Experience Level: {profile.experience_level}
- Today: {training_context}

MEAL TARGETS:
- Calories: {meal_macros['calories']}
- Protein: {meal_macros['protein']}g (PRIORITY: {meal_macros.get('protein_priority', 'High')})
- Carbs: {meal_macros['carbs']}g ({meal_macros.get('carb_timing', 'Moderate')})
- Fat: {meal_macros['fat']}g
- Fiber: {meal_macros['fiber']}g

COACHING PRIORITIES:
{self._get_meal_specific_priorities(profile.primary_goal, meal_type, training_day)}

Create a recipe that:
1. Meets the macro targets within 10% accuracy
2. Uses whole, nutrient-dense foods
3. Supports recovery and performance
4. Is practical and delicious
5. Includes meal prep tips if applicable

Format your response as:
RECIPE NAME: [Name]

NUTRITION FACTS:
- Calories: [amount]
- Protein: [amount]g
- Carbs: [amount]g  
- Fat: [amount]g
- Fiber: [amount]g

INGREDIENTS:
[List with specific amounts]

DIRECTIONS:
[Step-by-step instructions]

COACHING NOTES:
[Why this meal supports the user's goals]

MEAL PREP TIPS:
[Storage and preparation suggestions]
"""

        return prompt

    def _get_meal_specific_priorities(self, goal: FitnessGoal, meal_type: str, training_day: bool) -> str:
        """Get meal-specific priorities based on goals and timing"""

        priorities = []

        if meal_type == "breakfast":
            priorities.append("- Start the day with stable energy and satiety")
            if goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
                priorities.append("- High protein to kickstart muscle protein synthesis")

        elif meal_type == "pre_workout" and training_day:
            priorities.append("- Easily digestible carbs for immediate energy")
            priorities.append("- Moderate protein to prevent muscle breakdown")
            priorities.append("- Low fat and fiber to avoid digestive issues")

        elif meal_type == "post_workout" and training_day:
            priorities.append("- Fast-absorbing protein for muscle repair")
            priorities.append("- High glycemic carbs to replenish glycogen")
            priorities.append("- 3:1 or 4:1 carb to protein ratio for optimal recovery")

        elif meal_type == "dinner":
            if goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
                priorities.append("- Lower carbs to support fat burning overnight")
                priorities.append("- High protein and fiber for satiety")
            else:
                priorities.append("- Balanced macros to support overnight recovery")
                priorities.append("- Include casein protein or slow-digesting proteins")

        return "\n".join(priorities)

    async def _call_openai_for_recipe(self, prompt: str) -> str:
        """Call OpenAI API with coaching-enhanced prompt"""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a world-class sports nutritionist and chef who creates scientifically-backed, goal-oriented recipes that taste amazing and support athletic performance."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"❌ OpenAI API error in coaching service: {str(e)}")
            raise e

    def _calculate_meal_specific_macros(self, daily_targets: MacroTargets, meal_type: str,
                                        training_day: bool, profile: UserProfile) -> Dict:
        """Calculate macro targets for specific meal based on timing and goals"""

        # Get meal distribution percentages
        distribution = daily_targets.meal_distribution

        # Base meal percentages
        if meal_type in distribution:
            meal_percentage = distribution[meal_type]
        else:
            # Default distributions for common meal types
            meal_distributions = {
                "breakfast": 0.25,
                "lunch": 0.30,
                "pre_workout": 0.15,
                "post_workout": 0.20,
                "dinner": 0.25,
                "snack": 0.15
            }
            meal_percentage = meal_distributions.get(meal_type, 0.25)

        # Adjust for training day
        if training_day and meal_type == "pre_workout":
            # Higher carbs pre-workout
            carb_multiplier = 1.3
            protein_multiplier = 0.8
            fat_multiplier = 0.5
        elif training_day and meal_type == "post_workout":
            # Higher carbs and protein post-workout
            carb_multiplier = 1.4
            protein_multiplier = 1.2
            fat_multiplier = 0.6
        elif not training_day and profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            # Lower carbs on rest days for fat loss
            carb_multiplier = 0.7
            protein_multiplier = 1.1
            fat_multiplier = 1.2
        else:
            carb_multiplier = protein_multiplier = fat_multiplier = 1.0

        return {
            "calories": int(daily_targets.calories * meal_percentage),
            "protein": round(daily_targets.protein * meal_percentage * protein_multiplier, 1),
            "carbs": round(daily_targets.carbs * meal_percentage * carb_multiplier, 1),
            "fat": round(daily_targets.fat * meal_percentage * fat_multiplier, 1),
            "fiber": round(daily_targets.fiber * meal_percentage, 1),
            "protein_priority": daily_targets.protein_priority,
            "carb_timing": daily_targets.carb_timing
        }

    async def generate_smart_grocery_list(self, user_id: str, meal_plan: Dict) -> Dict:
        """Generate grocery list optimized for user's fitness goals"""

        profile = await self._get_user_profile(user_id)
        pantry_items = await self._get_pantry_analysis(user_id)

        # Identify goal-priority foods
        priority_foods = self._get_goal_priority_foods(profile.primary_goal)

        # Analyze meal plan for ingredients
        required_ingredients = self._extract_meal_plan_ingredients(meal_plan)

        # Generate optimized list
        grocery_list = await self._optimize_grocery_list(
            required_ingredients, priority_foods, pantry_items, profile
        )

        # Add coaching recommendations
        coaching_additions = self._get_coaching_grocery_additions(profile)

        return {
            "priority_items": grocery_list.get("must_haves", []),
            "optional_items": grocery_list.get("nice_to_haves", []),
            "goal_boosters": priority_foods,
            "coaching_additions": coaching_additions,
            "prep_suggestions": self._get_meal_prep_suggestions(profile),
            "cost_optimization": grocery_list.get("budget_tips", []),
            "substitution_options": grocery_list.get("substitutions", [])
        }

    def _get_goal_priority_foods(self, goal: FitnessGoal) -> List[Dict]:
        """Get priority foods for specific fitness goals"""

        priority_foods = {
            FitnessGoal.STRENGTH_BUILDING: [
                {"category": "Protein",
                 "foods": ["Lean beef", "Chicken breast", "Salmon", "Greek yogurt", "Eggs", "Whey protein"],
                 "reason": "High-quality protein for muscle building"},
                {"category": "Carbs", "foods": ["Oats", "Sweet potatoes", "Rice", "Quinoa", "Bananas"],
                 "reason": "Sustained energy for training"},
                {"category": "Recovery", "foods": ["Tart cherry juice", "Spinach", "Berries", "Nuts"],
                 "reason": "Anti-inflammatory compounds"}
            ],
            FitnessGoal.FAT_LOSS: [
                {"category": "Protein",
                 "foods": ["Chicken breast", "White fish", "Egg whites", "Protein powder", "Cottage cheese"],
                 "reason": "High thermic effect, muscle preservation"},
                {"category": "Fiber", "foods": ["Broccoli", "Brussels sprouts", "Cauliflower", "Asparagus", "Berries"],
                 "reason": "Satiety and metabolic benefits"},
                {"category": "Healthy Fats", "foods": ["Avocado", "Olive oil", "Almonds", "Salmon"],
                 "reason": "Hormone production and satiety"}
            ],
            FitnessGoal.MUSCLE_GAIN: [
                {"category": "Protein", "foods": ["Whole eggs", "Beef", "Chicken thighs", "Milk", "Peanut butter"],
                 "reason": "Complete amino acid profiles"},
                {"category": "Calorie Dense", "foods": ["Nuts", "Dates", "Granola", "Whole grains", "Dried fruits"],
                 "reason": "Efficient calorie delivery"},
                {"category": "Recovery", "foods": ["Chocolate milk", "Bananas", "Oats", "Yogurt"],
                 "reason": "Post-workout glycogen replenishment"}
            ],
            FitnessGoal.BODY_RECOMPOSITION: [
                {"category": "Lean Protein", "foods": ["Turkey", "Fish", "Tofu", "Legumes", "Egg whites"],
                 "reason": "Muscle preservation during deficit"},
                {"category": "Nutrient Dense",
                 "foods": ["Leafy greens", "Colorful vegetables", "Berries", "Lean meats"],
                 "reason": "Maximum nutrition per calorie"},
                {"category": "Timing Foods", "foods": ["Rice cakes", "Protein powder", "Sweet potatoes"],
                 "reason": "Flexible macro timing"}
            ]
        }

        return priority_foods.get(goal, priority_foods[FitnessGoal.STRENGTH_BUILDING])

    def _get_coaching_grocery_additions(self, profile: UserProfile) -> List[Dict]:
        """Get additional grocery recommendations based on coaching insights"""

        additions = []

        # Goal-specific additions
        if profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
            additions.extend([
                {"item": "Creatine monohydrate", "reason": "Proven strength and muscle building supplement",
                 "category": "supplement"},
                {"item": "Chocolate milk", "reason": "Excellent post-workout recovery drink", "category": "recovery"},
                {"item": "Whole grain bread", "reason": "Pre-workout carbohydrate source", "category": "fuel"}
            ])

        elif profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            additions.extend([
                {"item": "Green tea", "reason": "Metabolism support and appetite control", "category": "metabolic"},
                {"item": "Shirataki noodles", "reason": "Low-calorie pasta alternative", "category": "substitution"},
                {"item": "Cucumber", "reason": "High volume, low calorie for satiety", "category": "volume"}
            ])

        # Training frequency adjustments
        if profile.training_days_per_week >= 5:
            additions.append({
                "item": "Epsom salt",
                "reason": "Recovery baths for high training frequency",
                "category": "recovery"
            })

        # Experience level adjustments
        if profile.experience_level == "beginner":
            additions.extend([
                {"item": "Meal prep containers", "reason": "Essential for consistency", "category": "tools"},
                {"item": "Kitchen scale", "reason": "Accurate portion tracking", "category": "tools"}
            ])

        return additions

    async def _analyze_recent_progress(self, user_id: str) -> ProgressMetrics:
        """Analyze user's recent progress data"""

        try:
            # Get progress entries from last 4 weeks
            result = supabase.table("progress_entries") \
                .select("*") \
                .eq("user_id", user_id) \
                .gte("recorded_at", (datetime.now() - timedelta(weeks=4)).isoformat()) \
                .order("recorded_at") \
                .execute()

            entries = result.data or []

            if len(entries) < 2:
                return ProgressMetrics(
                    weight_change=0.0,
                    bf_change=None,
                    adherence_rate=0.0,
                    energy_level=5.0,
                    strength_trend="insufficient_data",
                    plateau_detected=False,
                    weeks_at_plateau=0
                )

            # Calculate weight trend
            weights = [entry['weight'] for entry in entries if entry.get('weight')]
            weight_change = weights[-1] - weights[0] if len(weights) >= 2 else 0.0

            # Calculate body fat change if available
            bf_readings = [entry['body_fat_estimate'] for entry in entries if entry.get('body_fat_estimate')]
            bf_change = bf_readings[-1] - bf_readings[0] if len(bf_readings) >= 2 else None

            # Calculate average adherence and energy
            adherence_scores = [entry['adherence_score'] for entry in entries if entry.get('adherence_score')]
            avg_adherence = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0.0

            energy_levels = [entry['energy_level'] for entry in entries if entry.get('energy_level')]
            avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 5.0

            # Detect plateaus (weight stable for 3+ weeks)
            recent_weights = weights[-3:] if len(weights) >= 3 else weights
            plateau_detected = len(recent_weights) >= 3 and max(recent_weights) - min(recent_weights) < 0.5

            return ProgressMetrics(
                weight_change=round(weight_change, 1),
                bf_change=round(bf_change, 1) if bf_change else None,
                adherence_rate=round(avg_adherence, 2),
                energy_level=round(avg_energy, 1),
                strength_trend=self._assess_strength_trend(entries),
                plateau_detected=plateau_detected,
                weeks_at_plateau=3 if plateau_detected else 0
            )

        except Exception as e:
            print(f"❌ Error analyzing progress: {e}")
            return ProgressMetrics(
                weight_change=0.0,
                bf_change=None,
                adherence_rate=0.0,
                energy_level=5.0,
                strength_trend="error",
                plateau_detected=False,
                weeks_at_plateau=0
            )

    def _assess_strength_trend(self, entries: List[Dict]) -> str:
        """Assess strength progression trend from entries"""

        # In a full implementation, this would analyze actual strength data
        # For now, we'll use energy levels and adherence as proxies

        recent_entries = entries[-3:] if len(entries) >= 3 else entries

        if not recent_entries:
            return "insufficient_data"

        avg_energy = sum(entry.get('energy_level', 5) for entry in recent_entries) / len(recent_entries)
        avg_adherence = sum(entry.get('adherence_score', 0.5) for entry in recent_entries) / len(recent_entries)

        if avg_energy >= 7 and avg_adherence >= 0.8:
            return "improving"
        elif avg_energy >= 5 and avg_adherence >= 0.6:
            return "stable"
        else:
            return "declining"

    async def _generate_ai_insights(self, profile: UserProfile, progress: ProgressMetrics,
                                    adherence: Dict) -> Dict:
        """Generate AI-powered insights about user's progress"""

        prompt = f"""You are an expert fitness coach analyzing a client's progress. Provide insights and recommendations.

CLIENT PROFILE:
- Goal: {profile.primary_goal.value}
- Week {profile.week_in_phase} of {profile.current_phase.value} phase
- Experience: {profile.experience_level}
- Training: {profile.training_days_per_week} days/week

PROGRESS DATA (Last 4 weeks):
- Weight change: {progress.weight_change} lbs
- Body fat change: {progress.bf_change}% (if available)
- Adherence rate: {progress.adherence_rate:.1%}
- Energy level: {progress.energy_level}/10
- Strength trend: {progress.strength_trend}
- Plateau detected: {progress.plateau_detected}

ADHERENCE BREAKDOWN:
- Calorie accuracy: {adherence.get('calorie_accuracy', 0):.1%}
- Protein target hits: {adherence.get('protein_hits', 0):.1%}
- Meal timing consistency: {adherence.get('meal_timing', 0):.1%}

Provide insights in this JSON format:
{{
    "progress_assessment": "brief overall assessment",
    "key_insights": ["insight 1", "insight 2", "insight 3"],
    "areas_of_concern": ["concern 1", "concern 2"],
    "positive_highlights": ["highlight 1", "highlight 2"],
    "motivation": "encouraging message",
    "next_phase_recommendation": "what to focus on next"
}}

Keep insights specific, actionable, and encouraging."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system",
                     "content": "You are a professional fitness coach providing scientific, personalized guidance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            insights_text = response.choices[0].message.content.strip()

            # Parse JSON response
            try:
                insights = json.loads(insights_text)
                return insights
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "progress_assessment": "Analysis in progress",
                    "key_insights": ["Continue tracking consistently for better insights"],
                    "areas_of_concern": [],
                    "positive_highlights": ["Staying committed to your goals"],
                    "motivation": "Keep up the great work!",
                    "next_phase_recommendation": "Focus on consistency"
                }

        except Exception as e:
            print(f"❌ Error generating AI insights: {e}")
            return {
                "progress_assessment": "Unable to generate insights",
                "key_insights": ["Track consistently for personalized feedback"],
                "areas_of_concern": [],
                "positive_highlights": ["You're taking steps toward your goals"],
                "motivation": "Every step counts toward your success!",
                "next_phase_recommendation": "Continue with current plan"
            }

    def _calculate_macro_adjustments(self, profile: UserProfile, progress: ProgressMetrics,
                                     adherence: Dict) -> Dict:
        """Calculate if macro adjustments are needed based on progress"""

        adjustments = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "reasoning": []
        }

        # Check if plateau detected
        if progress.plateau_detected and progress.weeks_at_plateau >= 3:
            if profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
                adjustments["calories"] = -150
                adjustments["carbs"] = -25
                adjustments["reasoning"].append("Plateau detected: reducing calories to restart fat loss")

            elif profile.primary_goal in [FitnessGoal.MUSCLE_GAIN, FitnessGoal.BULKING]:
                adjustments["calories"] = +200
                adjustments["carbs"] = +35
                adjustments["reasoning"].append("Plateau detected: increasing calories to support muscle growth")

        # Check adherence issues
        if adherence.get('protein_hits', 1.0) < 0.7:
            adjustments["protein"] = +15
            adjustments["reasoning"].append("Low protein adherence: increasing target for better compliance")

        # Check energy levels
        if progress.energy_level < 4 and profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            adjustments["carbs"] = +20
            adjustments["reasoning"].append("Low energy: adding carbs for training performance")

        # Check rapid weight loss/gain
        weekly_rate = abs(progress.weight_change) / 4  # 4 weeks of data

        if profile.primary_goal == FitnessGoal.FAT_LOSS and weekly_rate > 2.0:
            adjustments["calories"] = +100
            adjustments["reasoning"].append("Weight loss too rapid: slowing rate for muscle preservation")

        elif profile.primary_goal == FitnessGoal.MUSCLE_GAIN and weekly_rate > 1.5:
            adjustments["calories"] = -100
            adjustments["reasoning"].append("Weight gain too rapid: reducing rate to minimize fat gain")

        return adjustments

    # Database helper methods
    async def _save_fitness_profile(self, profile: UserProfile):
        """Save user fitness profile to database"""
        try:
            data = {
                "user_id": profile.user_id,
                "primary_goal": profile.primary_goal.value,
                "current_weight": profile.current_weight,
                "target_weight": profile.target_weight,
                "body_fat_percentage": profile.body_fat_percentage,
                "target_body_fat": profile.target_body_fat,
                "activity_level": profile.activity_level.value,
                "timeline_weeks": profile.timeline_weeks,
                "training_days_per_week": profile.training_days_per_week,
                "experience_level": profile.experience_level,
                "current_phase": profile.current_phase.value,
                "week_in_phase": profile.week_in_phase,
                "updated_at": datetime.now().isoformat()
            }

            result = supabase.table("user_fitness_profiles").upsert(data).execute()
            return result.data

        except Exception as e:
            print(f"❌ Error saving fitness profile: {e}")
            raise e

    async def _save_macro_targets(self, user_id: str, targets: MacroTargets):
        """Save macro targets to user preferences"""
        try:
            data = {
                "user_id": user_id,
                "daily_calories": targets.calories,
                "daily_protein": targets.protein,
                "daily_carbs": targets.carbs,
                "daily_fat": targets.fat,
                "daily_fiber": targets.fiber,
                "macro_strategy": {
                    "protein_priority": targets.protein_priority,
                    "carb_timing": targets.carb_timing,
                    "meal_distribution": targets.meal_distribution
                },
                "updated_at": datetime.now().isoformat()
            }

            # Update existing preferences or insert new
            result = supabase.table("user_preferences") \
                .upsert(data, on_conflict="user_id") \
                .execute()

            return result.data

        except Exception as e:
            print(f"❌ Error saving macro targets: {e}")
            raise e

    def _create_user_profile(self, user_id: str, assessment_data: Dict) -> UserProfile:
        """Create UserProfile from assessment data"""

        return UserProfile(
            user_id=user_id,
            age=assessment_data.get("age", 30),
            gender=assessment_data.get("gender", "male"),
            height_cm=assessment_data.get("height_cm", 175),
            current_weight=assessment_data.get("current_weight", 70),
            target_weight=assessment_data.get("target_weight", 75),
            body_fat_percentage=assessment_data.get("body_fat_percentage"),
            target_body_fat=assessment_data.get("target_body_fat"),
            activity_level=ActivityLevel(assessment_data.get("activity_level", "moderately_active")),
            primary_goal=FitnessGoal(assessment_data.get("primary_goal", "maintenance")),
            timeline_weeks=assessment_data.get("timeline_weeks", 12),
            training_days_per_week=assessment_data.get("training_days_per_week", 3),
            experience_level=assessment_data.get("experience_level", "beginner"),
            current_phase=TrainingPhase.FOUNDATION,
            week_in_phase=1
        )