# Testing/manual_test.py
# Simple manual test that doesn't require FastAPI TestClient

import requests
import json
import uuid
import time

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = str(uuid.uuid4())

def test_api_endpoint(endpoint, method="GET", data=None):
    """Helper function to test API endpoints"""
    try:
        if method == "POST":
            response = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
        else:
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        
        return {
            "status_code": response.status_code,
            "data": response.json() if response.headers.get('content-type') == 'application/json' else response.text,
            "success": response.status_code < 400
        }
    except requests.exceptions.ConnectionError:
        return {
            "status_code": None,
            "data": "Connection failed - is the server running?",
            "success": False
        }
    except Exception as e:
        return {
            "status_code": None,
            "data": str(e),
            "success": False
        }

def run_manual_tests():
    """Run manual tests against the live API"""
    print("🧪 Starting Manual API Tests...")
    print(f"📡 Testing against: {BASE_URL}")
    print(f"👤 Test User ID: {TEST_USER_ID}")
    print("-" * 60)
    
    tests = []
    
    # Test 1: Check if server is running
    print("1. 🔍 Testing server connectivity...")
    result = test_api_endpoint("/")
    tests.append(("Server Connectivity", result["success"]))
    if result["success"]:
        print(f"   ✅ Server responding: {result['data']}")
    else:
        print(f"   ❌ Server not responding: {result['data']}")
        print("   💡 Make sure to start your FastAPI server first:")
        print("      python main.py")
        return
    
    # Test 2: Rate a generated recipe
    print("\n2. 📝 Testing recipe rating (generated recipe)...")
    rating_data = {
        "user_id": TEST_USER_ID,
        "recipe_id": None,  # Generated recipe
        "recipe_data": {
            "recipe_name": "Test Pasta",
            "ingredients": [
                {"name": "pasta", "quantity": 1, "unit": "cup"},
                {"name": "tomato sauce", "quantity": 0.5, "unit": "cup"}
            ],
            "cuisine": "Italian",
            "macros": {"calories": 400, "protein": "15g"}
        },
        "rating": 5,
        "feedback_reason": None
    }
    
    result = test_api_endpoint("/rate-recipe", "POST", rating_data)
    tests.append(("Rate Generated Recipe", result["success"]))
    if result["success"]:
        print(f"   ✅ Rating submitted successfully")
        print(f"   📊 Response: {result['data']}")
    else:
        print(f"   ❌ Rating failed: Status {result['status_code']}")
        print(f"   📊 Response: {result['data']}")
    
    # Test 3: Rate with negative feedback
    print("\n3. 👎 Testing negative rating with feedback...")
    negative_rating = {
        "user_id": TEST_USER_ID,
        "recipe_data": {
            "ingredients": [{"name": "mushrooms", "quantity": 1}],
            "cuisine": "italian"
        },
        "rating": 1,
        "feedback_reason": "Too many ingredients I don't like"
    }
    
    result = test_api_endpoint("/rate-recipe", "POST", negative_rating)
    tests.append(("Negative Rating", result["success"]))
    if result["success"]:
        print(f"   ✅ Negative rating processed")
    else:
        print(f"   ❌ Negative rating failed: {result['data']}")
    
    # Test 4: Get user preferences
    print("\n4. 📋 Testing user preferences retrieval...")
    result = test_api_endpoint(f"/user-preferences/{TEST_USER_ID}")
    tests.append(("Get Preferences", result["success"]))
    if result["success"]:
        prefs = result["data"]
        print(f"   ✅ Preferences retrieved")
        print(f"   📊 Has preferences: {prefs.get('has_preferences', False)}")
        if prefs.get('has_preferences'):
            preferences = prefs.get('preferences', {})
            print(f"   💚 Preferred ingredients: {preferences.get('preferred_ingredients', [])}")
            print(f"   ❤️ Preferred cuisines: {preferences.get('preferred_cuisines', [])}")
            print(f"   💔 Disliked ingredients: {preferences.get('disliked_ingredients', [])}")
            print(f"   🚫 Disliked cuisines: {preferences.get('disliked_cuisines', [])}")
    else:
        print(f"   ❌ Failed to get preferences: {result['data']}")
    
    # Test 5: Invalid rating test
    print("\n5. ⚠️ Testing invalid rating (should fail)...")
    invalid_rating = {
        "user_id": TEST_USER_ID,
        "recipe_data": {"ingredients": []},
        "rating": 6,  # Invalid rating
        "feedback_reason": None
    }
    
    result = test_api_endpoint("/rate-recipe", "POST", invalid_rating)
    tests.append(("Invalid Rating Rejection", not result["success"]))  # Should fail
    if not result["success"] and "Rating must be between 1 and 5" in str(result["data"]):
        print(f"   ✅ Invalid rating correctly rejected")
    else:
        print(f"   ❌ Invalid rating not properly rejected: {result['data']}")
    
    # Test 6: Get rating history
    print("\n6. 📈 Testing rating history...")
    result = test_api_endpoint(f"/recipe-ratings/{TEST_USER_ID}")
    tests.append(("Rating History", result["success"]))
    if result["success"]:
        history = result["data"]
        print(f"   ✅ Rating history retrieved")
        print(f"   📊 Total ratings: {history.get('total_ratings', 0)}")
    else:
        print(f"   ❌ Failed to get rating history: {result['data']}")
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, success in tests if success)
    total = len(tests)
    
    for test_name, success in tests:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your API is working correctly.")
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        print("\n💡 Common issues:")
        print("   - Make sure your FastAPI server is running (python main.py)")
        print("   - Check that your Supabase credentials are correct")
        print("   - Verify that the database tables exist")

if __name__ == "__main__":
    run_manual_tests()