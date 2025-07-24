# nutrition-backend/routers/nutritionCoach.py

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum

from services.nutrition_coach import NutritionCoachService, FitnessGoal, ActivityLevel

router = APIRouter()
coach_service = NutritionCoachService()


# Request Models
class FitnessAssessmentRequest(BaseModel):
    user_id: str
    age: int
    gender: str  # "male" or "female"
    height_cm: float
    current_weight: float
    target_weight: float
    body_fat_percentage: Optional[float] = None
    target_body_fat: Optional[float] = None
    activity_level: str  # ActivityLevel enum value
    primary_goal: str  # FitnessGoal enum value
    timeline_weeks: int
    training_days_per_week: int
    experience_level: str  # "beginner", "intermediate", "advanced"
    current_injuries: Optional[List[str]] = []
    supplement_preferences: Optional[List[str]] = []
    meal_prep_experience: Optional[str] = "beginner"


class ProgressEntryRequest(BaseModel):
    user_id: str
    weight: Optional[float] = None
    body_fat_estimate: Optional[float] = None
    energy_level: Optional[int] = None  # 1-10 scale
    adherence_score: Optional[float] = None  # 0-1 scale
    strength_notes: Optional[str] = None
    mood_rating: Optional[int] = None  # 1-10 scale
    sleep_quality: Optional[int] = None  # 1-10 scale
    notes: Optional[str] = None
    progress_photos: Optional[List[str]] = []  # photo URLs


class GoalOrientedRecipeRequest(BaseModel):
    user_id: str
    meal_type: str  # "breakfast", "lunch", "dinner", "pre_workout", "post_workout", "snack"
    training_day: bool = False
    specific_macros: Optional[Dict[str, float]] = None  # Override calculated macros
    dietary_restrictions: Optional[List[str]] = []
    cuisine_preference: Optional[str] = None
    prep_time_max: Optional[int] = None  # minutes
    serving_size: Optional[int] = 1


class SmartGroceryRequest(BaseModel):
    user_id: str
    meal_plan_days: int = 7
    budget_target: Optional[float] = None
    store_preferences: Optional[List[str]] = []
    bulk_buying: bool = False
    meal_prep_focus: bool = False


class MacroAdjustmentRequest(BaseModel):
    user_id: str
    adjustment_reason: str  # "plateau", "energy_low", "too_fast_progress", "manual"
    calorie_change: Optional[int] = None
    protein_change: Optional[float] = None
    carb_change: Optional[float] = None
    fat_change: Optional[float] = None
    temporary_adjustment: bool = False  # If True, revert after 1-2 weeks


# Response Models
class CoachingDashboardResponse(BaseModel):
    user_profile: Dict[str, Any]
    current_macros: Dict[str, Any]
    progress_summary: Dict[str, Any]
    weekly_insights: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    goal_timeline: Dict[str, Any]
    next_check_in: str  # ISO datetime


