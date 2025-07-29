# nutrition-backend/routers/socialMediaImport.py

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import base64
import io
from PIL import Image
import json
from datetime import datetime

from services.social_media_import import SocialMediaImportService
from database import supabase

router = APIRouter()
social_import_service = SocialMediaImportService()


# Request Models
class SocialMediaURLRequest(BaseModel):
    user_id: str
    url: str
    create_alternatives: bool = True
    alternative_types: Optional[List[str]] = ["healthier", "budget", "quick"]


class RecipeFromImageRequest(BaseModel):
    user_id: str
    image_base64: str
    create_alternatives: bool = True
    alternative_types: Optional[List[str]] = ["healthier", "budget", "quick"]


class RecreateRecipeRequest(BaseModel):
    user_id: str
    original_recipe: Dict
    alternative_type: str  # "healthier", "budget", "quick", "vegan", etc.
    preserve_flavors: bool = True


# Endpoints
@router.post("/import-from-url")
async def import_recipe_from_url(req: SocialMediaURLRequest):
    """Import recipe from TikTok/Instagram URL"""
    try:
        print(f"📱 Importing recipe from URL: {req.url}")

        # Extract platform and validate URL
        platform = social_import_service.detect_platform(req.url)
        if not platform:
            raise HTTPException(status_code=400, detail="Unsupported URL. Please provide a TikTok or Instagram URL.")

        # Extract recipe from social media content
        recipe_data = await social_import_service.extract_recipe_from_url(
            url=req.url,
            platform=platform,
            user_id=req.user_id
        )

        if not recipe_data:
            raise HTTPException(status_code=404, detail="Could not extract recipe from the provided URL")

        # Generate alternatives if requested
        alternatives = []
        if req.create_alternatives:
            for alt_type in req.alternative_types:
                alt_recipe = await social_import_service.create_alternative_recipe(
                    original_recipe=recipe_data,
                    alternative_type=alt_type,
                    user_id=req.user_id
                )
                if alt_recipe:
                    alternatives.append(alt_recipe)

        # Save to database
        saved_recipe_id = await save_imported_recipe(req.user_id, recipe_data, req.url, platform)

        return {
            "success": True,
            "message": "Recipe imported successfully!",
            "original_recipe": recipe_data,
            "alternatives": alternatives,
            "recipe_id": saved_recipe_id,
            "source": {
                "platform": platform,
                "url": req.url
            }
        }

    except Exception as e:
        print(f"❌ Error importing from URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to import recipe: {str(e)}")


@router.post("/extract-from-image")
async def extract_recipe_from_image(
        user_id: str = Form(...),
        image: UploadFile = File(...),
        create_alternatives: bool = Form(True),
        alternative_types: str = Form('["healthier", "budget", "quick"]')
):
    """Extract recipe from uploaded food image"""
    try:
        # Validate file type
        if not image.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Please upload an image file")

        # Read and validate image size
        contents = await image.read()
        if len(contents) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(status_code=400, detail="Image size must be less than 10MB")

        # Convert to base64
        image_base64 = base64.b64encode(contents).decode('utf-8')

        # Extract recipe using AI
        recipe_data = await social_import_service.extract_recipe_from_image(
            image_base64=image_base64,
            user_id=user_id
        )

        if not recipe_data:
            raise HTTPException(status_code=404, detail="Could not identify recipe from the image")

        # Parse alternative types
        alt_types = json.loads(alternative_types) if isinstance(alternative_types, str) else alternative_types

        # Generate alternatives if requested
        alternatives = []
        if create_alternatives:
            for alt_type in alt_types:
                alt_recipe = await social_import_service.create_alternative_recipe(
                    original_recipe=recipe_data,
                    alternative_type=alt_type,
                    user_id=user_id
                )
                if alt_recipe:
                    alternatives.append(alt_recipe)

        # Save to database
        saved_recipe_id = await save_imported_recipe(
            user_id,
            recipe_data,
            source_url=None,
            platform="image_upload"
        )

        return {
            "success": True,
            "message": "Recipe extracted successfully!",
            "original_recipe": recipe_data,
            "alternatives": alternatives,
            "recipe_id": saved_recipe_id,
            "confidence": recipe_data.get("extraction_confidence", 0.9)
        }

    except Exception as e:
        print(f"❌ Error extracting from image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to extract recipe: {str(e)}")


