# nutrition-backend/routers/recipeScaling.py

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import sys
import os

# Add the parent directory to the path so we can import our services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.recipeScalingModels import (
    ScaleRecipeRequest, ScaledRecipeResponse,
    ConvertUnitsRequest, GroceryListRequest, GroceryListResponse,
    CombinedGroceryListRequest, NutritionComparisonRequest, NutritionComparisonResponse,
    OptimizeServingsRequest, BatchScaleRequest, ImportRecipeRequest,
    ExportRecipeRequest, SearchRecipesRequest, UnitConversionRequest,
    UnitConversionResponse, RecipeAnalyticsRequest, RecipeAnalyticsResponse
)
from services.recipe_scaler import RecipeScalerService
from services.unit_converter import UnitConverterService

router = APIRouter()

# Initialize services
recipe_scaler_service = RecipeScalerService()
unit_converter_service = UnitConverterService()


@router.post("/scale-recipe", response_model=ScaledRecipeResponse)
async def scale_recipe(request: ScaleRecipeRequest):
    """Scale a recipe to a different number of servings"""
    try:
        result = await recipe_scaler_service.scale_recipe(
            request.recipe_name,
            request.new_servings,
            request.user_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error scaling recipe: {str(e)}")


@router.post("/convert-units")
async def convert_recipe_units(request: ConvertUnitsRequest):
    """Convert ingredients in a recipe to different units"""
    try:
        success = await recipe_scaler_service.convert_recipe_units(
            request.recipe_name,
            request.unit_conversions,
            request.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Recipe not found or conversion failed")

        return {"success": True, "message": "Units converted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting units: {str(e)}")


@router.post("/grocery-list", response_model=GroceryListResponse)
async def generate_grocery_list(request: GroceryListRequest):
    """Generate grocery list for a scaled recipe"""
    try:
        result = await recipe_scaler_service.get_grocery_list(
            request.recipe_name,
            request.servings,
            request.user_id,
            request.preferred_units
        )

        if not result:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating grocery list: {str(e)}")


@router.post("/combined-grocery-list", response_model=GroceryListResponse)
async def generate_combined_grocery_list(request: CombinedGroceryListRequest):
    """Generate combined grocery list for multiple recipes"""
    try:
        result = await recipe_scaler_service.get_combined_grocery_list(
            request.recipe_servings,
            request.user_id,
            request.preferred_units
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating combined grocery list: {str(e)}")


@router.post("/nutrition-comparison", response_model=NutritionComparisonResponse)
async def compare_nutrition_across_servings(request: NutritionComparisonRequest):
    """Compare nutrition across different serving sizes"""
    try:
        result = await recipe_scaler_service.get_nutrition_comparison(
            request.recipe_name,
            request.serving_sizes,
            request.user_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing nutrition: {str(e)}")


@router.post("/optimize-servings")
async def optimize_serving_size(request: OptimizeServingsRequest):
    """Find optimal serving size to meet target calories"""
    try:
        optimal_servings = await recipe_scaler_service.optimize_serving_size(
            request.recipe_name,
            request.target_calories_per_serving,
            request.user_id
        )

        if optimal_servings is None:
            raise HTTPException(status_code=404, detail="Recipe not found or no nutrition data")

        return {
            "recipe_name": request.recipe_name,
            "target_calories": request.target_calories_per_serving,
            "optimal_servings": optimal_servings,
            "message": f"For {request.target_calories_per_serving} calories per serving, make {optimal_servings} servings"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing servings: {str(e)}")


@router.post("/batch-scale")
async def batch_scale_recipes(request: BatchScaleRequest):
    """Scale multiple recipes at once"""
    try:
        results = await recipe_scaler_service.batch_scale_recipes(
            request.recipe_names,
            request.new_servings,
            request.user_id
        )

        return {
            "scaled_recipes": len(results),
            "results": results,
            "new_servings": request.new_servings
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error batch scaling recipes: {str(e)}")


@router.post("/import-recipe")
async def import_recipe(request: ImportRecipeRequest):
    """Import a recipe from data"""
    try:
        success = await recipe_scaler_service.import_recipe(
            request.recipe_data,
            request.user_id,
            request.save_to_db
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to import recipe")

        return {"success": True, "message": "Recipe imported successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing recipe: {str(e)}")


@router.post("/export-recipe")
async def export_recipe(request: ExportRecipeRequest):
    """Export a recipe"""
    try:
        result = await recipe_scaler_service.export_recipe(
            request.recipe_name,
            request.user_id,
            request.format
        )

        if not result:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting recipe: {str(e)}")


@router.post("/search-recipes")
async def search_recipes(request: SearchRecipesRequest):
    """Search recipes with filters"""
    try:
        results = await recipe_scaler_service.search_recipes(
            request.user_id,
            request.query,
            request.cuisine,
            request.difficulty,
            request.tag,
            request.max_cook_time
        )

        return {
            "recipes": results,
            "total_found": len(results),
            "filters_applied": {
                "query": request.query,
                "cuisine": request.cuisine,
                "difficulty": request.difficulty,
                "tag": request.tag,
                "max_cook_time": request.max_cook_time
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching recipes: {str(e)}")


@router.post("/convert-units", response_model=UnitConversionResponse)
async def convert_units(request: UnitConversionRequest):
    """Convert between units"""
    try:
        result = unit_converter_service.convert_units(
            request.quantity,
            request.from_unit,
            request.to_unit
        )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting units: {str(e)}")


@router.get("/compatible-units/{unit}")
async def get_compatible_units(unit: str):
    """Get units compatible with the given unit"""
    try:
        compatible = unit_converter_service.get_compatible_units(unit)
        unit_type = unit_converter_service.get_unit_type(unit)

        return {
            "unit": unit,
            "unit_type": unit_type,
            "compatible_units": compatible
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting compatible units: {str(e)}")


@router.post("/recipe-analytics", response_model=RecipeAnalyticsResponse)
async def get_recipe_analytics(request: RecipeAnalyticsRequest):
    """Get comprehensive analytics for a recipe"""
    try:
        result = await recipe_scaler_service.get_recipe_analytics(
            request.recipe_name,
            request.user_id
        )

        if not result:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting recipe analytics: {str(e)}")


@router.get("/user-recipes/{user_id}")
async def get_user_recipes(user_id: str):
    """Get all recipes for a user"""
    try:
        recipes = await recipe_scaler_service.get_user_recipes(user_id)

        return {
            "recipes": recipes,
            "total_recipes": len(recipes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting user recipes: {str(e)}")


@router.delete("/recipe/{recipe_name}")
async def delete_recipe(recipe_name: str, user_id: str):
    """Delete a recipe"""
    try:
        success = await recipe_scaler_service.delete_recipe(recipe_name, user_id)

        if not success:
            raise HTTPException(status_code=404, detail="Recipe not found")

        return {"success": True, "message": f"Recipe '{recipe_name}' deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting recipe: {str(e)}")


# Health check endpoint
@router.get("/health")
async def health_check():
    """Health check for recipe scaling service"""
    return {
        "status": "healthy",
        "service": "recipe-scaling",
        "features": [
            "recipe_scaling",
            "unit_conversion",
            "grocery_lists",
            "nutrition_analysis",
            "recipe_analytics"
        ]
    }