class GoalOrientedRecipeResponse(BaseModel):
    recipe: Dict[str, Any]
    coaching_notes: List[str]
    meal_macros: Dict[str, float]
    goal_alignment_score: float  # 0-1 scale
    preparation_tips: List[str]
    substitution_options: List[Dict[str, Any]]


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
        # Get user profile and current status
        profile = await coach_service._get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Get current macro targets
        macro_targets = await coach_service._get_current_macro_targets(user_id)

        # Get recent progress analysis
        progress_analysis = await coach_service.weekly_progress_analysis(user_id)

        # Get upcoming recommendations
        recommendations = await coach_service._get_upcoming_recommendations(user_id)

        # Calculate goal timeline
        goal_timeline = coach_service._calculate_goal_timeline(profile, progress_analysis)

        dashboard = CoachingDashboardResponse(
            user_profile={
                "goal": profile.primary_goal.value,
                "phase": profile.current_phase.value,
                "week_in_phase": profile.week_in_phase,
                "experience": profile.experience_level,
                "timeline_weeks": profile.timeline_weeks
            },
            current_macros=macro_targets.__dict__ if macro_targets else {},
            progress_summary=progress_analysis.get("progress_summary", {}),
            weekly_insights=progress_analysis.get("key_insights", {}),
            recommendations=recommendations,
            goal_timeline=goal_timeline,
            next_check_in=(datetime.now().isoformat())
        )

        return {
            "success": True,
            "data": dashboard.dict()
        }

    except Exception as e:
        print(f"❌ Error getting coaching dashboard: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


@router.post("/log-progress")
async def log_progress_entry(request: ProgressEntryRequest):
    """Log daily/weekly progress metrics"""
    try:
        from database import supabase

        progress_data = {
            "user_id": request.user_id,
            "weight": request.weight,
            "body_fat_estimate": request.body_fat_estimate,
            "energy_level": request.energy_level,
            "adherence_score": request.adherence_score,
            "mood_rating": request.mood_rating,
            "sleep_quality": request.sleep_quality,
            "notes": request.notes,
            "recorded_at": datetime.now().isoformat()
        }

        # Save to database
        result = supabase.table("progress_entries").insert(progress_data).execute()

        # Check if weekly analysis is needed
        should_analyze = await coach_service._should_run_weekly_analysis(request.user_id)

        analysis_result = None
        if should_analyze:
            analysis_result = await coach_service.weekly_progress_analysis(request.user_id)

        return {
            "success": True,
            "message": "Progress logged successfully",
            "data": {
                "entry_id": result.data[0]["id"] if result.data else None,
                "weekly_analysis": analysis_result,
                "next_check_in": (datetime.now()).isoformat()
            }
        }

    except Exception as e:
        print(f"❌ Error logging progress: {e}")
        raise HTTPException(status_code=500, detail=f"Progress logging failed: {str(e)}")


@router.post("/generate-goal-recipe")
async def generate_goal_oriented_recipe(request: GoalOrientedRecipeRequest):
    """Generate recipe optimized for user's specific goals and meal timing"""
    try:
        result = await coach_service.generate_goal_oriented_recipes(
            user_id=request.user_id,
            meal_type=request.meal_type,
            training_day=request.training_day
        )

        # Add additional request-specific modifications
        if request.specific_macros:
            result["meal_macros"].update(request.specific_macros)

        if request.prep_time_max:
            result["coaching_notes"].append(f"Recipe optimized for {request.prep_time_max} minute prep time")

        response = GoalOrientedRecipeResponse(
            recipe=result["recipe"],
            coaching_notes=result["coaching_notes"],
            meal_macros=result["meal_macros"],
            goal_alignment_score=result["goal_alignment"],
            preparation_tips=result.get("prep_tips", []),
            substitution_options=result.get("substitutions", [])
        )

        return {
            "success": True,
            "data": response.dict()
        }

    except Exception as e:
        print(f"❌ Error generating goal-oriented recipe: {e}")
        raise HTTPException(status_code=500, detail=f"Recipe generation failed: {str(e)}")


@router.get("/smart-grocery-list/{user_id}")
async def get_smart_grocery_list(
        user_id: str,
        days: int = Query(7, description="Number of days to plan for"),
        budget: Optional[float] = Query(None, description="Budget target"),
        meal_prep: bool = Query(False, description="Focus on meal prep items")
):
    """Generate intelligent grocery list based on goals and meal planning"""
    try:
        # Get user's current meal plan or generate a basic one
        meal_plan = await coach_service._get_or_generate_meal_plan(user_id, days)

        grocery_request = {
            "meal_plan_days": days,
            "budget_target": budget,
            "meal_prep_focus": meal_prep
        }

        result = await coach_service.generate_smart_grocery_list(user_id, meal_plan)

        return {
            "success": True,
            "data": {
                "grocery_list": result,
                "meal_plan_summary": {
                    "total_days": days,
                    "estimated_cost": result.get("estimated_total_cost", 0),
                    "goal_alignment": result.get("goal_alignment_score", 0.8)
                },
                "coaching_tips": result.get("coaching_additions", [])
            }
        }

    except Exception as e:
        print(f"❌ Error generating smart grocery list: {e}")
        raise HTTPException(status_code=500, detail=f"Grocery list generation failed: {str(e)}")


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
        # Get current profile and targets
        profile = await coach_service._get_user_profile(request.user_id)
        current_targets = await coach_service._get_current_macro_targets(request.user_id)

        # Calculate new targets
        adjusted_targets = coach_service._apply_macro_adjustments(
            current_targets, request, profile
        )

        # Save adjusted targets
        await coach_service._save_macro_targets(request.user_id, adjusted_targets)

        # Log the adjustment reason
        await coach_service._log_macro_adjustment(request.user_id, request.dict())

        return {
            "success": True,
            "message": "Macro targets adjusted successfully",
            "data": {
                "previous_targets": current_targets.__dict__ if current_targets else {},
                "new_targets": adjusted_targets.__dict__,
                "adjustment_reason": request.adjustment_reason,
                "temporary": request.temporary_adjustment
            }
        }

    except Exception as e:
        print(f"❌ Error adjusting macros: {e}")
        raise HTTPException(status_code=500, detail=f"Macro adjustment failed: {str(e)}")


@router.get("/goal-progress/{user_id}")
async def get_goal_progress(user_id: str, weeks: int = Query(12, description="Weeks of history to analyze")):
    """Get detailed goal progress analysis and projections"""
    try:
        # Get historical progress data
        progress_history = await coach_service._get_progress_history(user_id, weeks)

        # Get current profile for context
        profile = await coach_service._get_user_profile(user_id)

        # Calculate progress metrics
        progress_analysis = coach_service._analyze_goal_progress(profile, progress_history)

        # Generate projections
        goal_projections = coach_service._project_goal_achievement(profile, progress_history)

        return {
            "success": True,
            "data": {
                "current_progress": progress_analysis,
                "projections": goal_projections,
                "milestone_tracking": coach_service._get_milestone_progress(profile, progress_history),
                "recommendations": coach_service._get_progress_recommendations(progress_analysis)
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
        # Get comprehensive user data
        profile = await coach_service._get_user_profile(user_id)
        recent_progress = await coach_service._analyze_recent_progress(user_id)
        adherence_data = await coach_service._calculate_adherence_metrics(user_id)

        # Generate AI insights
        insights = await coach_service._generate_ai_insights(profile, recent_progress, adherence_data)

        # Filter by insight type if specified
        if insight_type != "all":
            insights = coach_service._filter_insights_by_type(insights, insight_type)

        return {
            "success": True,
            "data": {
                "insights": insights,
                "generated_at": datetime.now().isoformat(),
                "confidence_score": insights.get("confidence", 0.8),
                "action_items": coach_service._extract_action_items(insights)
            }
        }

    except Exception as e:
        print(f"❌ Error getting coaching insights: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")


@router.post("/update-goal")
async def update_fitness_goal(user_id: str, new_goal: str, timeline_weeks: Optional[int] = None):
    """Update user's primary fitness goal and recalculate targets"""
    try:
        # Validate new goal
        try:
            goal_enum = FitnessGoal(new_goal)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid goal: {new_goal}")

        # Get current profile
        profile = await coach_service._get_user_profile(user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")

        # Update goal and timeline
        profile.primary_goal = goal_enum
        if timeline_weeks:
            profile.timeline_weeks = timeline_weeks

        # Reset phase tracking for new goal
        profile.current_phase = coach_service.TrainingPhase.FOUNDATION
        profile.week_in_phase = 1

        # Recalculate macro targets
        new_macro_targets = coach_service.calculate_personalized_macros(profile)

        # Save updates
        await coach_service._save_fitness_profile(profile)
        await coach_service._save_macro_targets(user_id, new_macro_targets)

        # Log goal change
        await coach_service._log_goal_change(user_id, new_goal, timeline_weeks)

        return {
            "success": True,
            "message": f"Goal updated to {new_goal}",
            "data": {
                "new_profile": profile.__dict__,
                "new_macro_targets": new_macro_targets.__dict__,
                "estimated_timeline": coach_service._estimate_goal_timeline(profile)
            }
        }

    except Exception as e:
        print(f"❌ Error updating goal: {e}")
        raise HTTPException(status_code=500, detail=f"Goal update failed: {str(e)}")


@router.get("/meal-timing-guide/{user_id}")
async def get_meal_timing_guide(user_id: str, training_day: bool = Query(True, description="Is this a training day?")):
    """Get personalized meal timing recommendations"""
    try:
        profile = await coach_service._get_user_profile(user_id)
        macro_targets = await coach_service._get_current_macro_targets(user_id)

        if not profile or not macro_targets:
            raise HTTPException(status_code=404, detail="User profile or macro targets not found")

        # Generate meal timing guide
        timing_guide = coach_service._generate_meal_timing_guide(profile, macro_targets, training_day)

        return {
            "success": True,
            "data": {
                "meal_schedule": timing_guide["schedule"],
                "macro_distribution": timing_guide["macro_distribution"],
                "training_day": training_day,
                "key_principles": timing_guide["principles"],
                "sample_meals": timing_guide.get("sample_meals", [])
            }
        }

    except Exception as e:
        print(f"❌ Error getting meal timing guide: {e}")
        raise HTTPException(status_code=500, detail=f"Meal timing guide failed: {str(e)}")


@router.get("/plateau-breaker/{user_id}")
async def get_plateau_breaker_recommendations(user_id: str):
    """Get specific recommendations to break through plateaus"""
    try:
        # Analyze current progress
        progress = await coach_service._analyze_recent_progress(user_id)
        profile = await coach_service._get_user_profile(user_id)

        if not progress.plateau_detected:
            return {
                "success": True,
                "message": "No plateau detected",
                "data": {
                    "plateau_detected": False,
                    "current_progress": "on_track"
                }
            }

        # Generate plateau-breaking strategies
        strategies = coach_service._generate_plateau_breaking_strategies(profile, progress)

        return {
            "success": True,
            "data": {
                "plateau_detected": True,
                "weeks_at_plateau": progress.weeks_at_plateau,
                "recommended_strategies": strategies["strategies"],
                "macro_adjustments": strategies["macro_changes"],
                "timeline_adjustments": strategies["timeline_changes"],
                "motivation_boost": strategies["motivation_message"]
            }
        }

    except Exception as e:
        print(f"❌ Error getting plateau breaker recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Plateau analysis failed: {str(e)}")


@router.get("/success-probability/{user_id}")
async def calculate_success_probability(user_id: str):
    """Calculate probability of achieving fitness goals based on current progress"""
    try:
        profile = await coach_service._get_user_profile(user_id)
        progress_history = await coach_service._get_progress_history(user_id, 8)  # 8 weeks
        adherence_data = await coach_service._calculate_adherence_metrics(user_id)

        # Calculate success probability using multiple factors
        probability_analysis = coach_service._calculate_comprehensive_success_probability(
            profile, progress_history, adherence_data
        )

        return {
            "success": True,
            "data": {
                "overall_probability": probability_analysis["overall"],
                "timeline_probability": probability_analysis["timeline"],
                "factor_breakdown": probability_analysis["factors"],
                "improvement_suggestions": probability_analysis["improvements"],
                "confidence_interval": probability_analysis["confidence_range"]
            }
        }

    except Exception as e:
        print(f"❌ Error calculating success probability: {e}")
        raise HTTPException(status_code=500, detail=f"Success probability calculation failed: {str(e)}")


# Utility endpoints for frontend integration

@router.get("/available-goals")
async def get_available_goals():
    """Get list of available fitness goals"""
    goals = [
        {
            "value": goal.value,
            "display_name": goal.value.replace("_", " ").title(),
            "description": coach_service._get_goal_description(goal),
            "typical_timeline": coach_service._get_typical_timeline(goal)
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
            "description": coach_service._get_activity_description(level),
            "multiplier": coach_service.activity_multipliers[level]
        }
        for level in ActivityLevel
    ]

    return {
        "success": True,
        "data": {"activity_levels": levels}
    }