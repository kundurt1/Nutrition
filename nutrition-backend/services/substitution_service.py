import openai
import json
from typing import List, Dict, Any, Optional
from database import supabase
import os
from datetime import datetime

# Initialize OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")


class SubstitutionService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_smart_substitutions(
            self,
            missing_ingredients: List[str],
            dietary_restrictions: List[str] = None,
            budget_preference: str = "medium",
            cuisine_type: str = None,
            user_pantry: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Get AI-powered ingredient substitutions"""

        try:
            # Prepare context for AI
            context = self._build_substitution_context(
                missing_ingredients,
                dietary_restrictions,
                budget_preference,
                cuisine_type,
                user_pantry
            )

            # Create the prompt
            prompt = self._create_substitution_prompt(context)

            # Call OpenAI
            response = await self._call_openai_for_substitutions(prompt)

            # Parse and validate response
            substitutions = self._parse_ai_response(response)

            # Enhance with additional data
            enhanced_substitutions = await self._enhance_substitutions(substitutions)

            return enhanced_substitutions

        except Exception as e:
            print(f"❌ Error in AI substitution service: {str(e)}")
            # Fallback to database substitutions
            return await self._get_fallback_substitutions(missing_ingredients, dietary_restrictions)

    def _build_substitution_context(
            self,
            missing_ingredients: List[str],
            dietary_restrictions: List[str] = None,
            budget_preference: str = "medium",
            cuisine_type: str = None,
            user_pantry: List[Dict] = None
    ) -> Dict:
        """Build context for AI substitution request"""

        context = {
            "missing_ingredients": missing_ingredients,
            "dietary_restrictions": dietary_restrictions or [],
            "budget_preference": budget_preference,
            "cuisine_type": cuisine_type,
            "available_in_pantry": []
        }

        if user_pantry:
            context["available_in_pantry"] = [
                {
                    "name": item.get("name"),
                    "quantity": item.get("quantity"),
                    "unit": item.get("unit"),
                    "location": item.get("location")
                }
                for item in user_pantry
                if float(item.get("quantity", 0)) > 0
            ]

        return context

    def _create_substitution_prompt(self, context: Dict) -> str:
        """Create detailed prompt for OpenAI substitution request"""

        prompt = f"""
You are an expert chef and nutritionist. Help me find the best ingredient substitutions for a recipe.

MISSING INGREDIENTS: {', '.join(context['missing_ingredients'])}

CONSTRAINTS:
- Dietary restrictions: {', '.join(context['dietary_restrictions']) if context['dietary_restrictions'] else 'None'}
- Budget preference: {context['budget_preference']} (low=cheapest options, medium=balance cost/quality, high=premium options)
- Cuisine type: {context['cuisine_type'] or 'Not specified'}

AVAILABLE IN PANTRY:
{json.dumps(context['available_in_pantry'], indent=2) if context['available_in_pantry'] else 'No pantry items provided'}

For each missing ingredient, provide substitution options following this EXACT JSON format:

{{
  "substitutions": [
    {{
      "original_ingredient": "ingredient name",
      "substitutes": [
        {{
          "substitute_ingredient": "substitute name",
          "conversion_ratio": 1.0,
          "conversion_notes": "1:1 replacement or specific instructions",
          "confidence_score": 0.95,
          "reason": "why this substitution works",
          "dietary_benefits": ["vegan", "gluten-free", etc.],
          "cost_impact": "lower/same/higher",
          "flavor_impact": "minimal/slight/significant",
          "texture_impact": "none/slight/noticeable",
          "availability": "common/specialty/rare",
          "pantry_alternative": true/false
        }}
      ]
    }}
  ]
}}

RULES:
1. Provide 2-3 substitution options per ingredient, ranked by confidence
2. Consider the specific dietary restrictions strictly
3. If an ingredient is available in the pantry, mention it as the first option
4. For budget=low, prioritize cheaper alternatives
5. For budget=high, include premium/specialty options
6. Include conversion ratios (e.g., 0.75 means use 3/4 the amount)
7. Be specific about measurement conversions
8. Consider how substitutions affect the overall dish
9. Mark pantry alternatives when pantry items can substitute

Respond ONLY with valid JSON. No additional text.
"""
        return prompt

    async def _call_openai_for_substitutions(self, prompt: str) -> str:
        """Call OpenAI API for substitution suggestions"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional chef and food scientist specializing in ingredient substitutions. Always respond with valid JSON only."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=2000
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"❌ OpenAI API error: {str(e)}")
            raise e

    def _parse_ai_response(self, response: str) -> List[Dict]:
        """Parse and validate AI response"""

        try:
            # Clean the response (remove any markdown formatting)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]

            # Parse JSON
            data = json.loads(response)

            # Validate structure
            if "substitutions" not in data:
                raise ValueError("Invalid response structure: missing 'substitutions'")

            return data["substitutions"]

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {str(e)}")
            print(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response from AI: {str(e)}")
        except Exception as e:
            print(f"❌ Response parsing error: {str(e)}")
            raise e

    async def _enhance_substitutions(self, substitutions: List[Dict]) -> List[Dict]:
        """Enhance AI substitutions with additional data and validation"""

        enhanced = []

        for sub_group in substitutions:
            original = sub_group.get("original_ingredient", "")
            substitutes = sub_group.get("substitutes", [])

            enhanced_substitutes = []

            for substitute in substitutes:
                # Add timestamp and ID
                substitute["generated_at"] = datetime.now().isoformat()
                substitute["source"] = "ai_generated"

                # Validate confidence score
                confidence = substitute.get("confidence_score", 0.5)
                substitute["confidence_score"] = max(0.0, min(1.0, float(confidence)))

                # Ensure required fields
                substitute["substitute_ingredient"] = substitute.get("substitute_ingredient", "Unknown")
                substitute["conversion_ratio"] = float(substitute.get("conversion_ratio", 1.0))
                substitute["conversion_notes"] = substitute.get("conversion_notes", "1:1 replacement")

                # Add computed fields
                substitute["difficulty"] = self._assess_substitution_difficulty(substitute)
                substitute["recommended"] = substitute["confidence_score"] > 0.7

                enhanced_substitutes.append(substitute)

            # Sort by confidence score
            enhanced_substitutes.sort(key=lambda x: x["confidence_score"], reverse=True)

            enhanced.append({
                "original_ingredient": original,
                "substitutes": enhanced_substitutes,
                "total_options": len(enhanced_substitutes),
                "best_option": enhanced_substitutes[0] if enhanced_substitutes else None
            })

        return enhanced

    def _assess_substitution_difficulty(self, substitute: Dict) -> str:
        """Assess how difficult a substitution is to execute"""

        confidence = substitute.get("confidence_score", 0.5)
        availability = substitute.get("availability", "common")
        flavor_impact = substitute.get("flavor_impact", "minimal")

        if confidence > 0.8 and availability == "common" and flavor_impact == "minimal":
            return "easy"
        elif confidence > 0.6 and availability in ["common", "specialty"]:
            return "moderate"
        else:
            return "challenging"

    async def _get_fallback_substitutions(
            self,
            missing_ingredients: List[str],
            dietary_restrictions: List[str] = None
    ) -> List[Dict]:
        """Fallback to database substitutions if AI fails"""

        try:
            if not supabase:
                return []

            fallback_substitutions = []

            for ingredient in missing_ingredients:
                query = supabase.table("ingredient_substitutions") \
                    .select("*") \
                    .ilike("original_ingredient", f"%{ingredient.lower()}%") \
                    .order("confidence_score", desc=True) \
                    .limit(3)

                # Filter by dietary restrictions if provided
                if dietary_restrictions:
                    for restriction in dietary_restrictions:
                        dietary_query = supabase.table("ingredient_substitutions") \
                            .select("*") \
                            .ilike("original_ingredient", f"%{ingredient.lower()}%") \
                            .eq("dietary_restriction", restriction) \
                            .order("confidence_score", desc=True) \
                            .limit(2)

                        dietary_result = dietary_query.execute()
                        if dietary_result.data:
                            query = dietary_query
                            break

                result = query.execute()

                if result.data:
                    substitutes = []
                    for sub in result.data:
                        substitutes.append({
                            "substitute_ingredient": sub["substitute_ingredient"],
                            "conversion_ratio": sub["ratio"],
                            "conversion_notes": sub["conversion_notes"],
                            "confidence_score": sub["confidence_score"],
                            "reason": f"Database suggestion for {sub.get('dietary_restriction', 'general')} needs",
                            "source": "database",
                            "difficulty": "easy" if sub["confidence_score"] > 0.8 else "moderate"
                        })

                    fallback_substitutions.append({
                        "original_ingredient": ingredient,
                        "substitutes": substitutes,
                        "total_options": len(substitutes),
                        "best_option": substitutes[0] if substitutes else None
                    })

            return fallback_substitutions

        except Exception as e:
            print(f"❌ Error in fallback substitutions: {str(e)}")
            return []

    async def save_successful_substitution(
            self,
            user_id: str,
            original_ingredient: str,
            substitute_used: str,
            rating: int,
            notes: str = None
    ):
        """Save user feedback on substitutions for learning"""

        try:
            if not supabase:
                return

            feedback_data = {
                "user_id": user_id,
                "original_ingredient": original_ingredient,
                "substitute_used": substitute_used,
                "rating": rating,  # 1-5 stars
                "notes": notes,
                "created_at": datetime.now().isoformat()
            }

            # This would require a user_substitution_feedback table
            # supabase.table("user_substitution_feedback").insert(feedback_data).execute()

        except Exception as e:
            print(f"❌ Error saving substitution feedback: {str(e)}")


# Global instance
substitution_service = SubstitutionService()