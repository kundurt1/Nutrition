from fastapi import APIRouter, HTTPException, Query
from models.user_models import LogMealRequest, CustomEntryRequest
from services.nutrition_service import NutritionService

router = APIRouter()
nutrition_service = NutritionService()

@router.post("/log-meal")
async def log_meal(req: LogMealRequest):
    """Log a meal - used by meal tracking functionality"""
    try:
        return await nutrition_service.log_meal(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log meal: {str(e)}")

@router.get("/meal-log")
async def get_meal_log(user_id: str = Query(...)):
    """Get user's meal log - used by HomePage.jsx for nutrition insights"""
    try:
        return await nutrition_service.get_meal_log(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get meal log: {str(e)}")

@router.get("/nutrition-summary")
async def get_nutrition_summary(user_id: str = Query(...)):
    """Get nutrition summary - used by HomePage.jsx dashboard"""
    try:
        return await nutrition_service.get_nutrition_summary(user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get nutrition summary: {str(e)}")

@router.post("/custom-entry")
async def custom_entry(req: CustomEntryRequest):
    """Log custom food entry - used by nutrition tracking"""
    try:
        return await nutrition_service.custom_entry(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log custom entry: {str(e)}")
