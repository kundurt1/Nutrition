// src/services/ApiService.ts
import AsyncStorage from '@react-native-async-storage/async-storage';

interface RecipeRequest {
    title: string;
    mealType: string;
    budget?: number;
    userId: string;
}

interface Recipe {
    id: number;
    recipe_name: string;
    ingredients: string;
    instructions: string;
    macros: string;
    cost?: number;
    cooking_time?: number;
}

interface NutritionData {
    calories: number;
    protein: number;
    carbs: number;
    fat: number;
    fiber?: number;
}

interface UserPreferences {
    budget: string;
    allergies: string;
    diet: string;
    dietary_restrictions: Record<string, boolean>;
    macro_targets: Record<string, number>;
}

class ApiService {
    private baseUrl: string;

    constructor() {
        // Use your FastAPI backend URL
        this.baseUrl = __DEV__
            ? 'http://localhost:8000'
            : 'https://your-production-api.com';
    }

    private async getAuthHeaders(): Promise<HeadersInit> {
        const user = await AsyncStorage.getItem('user');
        const headers: HeadersInit = {
            'Content-Type': 'application/json',
        };

        if (user) {
            const userData = JSON.parse(user);
            // Add authentication header if you implement JWT tokens
            // headers['Authorization'] = `Bearer ${userData.token}`;
        }

        return headers;
    }

    // Recipe Generation
    async generateRecipe(request: RecipeRequest): Promise<Recipe[]> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/generate-recipe`, {
                method: 'POST',
                headers,
                body: JSON.stringify(request),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data.recipes || [];
        } catch (error) {
            console.error('Error generating recipe:', error);
            throw error;
        }
    }

    // Food Image Analysis
    async analyzeFood(imageUri: string): Promise<NutritionData> {
        try {
            const formData = new FormData();
            formData.append('image', {
                uri: imageUri,
                type: 'image/jpeg',
                name: 'food.jpg',
            } as any);

            const response = await fetch(`${this.baseUrl}/analyze-food-image`, {
                method: 'POST',
                body: formData,
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error analyzing food image:', error);
            throw error;
        }
    }

    // Barcode Scanning
    async scanBarcode(barcode: string): Promise<NutritionData> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/scan-barcode`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ barcode }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error scanning barcode:', error);
            throw error;
        }
    }

    // User Preferences
    async saveUserPreferences(userId: string, preferences: UserPreferences): Promise<void> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/user-preferences/${userId}`, {
                method: 'PUT',
                headers,
                body: JSON.stringify(preferences),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error saving preferences:', error);
            throw error;
        }
    }

    async getUserPreferences(userId: string): Promise<UserPreferences | null> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/user-preferences/${userId}`, {
                method: 'GET',
                headers,
            });

            if (response.status === 404) {
                return null; // No preferences found
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching preferences:', error);
            throw error;
        }
    }

    // Nutrition Logging
    async logNutrition(userId: string, nutritionData: NutritionData & { meal_name?: string }): Promise<void> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/log-nutrition`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    user_id: userId,
                    ...nutritionData,
                    timestamp: new Date().toISOString(),
                }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error logging nutrition:', error);
            throw error;
        }
    }

    // Get Daily Nutrition Summary
    async getDailyNutrition(userId: string, date?: string): Promise<NutritionData> {
        try {
            const headers = await this.getAuthHeaders();
            const queryDate = date || new Date().toISOString().split('T')[0];
            const response = await fetch(`${this.baseUrl}/daily-nutrition/${userId}?date=${queryDate}`, {
                method: 'GET',
                headers,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error fetching daily nutrition:', error);
            throw error;
        }
    }

    // Grocery List Management
    async addToGroceryList(userId: string, ingredients: string[]): Promise<void> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/grocery-list/${userId}`, {
                method: 'POST',
                headers,
                body: JSON.stringify({ ingredients }),
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Error adding to grocery list:', error);
            throw error;
        }
    }

    async getGroceryList(userId: string): Promise<any[]> {
        try {
            const headers = await this.getAuthHeaders();
            const response = await fetch(`${this.baseUrl}/grocery-list/${userId}`, {
                method: 'GET',
                headers,
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            return data.items || [];
        } catch (error) {
            console.error('Error fetching grocery list:', error);
            throw error;
        }
    }

    // Health Check
    async healthCheck(): Promise<boolean> {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch (error) {
            console.error('Health check failed:', error);
            return false;
        }
    }
}

// Export singleton instance
export const apiService = new ApiService();
export default apiService;