# nutrition-backend/routers/nutritionCoach.py
# Complete router implementation - FINAL VERSION

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum

from services.nutrition_coach import NutritionCoachService, FitnessGoal, ActivityLevel
from database import supabase

router = APIRouter()
coach_service = NutritionCoachService()


# Request Models
class FitnessAssessmentRequest(BaseModel):
    user_id: str
    age: int
    gender: str
    height_cm: float
    current_weight: float
    target_weight: float
    body_fat_percentage: Optional[float] = None
    target_body_fat: Optional[float] = None
    activity_level: str
    primary_goal: str
    timeline_weeks: int
    training_days_per_week: int
    experience_level: str
    current_injuries: Optional[List[str]] = []
    supplement_preferences: Optional[List[str]] = []
    meal_prep_experience: Optional[str] = "beginner"


class ProgressEntryRequest(BaseModel):
    user_id: str
    weight: Optional[float] = None
    body_fat_estimate: Optional[float] = None
    energy_level: Optional[int] = None
    adherence_score: Optional[float] = None
    strength_notes: Optional[str] = None
    mood_rating: Optional[int] = None
    sleep_quality: Optional[int] = None
    notes: Optional[str] = None
    progress_photos: Optional[List[str]] = []


class GoalOrientedRecipeRequest(BaseModel):
    user_id: str
    meal_type: str
    training_day: bool = False
    specific_macros: Optional[Dict[str, float]] = None
    dietary_restrictions: Optional[List[str]] = []
    cuisine_preference: Optional[str] = None
    prep_time_max: Optional[int] = None
    serving_size: Optional[int] = 1


class MacroAdjustmentRequest(BaseModel):
    user_id: str
    adjustment_reason: str
    calorie_change: Optional[int] = None
    protein_change: Optional[float] = None
    carb_change: Optional[float] = None
    fat_change: Optional[float] = None
    temporary_adjustment: bool = False


# Utility functions
def _get_goal_description(goal):
    """Get description for a fitness goal"""
    descriptions = {
        FitnessGoal.STRENGTH_BUILDING: "Build muscle and increase strength with progressive overload",
        FitnessGoal.FAT_LOSS: "Lose body fat while preserving muscle mass",
        FitnessGoal.MUSCLE_GAIN: "Maximize muscle growth and size",
        FitnessGoal.BODY_RECOMPOSITION: "Lose fat and gain muscle simultaneously",
        FitnessGoal.CUTTING: "Achieve a lean, defined physique",
        FitnessGoal.BULKING: "Gain weight and muscle mass efficiently",
        FitnessGoal.MAINTENANCE: "Maintain current physique and health",
        FitnessGoal.ENDURANCE: "Improve cardiovascular fitness and endurance"
    }
    return descriptions.get(goal, "Achieve your fitness goals")


def _get_typical_timeline(goal):
    """Get typical timeline for a fitness goal"""
    timelines = {
        FitnessGoal.STRENGTH_BUILDING: "12-16 weeks",
        FitnessGoal.FAT_LOSS: "8-16 weeks",
        FitnessGoal.MUSCLE_GAIN: "12-20 weeks",
        FitnessGoal.BODY_RECOMPOSITION: "16-24 weeks",
        FitnessGoal.CUTTING: "8-12 weeks",
        FitnessGoal.BULKING: "16-24 weeks",
        FitnessGoal.MAINTENANCE: "Ongoing",
        FitnessGoal.ENDURANCE: "8-12 weeks"
    }
    return timelines.get(goal, "12-16 weeks")


def _get_activity_description(level):
    """Get description for activity level"""
    descriptions = {
        ActivityLevel.SEDENTARY: "Little or no exercise, desk job",
        ActivityLevel.LIGHTLY_ACTIVE: "Light exercise 1-3 days/week",
        ActivityLevel.MODERATELY_ACTIVE: "Moderate exercise 3-5 days/week",
        ActivityLevel.VERY_ACTIVE: "Heavy exercise 6-7 days/week",
        ActivityLevel.EXTREMELY_ACTIVE: "Very heavy exercise, physical job"
    }
    return descriptions.get(level, "Moderate activity level")


