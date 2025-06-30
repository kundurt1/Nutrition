from openai import OpenAI
from config import settings

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)

    async def generate_three_recipes(self, title: str, budget: float, allergies: str, diet: str) -> str:
        """Generate three recipes using OpenAI"""
        prompt = self._build_three_recipe_prompt(title, budget, allergies, diet)
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        return response.choices[0].message.content

    async def generate_single_recipe(self, title: str, budget: float, allergies: str, diet: str, exclusion_context: str) -> str:
        """Generate single recipe using OpenAI"""
        prompt = self._build_single_recipe_prompt(title, budget, allergies, diet, exclusion_context)
        
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8
        )
        
        return response.choices[0].message.content

    def _build_three_recipe_prompt(self, title: str, budget: float, allergies: str, diet: str) -> str:
        """Build prompt for three recipes"""
        # Your existing prompt building logic
        pass

    def _build_single_recipe_prompt(self, title: str, budget: float, allergies: str, diet: str, exclusion_context: str) -> str:
        """Build prompt for single recipe"""
        # Your existing single recipe prompt logic
        pass