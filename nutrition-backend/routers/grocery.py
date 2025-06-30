from fastapi import APIRouter, HTTPException, Query
from models.grocery_models import SaveGroceryListRequest
from services.grocery_service import GroceryService

router = APIRouter()
grocery_service = GroceryService()

@router.post("/save-grocery-list")
async def save_grocery_list(req: SaveGroceryListRequest):
    """Save consolidated grocery list - used by GenerateRecipe.jsx and GroceryList.jsx"""
    try:
        return await grocery_service.save_consolidated_grocery_list(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save grocery list: {str(e)}")

@router.get("/grocery-list/{user_id}")
async def get_grocery_list(user_id: str, include_purchased: bool = False):
    """Get user's grocery list - used by GroceryList.jsx"""
    try:
        return await grocery_service.get_grocery_list(user_id, include_purchased)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get grocery list: {str(e)}")

@router.patch("/grocery-list/{item_id}/purchase")
async def mark_item_purchased(item_id: int, user_id: str = Query(...)):
    """Mark grocery item as purchased - used by GroceryList.jsx"""
    try:
        return await grocery_service.mark_item_purchased(item_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark item as purchased: {str(e)}")