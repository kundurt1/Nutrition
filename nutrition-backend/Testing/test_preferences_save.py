"""
Test file for user preferences save functionality
Run with: pytest test_preferences_save.py -v
"""

import pytest
import requests
import json
from datetime import datetime
import uuid

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = f"test_user_{uuid.uuid4().hex[:8]}"  # Generate unique test user ID


class TestPreferencesSave:
    """Test suite for preferences save and retrieval functionality"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.test_preferences = {
            "user_id": TEST_USER_ID,
            "budget": "50-100",
            "allergies": "peanuts, shellfish",
            "diet": "vegetarian",
            "dietary_restrictions": {
                "vegan": False,
                "vegetarian": True,
                "gluten_free": False,
                "dairy_free": True,
                "nut_free": True,
                "low_carb": False,
                "keto": False,
                "paleo": False
            },
            "macro_targets": {
                "enableTargets": True,
                "calories": 2500,
                "protein": 180,
                "carbs": 250,
                "fat": 85,
                "fiber": 30
            },
            "cuisine_preferences": {
                "preferred": ["Italian", "Mexican", "Japanese"],
                "disliked": ["German", "British"]
            },
            "cooking_constraints": {
                "maxCookTime": 60,
                "maxPrepTime": 20,
                "maxIngredients": 12,
                "difficultyLevel": "intermediate",
                "kitchenEquipment": ["Oven", "Stovetop", "Air Fryer", "Instant Pot"]
            }
        }

    def test_save_preferences_endpoint(self):
        """Test that preferences can be saved successfully"""
        response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )

        # Check response status
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"

        # Check response contains success message
        data = response.json()
        assert data.get("message") == "Preferences saved successfully"
        assert data.get("user_id") == TEST_USER_ID

        print(f"✅ Preferences saved successfully for user {TEST_USER_ID}")

    def test_retrieve_saved_preferences(self):
        """Test that saved preferences can be retrieved correctly"""
        # First save the preferences
        save_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert save_response.status_code == 200

        # Now retrieve them
        get_response = requests.get(f"{BASE_URL}/get-preferences/{TEST_USER_ID}")

        # Check response status
        assert get_response.status_code == 200, f"Expected 200, got {get_response.status_code}"

        # Check retrieved data
        data = get_response.json()
        assert "preferences" in data

        prefs = data["preferences"]

        # Verify all fields were saved correctly
        assert prefs["budget"] == self.test_preferences["budget"]
        assert prefs["allergies"] == self.test_preferences["allergies"]
        assert prefs["diet"] == self.test_preferences["diet"]

        print(f"✅ Retrieved preferences match saved data")

    def test_macro_targets_saved_correctly(self):
        """Test that macro targets are saved and retrieved with correct values"""
        # Save preferences
        save_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert save_response.status_code == 200

        # Retrieve preferences
        get_response = requests.get(f"{BASE_URL}/get-preferences/{TEST_USER_ID}")
        data = get_response.json()

        macro_targets = data["preferences"]["macro_targets"]

        # Verify macro targets
        assert macro_targets["enableTargets"] == True
        assert macro_targets["calories"] == 2500
        assert macro_targets["protein"] == 180
        assert macro_targets["carbs"] == 250
        assert macro_targets["fat"] == 85
        assert macro_targets["fiber"] == 30

        print(f"✅ Macro targets saved correctly:")
        print(f"   - Calories: {macro_targets['calories']}")
        print(f"   - Protein: {macro_targets['protein']}g")
        print(f"   - Carbs: {macro_targets['carbs']}g")
        print(f"   - Fat: {macro_targets['fat']}g")
        print(f"   - Fiber: {macro_targets['fiber']}g")

    def test_dietary_restrictions_saved_correctly(self):
        """Test that dietary restrictions are properly saved"""
        # Save preferences
        save_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert save_response.status_code == 200

        # Retrieve preferences
        get_response = requests.get(f"{BASE_URL}/get-preferences/{TEST_USER_ID}")
        data = get_response.json()

        dietary_restrictions = data["preferences"]["dietary_restrictions"]

        # Verify dietary restrictions
        assert dietary_restrictions["vegetarian"] == True
        assert dietary_restrictions["dairy_free"] == True
        assert dietary_restrictions["nut_free"] == True
        assert dietary_restrictions["vegan"] == False
        assert dietary_restrictions["gluten_free"] == False

        print(f"✅ Dietary restrictions saved correctly")

    def test_cuisine_preferences_saved_correctly(self):
        """Test that cuisine preferences are properly saved"""
        # Save preferences
        save_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert save_response.status_code == 200

        # Retrieve preferences
        get_response = requests.get(f"{BASE_URL}/get-preferences/{TEST_USER_ID}")
        data = get_response.json()

        cuisine_prefs = data["preferences"]["cuisine_preferences"]

        # Verify cuisine preferences
        assert "Italian" in cuisine_prefs["preferred"]
        assert "Mexican" in cuisine_prefs["preferred"]
        assert "Japanese" in cuisine_prefs["preferred"]
        assert "German" in cuisine_prefs["disliked"]
        assert "British" in cuisine_prefs["disliked"]

        print(f"✅ Cuisine preferences saved correctly")
        print(f"   - Preferred: {cuisine_prefs['preferred']}")
        print(f"   - Disliked: {cuisine_prefs['disliked']}")

    def test_update_existing_preferences(self):
        """Test that updating existing preferences works correctly"""
        # Save initial preferences
        save_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert save_response.status_code == 200

        # Update preferences with new values
        updated_preferences = self.test_preferences.copy()
        updated_preferences["macro_targets"]["calories"] = 3000
        updated_preferences["macro_targets"]["protein"] = 200
        updated_preferences["diet"] = "keto"

        # Save updated preferences
        update_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=updated_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert update_response.status_code == 200

        # Retrieve and verify updated preferences
        get_response = requests.get(f"{BASE_URL}/get-preferences/{TEST_USER_ID}")
        data = get_response.json()

        assert data["preferences"]["macro_targets"]["calories"] == 3000
        assert data["preferences"]["macro_targets"]["protein"] == 200
        assert data["preferences"]["diet"] == "keto"

        print(f"✅ Preferences updated successfully")
        print(f"   - Updated calories: 2500 → 3000")
        print(f"   - Updated protein: 180g → 200g")
        print(f"   - Updated diet: vegetarian → keto")

    def test_preferences_affect_recipe_generation(self):
        """Test that saved preferences are used in recipe generation"""
        # Save preferences with specific constraints
        save_response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=self.test_preferences,
            headers={"Content-Type": "application/json"}
        )
        assert save_response.status_code == 200

        # Generate a recipe using the saved preferences
        recipe_request = {
            "user_id": TEST_USER_ID,
            "title": "Quick dinner",
            "num_recipes": 1
        }

        recipe_response = requests.post(
            f"{BASE_URL}/generate-recipe-with-advanced-preferences",
            json=recipe_request,
            headers={"Content-Type": "application/json"}
        )

        # Check that recipe generation works
        assert recipe_response.status_code == 200, f"Recipe generation failed: {recipe_response.text}"

        recipe_data = recipe_response.json()

        # Verify recipe respects preferences (if data is available)
        if "recipes" in recipe_data and len(recipe_data["recipes"]) > 0:
            recipe = recipe_data["recipes"][0]

            # Check that recipe respects the vegetarian diet
            ingredients_text = " ".join(recipe.get("ingredients", []))
            meat_keywords = ["chicken", "beef", "pork", "fish", "salmon", "tuna", "steak"]

            has_meat = any(meat in ingredients_text.lower() for meat in meat_keywords)
            assert not has_meat, f"Recipe contains meat despite vegetarian preference"

            print(f"✅ Recipe generation respects saved preferences")
            print(f"   - Generated vegetarian recipe: {recipe.get('title', 'Unknown')}")

    def test_default_preferences_for_new_user(self):
        """Test that new users get default preferences"""
        new_user_id = f"new_user_{uuid.uuid4().hex[:8]}"

        get_response = requests.get(f"{BASE_URL}/get-preferences/{new_user_id}")

        assert get_response.status_code == 200
        data = get_response.json()

        # Check default values
        prefs = data["preferences"]
        assert prefs["macro_targets"]["calories"] == 2000
        assert prefs["macro_targets"]["protein"] == 150
        assert prefs["macro_targets"]["carbs"] == 200
        assert prefs["macro_targets"]["fat"] == 70
        assert prefs["macro_targets"]["fiber"] == 25
        assert prefs["macro_targets"]["enableTargets"] == False

        print(f"✅ Default preferences returned for new user")

    def test_invalid_data_handling(self):
        """Test that invalid data is handled gracefully"""
        invalid_preferences = {
            "user_id": TEST_USER_ID,
            "budget": "invalid_budget",  # This should still work as a string
            "macro_targets": {
                "enableTargets": True,
                "calories": "not_a_number",  # This should be converted or handled
                "protein": -50,  # Negative value
            }
        }

        response = requests.post(
            f"{BASE_URL}/save-preferences",
            json=invalid_preferences,
            headers={"Content-Type": "application/json"}
        )

        # The endpoint should handle this gracefully
        # It might save with defaults or validation
        print(f"⚠️  Invalid data handling test - Status: {response.status_code}")

        if response.status_code == 200:
            # Retrieve to see what was actually saved
            get_response = requests.get(f"{BASE_URL}/get-preferences/{TEST_USER_ID}")
            if get_response.status_code == 200:
                data = get_response.json()
                print(
                    f"   - System handled invalid data and saved: {data['preferences'].get('macro_targets', {}).get('calories', 'N/A')}")


def run_all_tests():
    """Run all tests without pytest"""
    print("\n" + "=" * 60)
    print("🧪 RUNNING PREFERENCES SAVE TESTS")
    print("=" * 60 + "\n")

    test_suite = TestPreferencesSave()
    test_suite.setup()

    tests = [
        ("Save Preferences", test_suite.test_save_preferences_endpoint),
        ("Retrieve Preferences", test_suite.test_retrieve_saved_preferences),
        ("Macro Targets", test_suite.test_macro_targets_saved_correctly),
        ("Dietary Restrictions", test_suite.test_dietary_restrictions_saved_correctly),
        ("Cuisine Preferences", test_suite.test_cuisine_preferences_saved_correctly),
        ("Update Preferences", test_suite.test_update_existing_preferences),
        ("Recipe Generation", test_suite.test_preferences_affect_recipe_generation),
        ("Default Preferences", test_suite.test_default_preferences_for_new_user),
        ("Invalid Data", test_suite.test_invalid_data_handling),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n📝 Testing: {test_name}")
            print("-" * 40)
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # You can run with pytest or directly
    try:
        # Try to run with pytest if available
        import sys

        sys.exit(pytest.main([__file__, "-v", "-s"]))
    except ImportError:
        # Run tests directly if pytest not installed
        print("Note: pytest not found, running tests directly")
        run_all_tests()