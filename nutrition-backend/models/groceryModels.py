from pydantic import BaseModel
from typing import Optional, List

class GroceryItem(BaseModel):
    item_name: str
    quantity: float
    estimated_cost: float
    category: Optional[str] = "Recipe Generated"
    is_purchased: bool = False

class SaveGroceryListRequest(BaseModel):
    user_id: str
    grocery_items: List[GroceryItem]