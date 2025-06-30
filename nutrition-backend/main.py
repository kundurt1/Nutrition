import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from routers import recipes, grocery, ratings, nutrition, favorites
from config import settings

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

# Include routers
app.include_router(recipes.router, prefix="/api", tags=["recipes"])
app.include_router(grocery.router, prefix="/api", tags=["grocery"])
app.include_router(ratings.router, prefix="/api", tags=["ratings"])
app.include_router(nutrition.router, prefix="/api", tags=["nutrition"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])

@app.get("/")
def root():
    return {"api_key_loaded": bool(os.getenv("OPENAI_API_KEY"))}

# ================================
# config.py - Configuration
# ================================
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # App settings
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
