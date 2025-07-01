import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import recipes, grocery, ratings, nutrition, favorites

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Nutrition App API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (keeping your existing URLs - no /api prefix)
app.include_router(recipes.router, tags=["recipes"])
app.include_router(grocery.router, tags=["grocery"])
app.include_router(ratings.router, tags=["ratings"])
app.include_router(nutrition.router, tags=["nutrition"])
app.include_router(favorites.router, tags=["favorites"])

@app.get("/")
def root():
    return {"api_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}

@app.get("/test")
def test():
    return {"message": "All routers working with your naming convention!"}