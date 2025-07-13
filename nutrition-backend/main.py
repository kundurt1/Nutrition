# nutrition-backend/main.py

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import recipes, grocery, ratings, nutrition, favorites, mealPlanning
from routers import recipeScaling  # NEW - Add recipe scaling router

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Nutrition App API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",  # In case you switch to port 3000
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers (keeping your existing URLs - no /api prefix)
app.include_router(recipes.router, tags=["recipes"])
app.include_router(grocery.router, tags=["grocery"])
app.include_router(ratings.router, tags=["ratings"])
app.include_router(nutrition.router, tags=["nutrition"])
app.include_router(favorites.router, tags=["favorites"])
app.include_router(mealPlanning.router, tags=["meal-planning"])

# NEW - Include recipe scaling router
app.include_router(recipeScaling.router, prefix="/recipe-scaling", tags=["recipe-scaling"])

@app.get("/")
def root():
    return {
        "api_key_loaded": bool(os.getenv("OPENAI_API_KEY")),
        "features": [
            "recipe_generation",
            "grocery_management",
            "ratings_and_favorites",
            "nutrition_tracking",
            "meal_planning",
            "recipe_scaling"  # NEW
        ]
    }

@app.get("/test")
def test():
    return {"message": "All routers working with recipe scaling functionality!"}