async def _apply_macro_adjustments(current_targets, request, profile):
    """Apply macro adjustments based on request"""

    if hasattr(current_targets, '__dict__'):
        targets = current_targets.__dict__.copy()
    else:
        targets = current_targets.copy()

    if request.calorie_change:
        targets["calories"] = targets.get("calories", 2000) + request.calorie_change
    if request.protein_change:
        targets["protein"] = targets.get("protein", 150) + request.protein_change
    if request.carb_change:
        targets["carbs"] = targets.get("carbs", 200) + request.carb_change
    if request.fat_change:
        targets["fat"] = targets.get("fat", 70) + request.fat_change

    return targets


async def _log_macro_adjustment(user_id: str, adjustment_data: Dict):
    """Log macro adjustment to database"""
    try:
        data = {
            "user_id": user_id,
            "adjustment_reason": adjustment_data.get("adjustment_reason", "manual"),
            "calorie_change": adjustment_data.get("calorie_change", 0),
            "protein_change": adjustment_data.get("protein_change", 0),
            "carb_change": adjustment_data.get("carb_change", 0),
            "fat_change": adjustment_data.get("fat_change", 0),
            "temporary_adjustment": adjustment_data.get("temporary_adjustment", False),
            "applied_at": datetime.now().isoformat()
        }

        supabase.table("macro_adjustments").insert(data).execute()

    except Exception as e:
        print(f"❌ Error logging macro adjustment: {e}")


async def _get_upcoming_recommendations(user_id: str) -> List[Dict]:
    """Get upcoming recommendations for the user"""

    profile = await coach_service._get_user_profile(user_id)
    if not profile:
        return []

    recommendations = [
        {
            "title": "Weekly Check-in",
            "description": "Log your progress and energy levels",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=7)).isoformat()
        },
        {
            "title": "Meal Prep Session",
            "description": "Prepare goal-oriented meals for the week",
            "priority": "medium",
            "due_date": (datetime.now() + timedelta(days=2)).isoformat()
        }
    ]

    if profile.primary_goal in [FitnessGoal.STRENGTH_BUILDING, FitnessGoal.MUSCLE_GAIN]:
        recommendations.append({
            "title": "Post-Workout Nutrition",
            "description": "Focus on protein within 2 hours of training",
            "priority": "high",
            "due_date": (datetime.now() + timedelta(days=1)).isoformat()
        })

    return recommendations


def _calculate_goal_timeline(profile, progress_analysis: Dict) -> Dict:
    """Calculate goal achievement timeline"""

    current_progress_rate = progress_analysis.get("progress_summary", {}).get("weight_change", 0)
    weeks_elapsed = profile.week_in_phase

    if current_progress_rate == 0:
        estimated_completion = profile.timeline_weeks
    else:
        weight_remaining = abs(profile.target_weight - profile.current_weight)
        weeks_remaining = weight_remaining / abs(
            current_progress_rate) if current_progress_rate != 0 else profile.timeline_weeks
        estimated_completion = min(weeks_remaining, profile.timeline_weeks * 1.5)

    return {
        "original_timeline": profile.timeline_weeks,
        "estimated_completion": int(estimated_completion),
        "weeks_elapsed": weeks_elapsed,
        "progress_percentage": min((weeks_elapsed / profile.timeline_weeks) * 100, 100),
        "on_track": abs(estimated_completion - profile.timeline_weeks) <= 2
    }


# Main API Endpoints

@router.post("/assess-fitness-goals")
async def assess_fitness_goals(request: FitnessAssessmentRequest):
    """Complete initial fitness assessment and create personalized coaching plan"""
    try:
        assessment_data = request.dict()
        result = await coach_service.assess_user_goals(request.user_id, assessment_data)

        return {
            "success": True,
            "message": "Fitness assessment completed successfully",
            "data": result
        }

    except Exception as e:
        print(f"❌ Error in fitness assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")