@router.post("/recreate-recipe")
async def recreate_recipe_alternative(req: RecreateRecipeRequest):
    """Create an alternative version of a recipe"""
    try:
        # Create the alternative recipe
        alternative_recipe = await social_import_service.create_alternative_recipe(
            original_recipe=req.original_recipe,
            alternative_type=req.alternative_type,
            user_id=req.user_id,
            preserve_flavors=req.preserve_flavors
        )

        if not alternative_recipe:
            raise HTTPException(status_code=500, detail="Failed to create alternative recipe")

        # Save the alternative
        saved_recipe_id = await save_imported_recipe(
            req.user_id,
            alternative_recipe,
            source_url=None,
            platform="recreation",
            original_recipe_id=req.original_recipe.get("id")
        )

        return {
            "success": True,
            "message": f"{req.alternative_type.title()} alternative created!",
            "recipe": alternative_recipe,
            "recipe_id": saved_recipe_id,
            "comparison": {
                "original_cost": req.original_recipe.get("cost_estimate", "N/A"),
                "new_cost": alternative_recipe.get("cost_estimate", "N/A"),
                "original_calories": req.original_recipe.get("macros", {}).get("calories", "N/A"),
                "new_calories": alternative_recipe.get("macros", {}).get("calories", "N/A")
            }
        }

    except Exception as e:
        print(f"❌ Error recreating recipe: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to recreate recipe: {str(e)}")


@router.get("/trending-imports")
async def get_trending_imports(limit: int = 10):
    """Get trending imported recipes from social media"""
    try:
        if not supabase:
            return {"trending": [], "message": "Database not available"}

        # Get recently imported recipes that are popular
        result = supabase.table("imported_recipes") \
            .select("*, recipes(*)") \
            .order("import_count", desc=True) \
            .limit(limit) \
            .execute()

        trending = []
        for item in (result.data or []):
            if item.get("recipes"):
                recipe_data = item["recipes"]
                trending.append({
                    "recipe_id": recipe_data["id"],
                    "recipe_name": recipe_data["title"],
                    "source_platform": item["source_platform"],
                    "import_count": item["import_count"],
                    "original_url": item["source_url"],
                    "tags": recipe_data.get("tags", []),
                    "cuisine": recipe_data.get("cuisine", ""),
                    "preview_image": item.get("preview_image")
                })

        return {
            "trending": trending,
            "total": len(trending)
        }

    except Exception as e:
        print(f"❌ Error getting trending imports: {str(e)}")
        return {"trending": [], "error": str(e)}


# Helper functions
async def save_imported_recipe(
        user_id: str,
        recipe_data: Dict,
        source_url: Optional[str] = None,
        platform: str = "unknown",
        original_recipe_id: Optional[str] = None
) -> Optional[str]:
    """Save imported recipe to database"""
    if not supabase:
        return None

    try:
        # Save to recipes table
        recipe_insert = {
            "user_id": user_id,
            "title": recipe_data.get("recipe_name", "Imported Recipe"),
            "ingredients": recipe_data.get("ingredients", []),
            "directions": recipe_data.get("directions", []),
            "tags": recipe_data.get("tags", []),
            "cuisine": recipe_data.get("cuisine", ""),
            "diet": recipe_data.get("diet", ""),
            "macro_estimate": recipe_data.get("macros", {}),
            "cost_estimate": recipe_data.get("cost_estimate", ""),
            "prep_time": recipe_data.get("prep_time", ""),
            "cook_time": recipe_data.get("cook_time", ""),
            "difficulty": recipe_data.get("difficulty", "medium"),
            "source": "social_import",
            "source_metadata": {
                "platform": platform,
                "url": source_url,
                "imported_at": datetime.now().isoformat(),
                "original_recipe_id": original_recipe_id
            }
        }

        result = supabase.table("recipes").insert(recipe_insert).execute()

        if result.data and len(result.data) > 0:
            recipe_id = result.data[0]["id"]

            # Track the import
            import_tracking = {
                "recipe_id": recipe_id,
                "user_id": user_id,
                "source_platform": platform,
                "source_url": source_url,
                "imported_at": datetime.now().isoformat(),
                "import_count": 1
            }

            # Try to insert or update import tracking
            existing = supabase.table("imported_recipes") \
                .select("*") \
                .eq("source_url", source_url) \
                .execute()

            if existing.data and len(existing.data) > 0:
                # Update import count
                supabase.table("imported_recipes") \
                    .update({"import_count": existing.data[0]["import_count"] + 1}) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
            else:
                # Insert new tracking record
                supabase.table("imported_recipes").insert(import_tracking).execute()

            print(f"✅ Saved imported recipe with ID: {recipe_id}")
            return recipe_id

    except Exception as e:
        print(f"❌ Error saving imported recipe: {str(e)}")
        return None