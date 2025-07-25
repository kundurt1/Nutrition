# nutrition-backend/services/nutrition_coach.py
# Complete implementation with all helper methods - FINAL FIXED VERSION

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
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"


class TrainingPhase(Enum):
    FOUNDATION = "foundation"
    PROGRESSION = "progression"
    INTENSIFICATION = "intensification"
    DELOAD = "deload"


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
    # Additional fields for assessment and calculations
    current_injuries: Optional[List[str]] = None
    supplement_preferences: Optional[List[str]] = None
    meal_prep_experience: Optional[str] = "beginner"
    # These are calculated internally but not saved to database
    bmr: Optional[float] = None
    tdee: Optional[float] = None


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

        self.activity_multipliers = {
            ActivityLevel.SEDENTARY: 1.2,
            ActivityLevel.LIGHTLY_ACTIVE: 1.375,
            ActivityLevel.MODERATELY_ACTIVE: 1.55,
            ActivityLevel.VERY_ACTIVE: 1.725,
            ActivityLevel.EXTREMELY_ACTIVE: 1.9
        }

    async def assess_user_goals(self, user_id: str, assessment_data: Dict) -> Dict:
        """Complete fitness goal assessment and profile creation"""

        profile = self._create_user_profile(user_id, assessment_data)
        macro_targets = self.calculate_personalized_macros(profile)

        await self._save_fitness_profile(profile)
        await self._save_macro_targets(user_id, macro_targets)

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

        # Convert weight to kg for BMR calculation
        weight_kg = profile.current_weight * 0.453592

        if profile.gender.lower() == 'male':
            bmr = (10 * weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) + 5
        else:
            bmr = (10 * weight_kg) + (6.25 * profile.height_cm) - (5 * profile.age) - 161

        tdee = bmr * self.activity_multipliers[profile.activity_level]
        target_calories = self._adjust_calories_for_goal(tdee, profile)
        macros = self._distribute_macros(target_calories, profile)

        return macros

    def _adjust_calories_for_goal(self, tdee: float, profile: UserProfile) -> int:
        """Adjust calories based on specific fitness goals"""

        goal_adjustments = {
            FitnessGoal.FAT_LOSS: -0.20,
            FitnessGoal.CUTTING: -0.25,
            FitnessGoal.MUSCLE_GAIN: +0.15,
            FitnessGoal.BULKING: +0.20,
            FitnessGoal.STRENGTH_BUILDING: +0.10,
            FitnessGoal.BODY_RECOMPOSITION: 0.0,
            FitnessGoal.MAINTENANCE: 0.0,
            FitnessGoal.ENDURANCE: +0.05
        }

        adjustment = goal_adjustments.get(profile.primary_goal, 0.0)

        if profile.experience_level == "beginner" and adjustment > 0:
            adjustment *= 0.8
        elif profile.experience_level == "advanced" and adjustment < 0:
            adjustment *= 1.2

        if profile.timeline_weeks < 12 and adjustment < 0:
            adjustment *= 1.3

        return int(tdee * (1 + adjustment))

    def _distribute_macros(self, calories: int, profile: UserProfile) -> MacroTargets:
        """Intelligent macro distribution based on goals"""

        protein_per_kg = self._get_protein_requirement(profile)
        weight_kg = profile.current_weight * 0.453592
        protein_grams = weight_kg * protein_per_kg
        protein_calories = protein_grams * 4

        fat_percentage = self._get_fat_percentage(profile)
        fat_calories = calories * fat_percentage
        fat_grams = fat_calories / 9

        carb_calories = calories - protein_calories - fat_calories
        carb_grams = max(carb_calories / 4, 50)

        if carb_grams < 100 and profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
            carb_grams = 100
            carb_calories = carb_grams * 4
            fat_calories = calories - protein_calories - carb_calories
            fat_grams = fat_calories / 9

        fiber_grams = max(25, calories / 80)
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

        profile = await self._get_user_profile(user_id)
        progress = await self._analyze_recent_progress(user_id)
        adherence = await self._calculate_adherence_metrics(user_id)

        insights = await self._generate_ai_insights(profile, progress, adherence)
        adjustments = self._calculate_macro_adjustments(profile, progress, adherence)
        recommendations = await self._generate_coaching_recommendations(profile, progress, adherence, insights)

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

    async def generate_goal_oriented_recipes(self, user_id: str, meal_type: str, training_day: bool = False) -> Dict:
        """Generate recipes optimized for user's specific goals and meal timing"""

        profile = await self._get_user_profile(user_id)
        macro_targets = await self._get_current_macro_targets(user_id)

        meal_macros = self._calculate_meal_specific_macros(macro_targets, meal_type, training_day, profile)
        coaching_prompt = self._build_coaching_recipe_prompt(profile, meal_macros, meal_type, training_day)
        recipe_response = await self._call_openai_for_recipe(coaching_prompt)
        recipe = self._parse_and_enhance_recipe(recipe_response, meal_macros, profile)

        return {
            "recipe": recipe,
            "coaching_notes": self._generate_recipe_coaching_notes(profile, meal_type),
            "meal_macros": meal_macros,
            "goal_alignment": self._assess_recipe_goal_alignment(recipe, profile)
        }

    def _build_coaching_recipe_prompt(self, profile: UserProfile, meal_macros: Dict, meal_type: str,
                                      training_day: bool) -> str:
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
            # Return a fallback recipe structure
            return f"""RECIPE NAME: Goal-Optimized {prompt.split('creating a ')[1].split(' recipe')[0].title()}

NUTRITION FACTS:
- Calories: 400
- Protein: 30g
- Carbs: 40g
- Fat: 12g
- Fiber: 8g

INGREDIENTS:
- 6 oz lean protein source
- 1 cup complex carbohydrates
- 2 cups vegetables
- 1 tbsp healthy fat

DIRECTIONS:
1. Prepare protein using preferred cooking method
2. Cook carbohydrates according to package instructions
3. Steam or sauté vegetables
4. Combine and season to taste

COACHING NOTES:
This meal supports your fitness goals with balanced macronutrients

MEAL PREP TIPS:
Can be prepared in advance and stored for 3-4 days"""

    def _calculate_meal_specific_macros(self, daily_targets: MacroTargets, meal_type: str, training_day: bool,
                                        profile: UserProfile) -> Dict:
        """Calculate macro targets for specific meal based on timing and goals"""

        distribution = daily_targets.meal_distribution

        if meal_type in distribution:
            meal_percentage = distribution[meal_type]
        else:
            meal_distributions = {
                "breakfast": 0.25,
                "lunch": 0.30,
                "pre_workout": 0.15,
                "post_workout": 0.20,
                "dinner": 0.25,
                "snack": 0.15
            }
            meal_percentage = meal_distributions.get(meal_type, 0.25)

        carb_multiplier = protein_multiplier = fat_multiplier = 1.0

        if training_day and meal_type == "pre_workout":
            carb_multiplier = 1.3
            protein_multiplier = 0.8
            fat_multiplier = 0.5
        elif training_day and meal_type == "post_workout":
            carb_multiplier = 1.4
            protein_multiplier = 1.2
            fat_multiplier = 0.6
        elif not training_day and profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            carb_multiplier = 0.7
            protein_multiplier = 1.1
            fat_multiplier = 1.2

        return {
            "calories": int(daily_targets.calories * meal_percentage),
            "protein": round(daily_targets.protein * meal_percentage * protein_multiplier, 1),
            "carbs": round(daily_targets.carbs * meal_percentage * carb_multiplier, 1),
            "fat": round(daily_targets.fat * meal_percentage * fat_multiplier, 1),
            "fiber": round(daily_targets.fiber * meal_percentage, 1),
            "protein_priority": daily_targets.protein_priority,
            "carb_timing": daily_targets.carb_timing
        }

    # Helper methods
    async def _get_user_profile(self, user_id: str):
        """Get user fitness profile from database"""
        try:
            result = supabase.table("user_fitness_profiles") \
                .select("*") \
                .eq("user_id", user_id) \
                .limit(1) \
                .execute()

            if result.data:
                profile_data = result.data[0]
                return UserProfile(
                    user_id=profile_data['user_id'],
                    age=profile_data['age'],
                    gender=profile_data['gender'],
                    height_cm=profile_data['height_cm'],
                    current_weight=profile_data['current_weight'],
                    target_weight=profile_data['target_weight'],
                    body_fat_percentage=profile_data.get('body_fat_percentage'),
                    target_body_fat=profile_data.get('target_body_fat'),
                    activity_level=ActivityLevel(profile_data['activity_level']),
                    primary_goal=FitnessGoal(profile_data['primary_goal']),
                    timeline_weeks=profile_data['timeline_weeks'],
                    training_days_per_week=profile_data['training_days_per_week'],
                    experience_level=profile_data['experience_level'],
                    current_phase=TrainingPhase(profile_data.get('current_phase', 'foundation')),
                    week_in_phase=profile_data.get('week_in_phase', 1)
                )
            return None
        except Exception as e:
            print(f"❌ Error getting user profile: {e}")
            return None

    async def _get_current_macro_targets(self, user_id: str):
        """Get current macro targets from user preferences - Fixed version"""
        try:
            result = supabase.table("user_preferences") \
                .select("daily_calories, daily_protein, daily_carbs, daily_fat, daily_fiber, macro_strategy") \
                .eq("user_id", user_id) \
                .limit(1) \
                .execute()

            if result.data and len(result.data) > 0:
                data = result.data[0]
                macro_strategy = data.get("macro_strategy", {}) or {}  # Handle None case

                return MacroTargets(
                    calories=data.get("daily_calories") or 0,
                    protein=data.get("daily_protein") or 0,
                    carbs=data.get("daily_carbs") or 0,
                    fat=data.get("daily_fat") or 0,
                    fiber=data.get("daily_fiber") or 0,
                    protein_priority=macro_strategy.get("protein_priority", "Evenly distributed"),
                    carb_timing=macro_strategy.get("carb_timing", "Evenly distributed"),
                    meal_distribution=macro_strategy.get("meal_distribution", {
                        "breakfast": 0.25,
                        "lunch": 0.35,
                        "snack": 0.15,
                        "dinner": 0.25
                    })
                )

            # Return default macro targets if none exist
            print(f"⚠️ No macro targets found for user {user_id}, returning defaults")
            return MacroTargets(
                calories=2000,
                protein=150.0,
                carbs=200.0,
                fat=70.0,
                fiber=25.0,
                protein_priority="Evenly distributed",
                carb_timing="Evenly distributed",
                meal_distribution={
                    "breakfast": 0.25,
                    "lunch": 0.35,
                    "snack": 0.15,
                    "dinner": 0.25
                }
            )

        except Exception as e:
            print(f"❌ Error getting macro targets: {e}")
            # Return default macro targets on error
            return MacroTargets(
                calories=2000,
                protein=150.0,
                carbs=200.0,
                fat=70.0,
                fiber=25.0,
                protein_priority="Evenly distributed",
                carb_timing="Evenly distributed",
                meal_distribution={
                    "breakfast": 0.25,
                    "lunch": 0.35,
                    "snack": 0.15,
                    "dinner": 0.25
                }
            )
    async def _calculate_adherence_metrics(self, user_id: str) -> Dict:
        """Calculate user's adherence metrics from recent data"""
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            try:
                nutrition_result = supabase.table("nutrition_entries") \
                    .select("*") \
                    .eq("user_id", user_id) \
                    .gte("created_at", week_ago) \
                    .execute()

                entries = nutrition_result.data or []

                if not entries:
                    return {"calorie_accuracy": 0.75, "protein_hits": 0.80, "meal_timing": 0.85}

                total_entries = len(entries)
                return {
                    "calorie_accuracy": min(total_entries * 0.1 + 0.5, 1.0),
                    "protein_hits": min(total_entries * 0.12 + 0.6, 1.0),
                    "meal_timing": 0.85
                }

            except Exception:
                return {"calorie_accuracy": 0.75, "protein_hits": 0.80, "meal_timing": 0.85}

        except Exception as e:
            print(f"❌ Error calculating adherence: {e}")
            return {"calorie_accuracy": 0.75, "protein_hits": 0.80, "meal_timing": 0.85}

    async def _analyze_recent_progress(self, user_id: str) -> ProgressMetrics:
        """Analyze user's recent progress data"""
        try:
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

            weights = [entry['weight'] for entry in entries if entry.get('weight')]
            weight_change = weights[-1] - weights[0] if len(weights) >= 2 else 0.0

            bf_readings = [entry['body_fat_estimate'] for entry in entries if entry.get('body_fat_estimate')]
            bf_change = bf_readings[-1] - bf_readings[0] if len(bf_readings) >= 2 else None

            adherence_scores = [entry['adherence_score'] for entry in entries if entry.get('adherence_score')]
            avg_adherence = sum(adherence_scores) / len(adherence_scores) if adherence_scores else 0.0

            energy_levels = [entry['energy_level'] for entry in entries if entry.get('energy_level')]
            avg_energy = sum(energy_levels) / len(energy_levels) if energy_levels else 5.0

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

    async def _generate_ai_insights(self, profile: UserProfile, progress: ProgressMetrics, adherence: Dict) -> Dict:
        """Generate AI-powered insights about user's progress"""

        # If OpenAI is not available, return structured insights
        try:
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

            try:
                insights = json.loads(insights_text)
                return insights
            except json.JSONDecodeError:
                pass

        except Exception as e:
            print(f"❌ Error generating AI insights: {e}")

        # Fallback insights based on data
        insights = {
            "progress_assessment": "Analysis in progress",
            "key_insights": [],
            "areas_of_concern": [],
            "positive_highlights": [],
            "motivation": "Keep up the great work!",
            "next_phase_recommendation": "Focus on consistency"
        }

        # Generate insights based on progress data
        if progress.adherence_rate >= 0.8:
            insights["positive_highlights"].append("Excellent adherence to nutrition plan")
        elif progress.adherence_rate < 0.6:
            insights["areas_of_concern"].append("Consider meal prep strategies to improve consistency")

        if progress.energy_level >= 8:
            insights["positive_highlights"].append("Energy levels are optimal")
        elif progress.energy_level < 5:
            insights["areas_of_concern"].append("Low energy levels - consider adjusting carb timing")

        if abs(progress.weight_change) > 0.5:
            insights["key_insights"].append(f"Weight trend: {progress.weight_change:+.1f} lbs over 4 weeks")

        return insights

    def _calculate_macro_adjustments(self, profile: UserProfile, progress: ProgressMetrics, adherence: Dict) -> Dict:
        """Calculate if macro adjustments are needed based on progress"""

        adjustments = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "reasoning": []
        }

        if progress.plateau_detected and progress.weeks_at_plateau >= 3:
            if profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
                adjustments["calories"] = -150
                adjustments["carbs"] = -25
                adjustments["reasoning"].append("Plateau detected: reducing calories to restart fat loss")
            elif profile.primary_goal in [FitnessGoal.MUSCLE_GAIN, FitnessGoal.BULKING]:
                adjustments["calories"] = +200
                adjustments["carbs"] = +35
                adjustments["reasoning"].append("Plateau detected: increasing calories to support muscle growth")

        if adherence.get('protein_hits', 1.0) < 0.7:
            adjustments["protein"] = +15
            adjustments["reasoning"].append("Low protein adherence: increasing target for better compliance")

        if progress.energy_level < 4 and profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            adjustments["carbs"] = +20
            adjustments["reasoning"].append("Low energy: adding carbs for training performance")

        weekly_rate = abs(progress.weight_change) / 4

        if profile.primary_goal == FitnessGoal.FAT_LOSS and weekly_rate > 2.0:
            adjustments["calories"] = +100
            adjustments["reasoning"].append("Weight loss too rapid: slowing rate for muscle preservation")
        elif profile.primary_goal == FitnessGoal.MUSCLE_GAIN and weekly_rate > 1.5:
            adjustments["calories"] = -100
            adjustments["reasoning"].append("Weight gain too rapid: reducing rate to minimize fat gain")

        return adjustments

    async def _save_fitness_profile(self, profile):
        """Save fitness profile to database - Fixed version without non-existent columns"""
        try:
            # First, check if a profile already exists for this user
            existing = supabase.table("user_fitness_profiles").select("*").eq("user_id", profile.user_id).execute()

            # Only include fields that exist in the database table
            profile_data = {
                "user_id": profile.user_id,
                "age": profile.age,
                "gender": profile.gender,
                "height_cm": profile.height_cm,
                "current_weight": profile.current_weight,
                "target_weight": profile.target_weight,
                "body_fat_percentage": profile.body_fat_percentage,
                "target_body_fat": profile.target_body_fat,
                "activity_level": profile.activity_level.value,
                "primary_goal": profile.primary_goal.value,
                "experience_level": profile.experience_level,
                "training_days_per_week": profile.training_days_per_week,
                "current_phase": profile.current_phase.value,
                "week_in_phase": profile.week_in_phase,
                "timeline_weeks": profile.timeline_weeks,
                "updated_at": datetime.now().isoformat()
            }

            # Note: current_injuries, supplement_preferences, and meal_prep_experience
            # are stored in the UserProfile object for internal use but not saved to database
            # as these columns don't exist in the current database schema

            if existing.data and len(existing.data) > 0:
                # Update existing profile
                result = supabase.table("user_fitness_profiles") \
                    .update(profile_data) \
                    .eq("user_id", profile.user_id) \
                    .execute()
            else:
                # Insert new profile
                profile_data["created_at"] = datetime.now().isoformat()
                result = supabase.table("user_fitness_profiles") \
                    .insert(profile_data) \
                    .execute()

            if not result.data:
                raise Exception("Failed to save fitness profile")

            print(f"✅ Saved fitness profile for user {profile.user_id}")
            return result.data[0]

        except Exception as e:
            print(f"❌ Error saving fitness profile: {e}")
            raise e

    async def _save_macro_targets(self, user_id: str, targets: MacroTargets):
        """Save macro targets to user preferences - Fixed version without upsert"""
        try:
            # First, check if preferences already exist for this user
            existing = supabase.table("user_preferences").select("*").eq("user_id", user_id).execute()

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

            if existing.data and len(existing.data) > 0:
                # Update existing preferences
                result = supabase.table("user_preferences") \
                    .update(data) \
                    .eq("user_id", user_id) \
                    .execute()
            else:
                # Insert new preferences
                data["created_at"] = datetime.now().isoformat()
                result = supabase.table("user_preferences") \
                    .insert(data) \
                    .execute()

            if not result.data:
                raise Exception("Failed to save macro targets")

            print(f"✅ Saved macro targets for user {user_id}")
            return result.data

        except Exception as e:
            print(f"❌ Error saving macro targets: {e}")
            raise e

    def _create_user_profile(self, user_id: str, assessment_data: Dict) -> UserProfile:
        """Create UserProfile from assessment data"""

        # Calculate BMR and TDEE
        weight_kg = assessment_data.get("current_weight", 70) * 0.453592
        height_cm = assessment_data.get("height_cm", 175)
        age = assessment_data.get("age", 30)
        gender = assessment_data.get("gender", "male")

        # Calculate BMR using Mifflin-St Jeor equation
        if gender.lower() == 'male':
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
        else:
            bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

        # Calculate TDEE
        activity_level = ActivityLevel(assessment_data.get("activity_level", "moderately_active"))
        tdee = bmr * self.activity_multipliers[activity_level]

        return UserProfile(
            user_id=user_id,
            age=assessment_data.get("age", 30),
            gender=assessment_data.get("gender", "male"),
            height_cm=assessment_data.get("height_cm", 175),
            current_weight=assessment_data.get("current_weight", 70),
            target_weight=assessment_data.get("target_weight", 75),
            body_fat_percentage=assessment_data.get("body_fat_percentage"),
            target_body_fat=assessment_data.get("target_body_fat"),
            activity_level=activity_level,
            primary_goal=FitnessGoal(assessment_data.get("primary_goal", "maintenance")),
            timeline_weeks=assessment_data.get("timeline_weeks", 12),
            training_days_per_week=assessment_data.get("training_days_per_week", 3),
            experience_level=assessment_data.get("experience_level", "beginner"),
            current_phase=TrainingPhase.FOUNDATION,
            week_in_phase=1,
            # Handle the additional fields that were missing
            current_injuries=assessment_data.get("current_injuries", []),
            supplement_preferences=assessment_data.get("supplement_preferences", []),
            meal_prep_experience=assessment_data.get("meal_prep_experience", "beginner"),
            bmr=bmr,
            tdee=tdee
        )

    # Additional helper methods for full functionality
    async def _should_run_weekly_analysis(self, user_id: str) -> bool:
        """Check if weekly analysis should be run"""
        try:
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()

            result = supabase.table("coaching_insights") \
                .select("generated_at") \
                .eq("user_id", user_id) \
                .gte("generated_at", week_ago) \
                .limit(1) \
                .execute()

            return len(result.data or []) == 0

        except Exception as e:
            print(f"❌ Error checking weekly analysis: {e}")
            return True

    async def _save_coaching_insights(self, user_id: str, insights_data: Dict):
        """Save coaching insights to database"""
        try:
            data = {
                "user_id": user_id,
                "week_number": insights_data.get("week_number", 1),
                "insights": insights_data.get("insights", {}),
                "recommendations": insights_data.get("recommendations", {}),
                "macro_adjustments": insights_data.get("adjustments", {}),
                "generated_at": datetime.now().isoformat()
            }

            result = supabase.table("coaching_insights").insert(data).execute()
            return result.data

        except Exception as e:
            print(f"❌ Error saving coaching insights: {e}")
            return None

    async def _generate_initial_coaching_plan(self, profile: UserProfile, macro_targets: MacroTargets) -> Dict:
        """Generate initial coaching plan for new users"""

        return {
            "phase_plan": {
                "current_phase": profile.current_phase.value,
                "week_in_phase": profile.week_in_phase,
                "total_phases": 4,
                "phase_goals": {
                    "foundation": "Establish consistent eating habits and baseline fitness",
                    "progression": "Increase training intensity and refine nutrition timing",
                    "intensification": "Peak performance and goal achievement focus",
                    "deload": "Recovery and preparation for next cycle"
                }
            },
            "nutrition_strategy": {
                "meal_frequency": "3 main meals + 1-2 snacks" if profile.primary_goal in [FitnessGoal.MUSCLE_GAIN,
                                                                                          FitnessGoal.BULKING] else "3 main meals + 1 snack",
                "hydration_target": "Half your body weight in ounces of water daily",
                "supplement_recommendations": self._get_supplement_recommendations(profile.primary_goal)
            },
            "weekly_focus": [
                "Track all meals and snacks consistently",
                "Hit protein targets daily for muscle preservation/growth",
                "Time carbohydrates around training sessions",
                "Log progress weekly for adaptive adjustments"
            ]
        }

    def _get_supplement_recommendations(self, goal: FitnessGoal) -> List[str]:
        """Get supplement recommendations based on goals"""

        base_supplements = ["Multivitamin", "Omega-3", "Vitamin D3"]

        goal_specific = {
            FitnessGoal.STRENGTH_BUILDING: ["Creatine monohydrate", "Whey protein"],
            FitnessGoal.MUSCLE_GAIN: ["Creatine monohydrate", "Whey protein", "Casein protein"],
            FitnessGoal.FAT_LOSS: ["Green tea extract", "L-Carnitine"],
            FitnessGoal.CUTTING: ["Caffeine", "Green tea extract", "BCAA"],
            FitnessGoal.BODY_RECOMPOSITION: ["Creatine monohydrate", "Whey protein"],
            FitnessGoal.BULKING: ["Creatine monohydrate", "Mass gainer", "Digestive enzymes"],
            FitnessGoal.ENDURANCE: ["Beta-alanine", "Citrulline malate"]
        }

        return base_supplements + goal_specific.get(goal, [])

    def _estimate_goal_timeline(self, profile: UserProfile) -> str:
        """Estimate realistic timeline for goal achievement"""

        weight_diff = abs(profile.target_weight - profile.current_weight)

        timeline_estimates = {
            FitnessGoal.FAT_LOSS: f"{max(8, int(weight_diff * 2))} weeks for sustainable fat loss",
            FitnessGoal.CUTTING: f"{max(6, int(weight_diff * 1.5))} weeks for aggressive cut",
            FitnessGoal.MUSCLE_GAIN: f"{max(12, int(weight_diff * 4))} weeks for lean muscle gain",
            FitnessGoal.BULKING: f"{max(12, int(weight_diff * 3))} weeks for mass gain",
            FitnessGoal.STRENGTH_BUILDING: "12-16 weeks for significant strength gains",
            FitnessGoal.BODY_RECOMPOSITION: "16-24 weeks for body recomposition",
            FitnessGoal.MAINTENANCE: "Ongoing lifestyle maintenance"
        }

        return timeline_estimates.get(profile.primary_goal, f"{profile.timeline_weeks} weeks")

    def _calculate_success_probability(self, profile: UserProfile) -> float:
        """Calculate probability of success based on profile factors"""

        base_probability = 0.7

        experience_modifiers = {
            "beginner": 0.85,
            "intermediate": 0.75,
            "advanced": 0.65
        }

        probability = base_probability * experience_modifiers.get(profile.experience_level, 0.75)

        weight_change_per_week = abs(profile.target_weight - profile.current_weight) / profile.timeline_weeks

        if weight_change_per_week > 2.0:
            probability *= 0.6
        elif weight_change_per_week < 0.5:
            probability *= 0.9

        if profile.training_days_per_week >= 4:
            probability *= 1.1
        elif profile.training_days_per_week < 2:
            probability *= 0.8

        return min(probability, 0.95)

    def _parse_and_enhance_recipe(self, recipe_response: str, meal_macros: Dict, profile: UserProfile) -> Dict:
        """Parse OpenAI recipe response and enhance with coaching data"""

        lines = recipe_response.split('\n')

        recipe = {
            "name": "Goal-Optimized Recipe",
            "ingredients": [],
            "directions": [],
            "nutrition": meal_macros,
            "coaching_notes": [],
            "prep_tips": []
        }

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("RECIPE NAME:"):
                recipe["name"] = line.replace("RECIPE NAME:", "").strip()
            elif line.startswith("INGREDIENTS:"):
                current_section = "ingredients"
            elif line.startswith("DIRECTIONS:"):
                current_section = "directions"
            elif line.startswith("COACHING NOTES:"):
                current_section = "coaching_notes"
            elif line.startswith("MEAL PREP TIPS:"):
                current_section = "prep_tips"
            elif current_section == "ingredients" and line.startswith("-"):
                recipe["ingredients"].append(line[1:].strip())
            elif current_section == "directions" and (line[0].isdigit() or line.startswith("-")):
                recipe["directions"].append(line.split(".", 1)[-1].strip() if "." in line else line[1:].strip())
            elif current_section == "coaching_notes":
                recipe["coaching_notes"].append(line)
            elif current_section == "prep_tips":
                recipe["prep_tips"].append(line)

        return recipe

    def _generate_recipe_coaching_notes(self, profile: UserProfile, meal_type: str) -> List[str]:
        """Generate coaching notes for the recipe"""

        notes = []

        goal_notes = {
            FitnessGoal.STRENGTH_BUILDING: "This meal supports muscle protein synthesis and provides sustained energy for training",
            FitnessGoal.FAT_LOSS: "High protein and fiber content promote satiety while supporting lean muscle maintenance",
            FitnessGoal.MUSCLE_GAIN: "Optimized protein and carbohydrate ratio for maximum muscle growth",
            FitnessGoal.BODY_RECOMPOSITION: "Balanced macros support both fat loss and muscle gain goals"
        }

        notes.append(goal_notes.get(profile.primary_goal, "Balanced nutrition to support your fitness goals"))

        if meal_type == "pre_workout":
            notes.append("Consume 30-60 minutes before training for optimal energy")
        elif meal_type == "post_workout":
            notes.append("Eat within 2 hours post-workout for optimal recovery")
        elif meal_type == "breakfast":
            notes.append("Start your day with sustained energy and muscle-building nutrients")

        return notes

    def _assess_recipe_goal_alignment(self, recipe: Dict, profile: UserProfile) -> float:
        """Assess how well the recipe aligns with user's goals"""

        base_score = 0.8

        nutrition = recipe.get("nutrition", {})
        protein_ratio = nutrition.get("protein", 0) * 4 / max(nutrition.get("calories", 1), 1)

        if profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
            if protein_ratio >= 0.25:
                base_score += 0.1
        elif profile.primary_goal in [FitnessGoal.FAT_LOSS, FitnessGoal.CUTTING]:
            if protein_ratio >= 0.30:
                base_score += 0.1

        return min(base_score, 1.0)

    async def _generate_coaching_recommendations(self, profile: UserProfile, progress: ProgressMetrics,
                                                 adherence: Dict, insights: Dict) -> Dict:
        """Generate specific coaching recommendations"""

        recommendations = {
            "immediate_actions": [],
            "weekly_focus": [],
            "long_term_strategies": [],
            "focus_areas": []
        }

        if adherence.get("protein_hits", 1.0) < 0.7:
            recommendations["immediate_actions"].append("Increase protein intake - aim for protein at every meal")
            recommendations["focus_areas"].append("Protein consistency")

        if adherence.get("calorie_accuracy", 1.0) < 0.7:
            recommendations["weekly_focus"].append("Track all meals and snacks more consistently")
            recommendations["focus_areas"].append("Meal tracking")

        if progress.energy_level < 5:
            recommendations["immediate_actions"].append("Increase carbohydrate intake around workouts")
            recommendations["weekly_focus"].append("Monitor sleep quality and stress levels")

        if progress.plateau_detected:
            recommendations["immediate_actions"].append("Consider a structured refeed day")
            recommendations["long_term_strategies"].append("Implement cycling approach to nutrition")

        if profile.primary_goal == FitnessGoal.FAT_LOSS:
            recommendations["weekly_focus"].append("Focus on high-volume, low-calorie foods for satiety")
        elif profile.primary_goal in [FitnessGoal.MUSCLE_GAIN, FitnessGoal.STRENGTH_BUILDING]:
            recommendations["weekly_focus"].append("Ensure adequate recovery nutrition between sessions")

        return recommendations

    def _format_progress_summary(self, progress: ProgressMetrics) -> Dict:
        """Format progress metrics for display"""

        return {
            "weight_change": progress.weight_change,
            "adherence_rate": progress.adherence_rate,
            "energy_level": progress.energy_level,
            "strength_trend": progress.strength_trend.replace("_", " ").title(),
            "plateau_detected": progress.plateau_detected,
            "weeks_at_plateau": progress.weeks_at_plateau if progress.plateau_detected else 0
        }