@router.get("/coaching-dashboard/{user_id}")
async def get_coaching_dashboard(user_id: str):
    """Get comprehensive coaching dashboard with all key metrics"""
    try:
        profile = await coach_service._get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404,
                                detail="User profile not found. Please complete fitness assessment first.")

        macro_targets = await coach_service._get_current_macro_targets(user_id)
        progress_analysis = await coach_service.weekly_progress_analysis(user_id)
        recommendations = await _get_upcoming_recommendations(user_id)
        goal_timeline = _calculate_goal_timeline(profile, progress_analysis)

        return {
            "success": True,
            "data": {
                "user_profile": {
                    "goal": profile.primary_goal.value,
                    "phase": profile.current_phase.value,
                    "week_in_phase": profile.week_in_phase,
                    "experience": profile.experience_level,
                    "timeline_weeks": profile.timeline_weeks
                },
                "current_macros": macro_targets.__dict__ if macro_targets else {},
                "progress_summary": progress_analysis.get("progress_summary", {}),
                "weekly_insights": progress_analysis.get("key_insights", {}),
                "recommendations": recommendations,
                "goal_timeline": goal_timeline,
                "next_check_in": (datetime.now()).isoformat()
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"❌ Error getting coaching dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.post("/log-progress")
async def log_progress_entry(request: ProgressEntryRequest):
    """Log daily/weekly progress metrics - Fixed version"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        print(f"📊 Logging progress for user {request.user_id}: {request.dict()}")

        progress_data = {
            "user_id": request.user_id,
            "recorded_at": datetime.now().isoformat()
        }

        # Only add fields that have values
        if request.weight is not None:
            progress_data["weight"] = float(request.weight)
        if request.body_fat_estimate is not None:
            progress_data["body_fat_estimate"] = float(request.body_fat_estimate)
        if request.energy_level is not None:
            progress_data["energy_level"] = int(request.energy_level)
        if request.adherence_score is not None:
            progress_data["adherence_score"] = float(request.adherence_score)
        if request.mood_rating is not None:
            progress_data["mood_rating"] = int(request.mood_rating)
        if request.sleep_quality is not None:
            progress_data["sleep_quality"] = int(request.sleep_quality)
        if request.notes:
            progress_data["notes"] = request.notes

        try:
            # First try to create the table if it doesn't exist
            result = supabase.table("progress_entries").insert(progress_data).execute()

            if not result.data:
                raise Exception("No data returned from insert")

            entry_id = result.data[0]["id"]
            print(f"✅ Progress entry created with ID: {entry_id}")

        except Exception as db_error:
            print(f"❌ Database error: {db_error}")

            # Try with minimal data if full insert fails
            minimal_data = {
                "user_id": request.user_id,
                "recorded_at": datetime.now().isoformat()
            }
            if request.weight:
                minimal_data["weight"] = float(request.weight)

            result = supabase.table("progress_entries").insert(minimal_data).execute()
            entry_id = result.data[0]["id"] if result.data else None

        # Try to run weekly analysis if user has a profile
        analysis_result = None
        try:
            profile = await coach_service._get_user_profile(request.user_id)
            if profile:
                should_analyze = await coach_service._should_run_weekly_analysis(request.user_id)
                if should_analyze:
                    print("🔄 Running weekly analysis...")
                    analysis_result = await coach_service.weekly_progress_analysis(request.user_id)
        except Exception as analysis_error:
            print(f"⚠️ Analysis skipped due to error: {analysis_error}")

        return {
            "success": True,
            "message": "Progress logged successfully",
            "data": {
                "entry_id": entry_id,
                "weekly_analysis": analysis_result,
                "next_check_in": datetime.now().isoformat(),
                "progress_data": progress_data  # Return what was saved
            }
        }

    except Exception as e:
        print(f"❌ Error logging progress: {e}")
        raise HTTPException(status_code=500, detail=f"Progress logging failed: {str(e)}")

    # Add endpoint to get recent progress entries


@router.get("/progress-history/{user_id}")
async def get_progress_history(user_id: str, limit: int = Query(10)):
    """Get recent progress entries for a user"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("progress_entries") \
            .select("*") \
            .eq("user_id", user_id) \
            .order("recorded_at", desc=True) \
            .limit(limit) \
            .execute()

        entries = result.data or []
        print(f"📊 Retrieved {len(entries)} progress entries for user {user_id}")

        return {
            "success": True,
            "entries": entries,
            "total_count": len(entries)
        }

    except Exception as e:
        print(f"❌ Error getting progress history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress history: {str(e)}")


# Add endpoint to verify progress was saved
@router.get("/progress-entry/{entry_id}")
async def get_progress_entry(entry_id: int, user_id: str = Query(...)):
    """Get a specific progress entry"""
    try:
        if not supabase:
            raise HTTPException(status_code=500, detail="Database not available")

        result = supabase.table("progress_entries") \
            .select("*") \
            .eq("id", entry_id) \
            .eq("user_id", user_id) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Progress entry not found")

        return {
            "success": True,
            "entry": result.data[0]
        }

    except Exception as e:
        print(f"❌ Error getting progress entry: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get progress entry: {str(e)}")

@router.post("/generate-goal-recipe")
async def generate_goal_oriented_recipe(request: GoalOrientedRecipeRequest):
    """Generate recipe optimized for user's specific goals and meal timing"""
    try:
        result = await coach_service.generate_goal_oriented_recipes(
            user_id=request.user_id,
            meal_type=request.meal_type,
            training_day=request.training_day
        )

        if request.specific_macros:
            result["meal_macros"].update(request.specific_macros)

        if request.prep_time_max:
            result["coaching_notes"].append(f"Recipe optimized for {request.prep_time_max} minute prep time")

        return {
            "success": True,
            "data": {
                "recipe": result["recipe"],
                "coaching_notes": result["coaching_notes"],
                "meal_macros": result["meal_macros"],
                "goal_alignment_score": result["goal_alignment"],
                "preparation_tips": result.get("prep_tips", []),
                "substitution_options": result.get("substitutions", [])
            }
        }

    except Exception as e:
        print(f"❌ Error generating goal-oriented recipe: {e}")
        raise HTTPException(status_code=500, detail=f"Recipe generation failed: {str(e)}")


@router.post("/weekly-analysis")
async def run_weekly_analysis(user_id: str):
    """Run comprehensive weekly progress analysis and generate recommendations"""
    try:
        analysis = await coach_service.weekly_progress_analysis(user_id)

        return {
            "success": True,
            "message": "Weekly analysis completed",
            "data": analysis
        }

    except Exception as e:
        print(f"❌ Error in weekly analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/adjust-macros")
async def adjust_macro_targets(request: MacroAdjustmentRequest):
    """Adjust macro targets based on progress or specific needs"""
    try:
        profile = await coach_service._get_user_profile(request.user_id)
        current_targets = await coach_service._get_current_macro_targets(request.user_id)

        adjusted_targets = await _apply_macro_adjustments(current_targets, request, profile)

        # Convert back to MacroTargets object for saving
        from services.nutrition_coach import MacroTargets
        macro_targets = MacroTargets(
            calories=adjusted_targets["calories"],
            protein=adjusted_targets["protein"],
            carbs=adjusted_targets["carbs"],
            fat=adjusted_targets["fat"],
            fiber=adjusted_targets.get("fiber", 25),
            protein_priority=adjusted_targets.get("protein_priority", "Evenly distributed"),
            carb_timing=adjusted_targets.get("carb_timing", "Evenly distributed"),
            meal_distribution=adjusted_targets.get("meal_distribution", {})
        )

        await coach_service._save_macro_targets(request.user_id, macro_targets)
        await _log_macro_adjustment(request.user_id, request.dict())

        return {
            "success": True,
            "message": "Macro targets adjusted successfully",
            "data": {
                "previous_targets": current_targets.__dict__ if current_targets else {},
                "new_targets": adjusted_targets,
                "adjustment_reason": request.adjustment_reason,
                "temporary": request.temporary_adjustment
            }
        }

    except Exception as e:
        print(f"❌ Error adjusting macros: {e}")
        raise HTTPException(status_code=500, detail=f"Macro adjustment failed: {str(e)}")


@router.post("/update-goal")
async def update_fitness_goal(user_id: str, new_goal: str, timeline_weeks: Optional[int] = None):
    """Update user's primary fitness goal and recalculate targets"""
    try:
        try:
            goal_enum = FitnessGoal(new_goal)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid goal: {new_goal}")

        profile = await coach_service._get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Update goal and timeline
        profile.primary_goal = goal_enum
        if timeline_weeks:
            profile.timeline_weeks = timeline_weeks

        # Reset phase tracking for new goal
        from services.nutrition_coach import TrainingPhase
        profile.current_phase = TrainingPhase.FOUNDATION
        profile.week_in_phase = 1

        # Recalculate macro targets
        new_macro_targets = coach_service.calculate_personalized_macros(profile)

        # Save updates
        await coach_service._save_fitness_profile(profile)
        await coach_service._save_macro_targets(user_id, new_macro_targets)

        return {
            "success": True,
            "message": f"Goal updated to {new_goal.replace('_', ' ')}",
            "data": {
                "new_profile": profile.__dict__,
                "new_macro_targets": new_macro_targets.__dict__,
                "estimated_timeline": coach_service._estimate_goal_timeline(profile)
            }
        }

    except Exception as e:
        print(f"❌ Error updating goal: {e}")
        raise HTTPException(status_code=500, detail=f"Goal update failed: {str(e)}")


@router.get("/goal-progress/{user_id}")
async def get_goal_progress(user_id: str, weeks: int = Query(12, description="Weeks of history to analyze")):
    """Get detailed goal progress analysis and projections"""
    try:
        # Get recent progress entries
        progress_result = supabase.table("progress_entries") \
            .select("*") \
            .eq("user_id", user_id) \
            .gte("recorded_at", (datetime.now() - timedelta(weeks=weeks)).isoformat()) \
            .order("recorded_at", desc=True) \
            .execute()

        progress_history = progress_result.data or []
        profile = await coach_service._get_user_profile(user_id)

        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Calculate basic progress analysis
        analysis = {
            "total_entries": len(progress_history),
            "weeks_tracked": weeks,
            "goal": profile.primary_goal.value,
            "progress_rate": "on_track"
        }

        if progress_history:
            weights = [entry['weight'] for entry in progress_history if entry.get('weight')]
            if len(weights) >= 2:
                weight_change = weights[0] - weights[-1]  # Most recent - oldest
                analysis["weight_change"] = weight_change
                analysis["weekly_rate"] = weight_change / weeks

        return {
            "success": True,
            "data": {
                "current_progress": analysis,
                "progress_history": progress_history[:10],  # Last 10 entries
                "recommendations": [
                    "Continue tracking consistently",
                    "Focus on weekly progress trends rather than daily fluctuations"
                ]
            }
        }

    except Exception as e:
        print(f"❌ Error getting goal progress: {e}")
        raise HTTPException(status_code=500, detail=f"Progress analysis failed: {str(e)}")


@router.get("/coaching-insights/{user_id}")
async def get_coaching_insights(user_id: str, insight_type: str = Query("all",
                                                                        description="Type of insights: all, nutrition, training, lifestyle")):
    """Get AI-powered coaching insights and recommendations"""
    try:
        profile = await coach_service._get_user_profile(user_id)
        recent_progress = await coach_service._analyze_recent_progress(user_id)
        adherence_data = await coach_service._calculate_adherence_metrics(user_id)

        insights = await coach_service._generate_ai_insights(profile, recent_progress, adherence_data)

        return {
            "success": True,
            "data": {
                "insights": insights,
                "generated_at": datetime.now().isoformat(),
                "confidence_score": insights.get("confidence", 0.8),
                "action_items": insights.get("key_insights", [])
            }
        }

    except Exception as e:
        print(f"❌ Error getting coaching insights: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")


@router.get("/available-goals")
async def get_available_goals():
    """Get list of available fitness goals"""
    goals = [
        {
            "value": goal.value,
            "display_name": goal.value.replace("_", " ").title(),
            "description": _get_goal_description(goal),
            "typical_timeline": _get_typical_timeline(goal)
        }
        for goal in FitnessGoal
    ]

    return {
        "success": True,
        "data": {"goals": goals}
    }


@router.get("/activity-levels")
async def get_activity_levels():
    """Get list of available activity levels"""
    levels = [
        {
            "value": level.value,
            "display_name": level.value.replace("_", " ").title(),
            "description": _get_activity_description(level),
            "multiplier": coach_service.activity_multipliers[level]
        }
        for level in ActivityLevel
    ]

    return {
        "success": True,
        "data": {"activity_levels": levels}
    }