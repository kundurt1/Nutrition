from pydantic import BaseModel

class RecipeRequest(BaseModel):
    title: str = "vegan high-protein dinner"
    budget: float = 10.0