import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import RecipeRatings from '../components/RecipeRatings';
import { addRecipeToNutritionLog } from '../components/NutritionTracker';
import { Utensils, CheckCircle } from 'lucide-react';

export default function GenerateRecipe() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [activeTab, setActiveTab] = useState('generate'); // This was missing!
  
  // Recipe Generation State
  const [title, setTitle] = useState('');
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [recipeResults, setRecipeResults] = useState(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);
  const [savingToGroceryList, setSavingToGroceryList] = useState(false);

  // Meal Planning State 
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('week');
  const [plannedMeals, setPlannedMeals] = useState({});
  const [availableRecipes, setAvailableRecipes] = useState([]);
  const [showRecipePanel, setShowRecipePanel] = useState(true);
  const [draggedRecipe, setDraggedRecipe] = useState(null);
  const [totalBudget, setTotalBudget] = useState(0);
  const [totalPrepTime, setTotalPrepTime] = useState(0);
  const [mealPlanLoading, setMealPlanLoading] = useState(false);

  const [addingToNutrition, setAddingToNutrition] = useState({});

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data: { user }, error: userError } = await supabase.auth.getUser();
        if (userError) {
          console.error('Auth error:', userError);
          setErrorMsg('Authentication error. Please try signing in again.');
          return;
        }
        if (!user) {
          setErrorMsg('You must be signed in to generate recipes.');
          return;
        }
        setUserId(user.id);
      } catch (error) {
        console.error('Error fetching user:', error);
        setErrorMsg('Error loading user data. Please refresh the page.');
      }
    };
    fetchUser();
  }, []);

  // Load meal plans and available recipes when switching to meal planning tab
  useEffect(() => {
    if (activeTab === 'meal-plan' && userId) {
      loadMealPlans();
      loadAvailableRecipes();
    }
  }, [activeTab, userId]);

  // Calculate total budget and prep time for meal planning
  useEffect(() => {
    const meals = Object.values(plannedMeals).flat();
    const budget = meals.reduce((sum, meal) => sum + (meal.cost || 0), 0);
    const prepTime = meals.reduce((sum, meal) => sum + (meal.prepTime || 0) + (meal.cookTime || 0), 0);
    setTotalBudget(budget);
    setTotalPrepTime(prepTime);
  }, [plannedMeals]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setRecipeResults(null);

    if (!title.trim()) {
      setErrorMsg('Please enter a recipe title.');
      return;
    }
    
    const budgetNum = parseFloat(budget);
    if (!budget || isNaN(budgetNum) || budgetNum <= 0) {
      setErrorMsg('Please enter a valid budget amount greater than 0.');
      return;
    }
    
    if (!userId) {
      setErrorMsg('Unable to find user. Please sign in again.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        title: title.trim(),
        budget: budgetNum,
        user_id: userId,
      };
      
      const res = await fetch('http://localhost:8000/generate-recipe-with-grocery', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        let errorMessage = `Server error: ${res.status} ${res.statusText}`;
        try {
          const errJson = await res.json();
          errorMessage = errJson.detail || errJson.message || JSON.stringify(errJson);
        } catch (parseError) {
          console.error('Error parsing error response:', parseError);
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();
      
      if (!data || !Array.isArray(data.recipes)) {
        throw new Error('Invalid response format from server');
      }
      
      setRecipeResults(data.recipes);
      
    } catch (err) {
      console.error('Recipe generation error:', err);
      setErrorMsg(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateRecipe = async (recipeIndex) => {
    if (!recipeResults || !userId) return;
    
    setRegeneratingIndex(recipeIndex);
    try {
      const currentRecipes = recipeResults.map(r => r.recipe_name || r.title || 'Recipe');
      
      const payload = {
        title: title.trim(),
        budget: parseFloat(budget),
        user_id: userId,
        regenerate_single: true,
        exclude_recipes: currentRecipes
      };
      
      const res = await fetch('http://localhost:8000/generate-single-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error('Failed to regenerate recipe');
      }

      const data = await res.json();
      
      if (data && data.recipe) {
        const newRecipes = [...recipeResults];
        newRecipes[recipeIndex] = data.recipe;
        setRecipeResults(newRecipes);
      }
      
    } catch (err) {
      console.error('Recipe regeneration error:', err);
      setErrorMsg(`Error regenerating recipe: ${err.message}`);
    } finally {
      setRegeneratingIndex(null);
    }
  };

  const handleDoubleClickAddToNutrition = async (recipe, recipeIndex) => {
  if (!userId) {
    alert('Please sign in to track nutrition');
    return;
  }

  setAddingToNutrition(prev => ({ ...prev, [recipeIndex]: true }));

  try {
    const result = await addRecipeToNutritionLog(userId, recipe);
    
    if (result.success) {
      // Show success notification
      const notification = document.createElement('div');
      notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center';
      notification.innerHTML = `
        <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
        </svg>
        Added to nutrition log!
      `;
      document.body.appendChild(notification);
      
      // Remove notification after 3 seconds
      setTimeout(() => {
        document.body.removeChild(notification);
      }, 3000);
    } else {
      alert('Failed to add to nutrition log: ' + (result.error || 'Unknown error'));
    }
  } catch (error) {
    console.error('Error adding to nutrition log:', error);
    alert('Error adding to nutrition log');
  } finally {
    setAddingToNutrition(prev => ({ ...prev, [recipeIndex]: false }));
  }
};
  const handleSaveToGroceryList = async () => {
    if (!recipeResults || !userId) return;
    
    setSavingToGroceryList(true);
    try {
      const allGroceryItems = [];
      
      recipeResults.forEach(recipe => {
        if (recipe.grocery_list && Array.isArray(recipe.grocery_list)) {
          recipe.grocery_list.forEach(item => {
            allGroceryItems.push({
              item_name: item.item || item.name || 'Unknown item',
              quantity: item.quantity || 1,
              estimated_cost: item.estimated_cost || 0,
              category: "Recipe Generated"
            });
          });
        }
      });

      if (allGroceryItems.length === 0) {
        alert('No grocery items found in recipes');
        return;
      }

      const payload = {
        user_id: userId,
        grocery_items: allGroceryItems
      };

      const res = await fetch('http://localhost:8000/save-grocery-list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error('Failed to save grocery list');
      }

      const data = await res.json();
      
      const shouldNavigate = window.confirm(
        `Successfully added ${data.inserted_items || 0} items to your grocery list! Would you like to view your grocery list now?`
      );
      
      if (shouldNavigate) {
        navigate('/grocery');
      }
      
    } catch (err) {
      console.error('Save grocery list error:', err);
      setErrorMsg(`Error saving to grocery list: ${err.message}`);
    } finally {
      setSavingToGroceryList(false);
    }
  };

  // Meal Planning Functions
  const loadMealPlans = async () => {
    try {
      const response = await fetch(`http://localhost:8000/meal-plans/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setPlannedMeals(data.meal_plans || {});
      }
    } catch (error) {
      console.error('Error loading meal plans:', error);
    }
  };

  const loadAvailableRecipes = async () => {
    try {
      const response = await fetch(`http://localhost:8000/user-recipes/${userId}?limit=20`);
      if (response.ok) {
        const data = await response.json();
        setAvailableRecipes(data.recipes || []);
      }
    } catch (error) {
      console.error('Error loading available recipes:', error);
    }
  };

  const saveMealPlan = async (dateKey, meals) => {
    try {
      const response = await fetch('http://localhost:8000/save-meal-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          date: dateKey,
          meals: meals
        })
      });

      if (!response.ok) {
        throw new Error('Failed to save meal plan');
      }
    } catch (error) {
      console.error('Error saving meal plan:', error);
    }
  };

  const getWeekDates = () => {
    const startOfWeek = new Date(currentDate);
    const day = startOfWeek.getDay();
    const diff = startOfWeek.getDate() - day;
    startOfWeek.setDate(diff);

    const weekDates = [];
    for (let i = 0; i < 7; i++) {
      const date = new Date(startOfWeek);
      date.setDate(startOfWeek.getDate() + i);
      weekDates.push(date);
    }
    return weekDates;
  };

  const formatDate = (date) => {
    return date.toISOString().split('T')[0];
  };

  const getMealsForDate = (date) => {
    const dateKey = formatDate(date);
    return plannedMeals[dateKey] || [];
  };

  const addMealToDate = async (date, meal, mealType = 'dinner') => {
    const dateKey = formatDate(date);
    const currentMeals = plannedMeals[dateKey] || [];
    const newMeal = { ...meal, mealType, id: Date.now() };
    const updatedMeals = [...currentMeals, newMeal];
    
    setPlannedMeals(prev => ({
      ...prev,
      [dateKey]: updatedMeals
    }));

    await saveMealPlan(dateKey, updatedMeals);
  };

  const removeMealFromDate = async (date, mealId) => {
    const dateKey = formatDate(date);
    const currentMeals = plannedMeals[dateKey] || [];
    const updatedMeals = currentMeals.filter(meal => meal.id !== mealId);
    
    setPlannedMeals(prev => ({
      ...prev,
      [dateKey]: updatedMeals
    }));

    await saveMealPlan(dateKey, updatedMeals);
  };

  const handleDragStart = (e, recipe) => {
    setDraggedRecipe(recipe);
    e.dataTransfer.effectAllowed = 'copy';
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  };

  const handleDrop = (e, date) => {
    e.preventDefault();
    if (draggedRecipe) {
      addMealToDate(date, draggedRecipe);
      setDraggedRecipe(null);
    }
  };

  const generateGroceryListFromMealPlan = async () => {
    try {
      setMealPlanLoading(true);
      const response = await fetch('http://localhost:8000/generate-grocery-from-meal-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          meal_plans: plannedMeals
        })
      });

      if (response.ok) {
        const data = await response.json();
        const shouldNavigate = window.confirm(
          `Successfully added ${data.items_added} items to your grocery list! Would you like to view your grocery list now?`
        );
        
        if (shouldNavigate) {
          navigate('/grocery');
        }
      }
    } catch (error) {
      console.error('Error generating grocery list from meal plan:', error);
      setErrorMsg('Failed to generate grocery list from meal plan');
    } finally {
      setMealPlanLoading(false);
    }
  };

  const navigateCalendar = (direction) => {
    const newDate = new Date(currentDate);
    if (viewMode === 'week') {
      newDate.setDate(currentDate.getDate() + (direction * 7));
    } else {
      newDate.setMonth(currentDate.getMonth() + direction);
    }
    setCurrentDate(newDate);
  };

  // UI Components
  const RecipeCard = ({ recipe, isDraggable = true }) => (
    <div
      className={`recipe-card ${isDraggable ? 'cursor-grab hover:shadow-md active:cursor-grabbing' : ''}`}
      style={{
        padding: '12px',
        margin: '8px 0',
        cursor: isDraggable ? 'grab' : 'default',
        transition: 'all 0.2s ease'
      }}
      draggable={isDraggable}
      onDragStart={(e) => isDraggable && handleDragStart(e, recipe)}
    >
      <div className="flex justify-between align-center mb-2">
        <h4 style={{ 
          fontSize: '0.875rem', 
          fontWeight: '600', 
          margin: 0,
          lineHeight: '1.2'
        }}>
          {recipe.recipe_name || recipe.title}
        </h4>
        <div style={{ 
          fontSize: '0.75rem', 
          color: '#ffc107',
          display: 'flex',
          alignItems: 'center',
          gap: '2px'
        }}>
          <span>⭐</span>
          <span>{recipe.rating || 4.0}</span>
        </div>
      </div>
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        fontSize: '0.75rem', 
        color: '#6c757d',
        marginBottom: '8px'
      }}>
        <span>⏱️ {recipe.prep_time || '30m'}</span>
        <span>💰 ${recipe.cost_estimate || recipe.cost}</span>
      </div>
      
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        fontSize: '0.75rem'
      }}>
        <span style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '2px 6px', 
          borderRadius: '4px',
          color: '#495057'
        }}>
          {recipe.cuisine}
        </span>
        <span style={{ color: '#6c757d' }}>
          {recipe.macros?.calories || recipe.calories} cal
        </span>
      </div>

      {recipe.tags?.slice(0, 2).map(tag => (
        <span key={tag} className="tag" style={{ 
          fontSize: '0.6rem',
          padding: '2px 6px',
          margin: '4px 2px 0 0',
          display: 'inline-block'
        }}>
          {tag}
        </span>
      ))}
    </div>
  );

  const DayCell = ({ date, meals }) => {
    const isToday = formatDate(date) === formatDate(new Date());
    const isCurrentMonth = date.getMonth() === currentDate.getMonth();
    
    return (
      <div
        style={{
          minHeight: '120px',
          border: '2px solid #e9ecef',
          borderRadius: '8px',
          padding: '8px',
          backgroundColor: isToday ? '#f0f8ff' : (isCurrentMonth ? 'white' : '#f8f9fa'),
          borderColor: isToday ? '#007bff' : '#e9ecef'
        }}
        onDragOver={handleDragOver}
        onDrop={(e) => handleDrop(e, date)}
      >
        <div className="flex justify-between align-center mb-2">
          <span style={{
            fontSize: '0.875rem',
            fontWeight: '600',
            color: isToday ? '#007bff' : (isCurrentMonth ? '#333' : '#6c757d')
          }}>
            {date.getDate()}
          </span>
          {meals.length > 0 && (
            <span style={{
              fontSize: '0.75rem',
              backgroundColor: '#28a745',
              color: 'white',
              padding: '2px 6px',
              borderRadius: '8px',
              fontWeight: '500'
            }}>
              {meals.length}
            </span>
          )}
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {meals.slice(0, 2).map(meal => (
            <div key={meal.id} style={{ position: 'relative' }} className="group">
              <div style={{
                fontSize: '0.75rem',
                backgroundColor: '#e3f2fd',
                color: '#1976d2',
                padding: '4px 6px',
                borderRadius: '4px',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {meal.recipe_name || meal.name}
              </div>
              <button
                onClick={() => removeMealFromDate(date, meal.id)}
                style={{
                  position: 'absolute',
                  top: '-2px',
                  right: '-2px',
                  width: '16px',
                  height: '16px',
                  backgroundColor: '#dc3545',
                  color: 'white',
                  border: 'none',
                  borderRadius: '50%',
                  fontSize: '10px',
                  cursor: 'pointer',
                  opacity: 0
                }}
                onMouseEnter={(e) => e.target.style.opacity = 1}
                onMouseLeave={(e) => e.target.style.opacity = 0}
              >
                ×
              </button>
            </div>
          ))}
          {meals.length > 2 && (
            <div style={{ fontSize: '0.7rem', color: '#6c757d' }}>
              +{meals.length - 2} more
            </div>
          )}
        </div>
      </div>
    );
  };

  const weekDates = getWeekDates();

  const renderRecipe = (rec, idx) => {
  const recipeName = rec.recipe_name || rec.recipe_text?.split('\n')[0] || `Recipe ${idx + 1}`;
  const ingredients = rec.ingredients || [];
  const directions = rec.directions || [];
  const macros = rec.macros || {};
  const tags = rec.tags || [];
  
  return (
    <div 
      key={idx} 
      className="mb-8 border border-gray-200 rounded-lg overflow-hidden shadow-sm cursor-pointer"
      onDoubleClick={() => handleDoubleClickAddToNutrition(rec, idx)}
      title="Double-click to add to nutrition log"
    >
      {/* Recipe Header */}
      <div className="bg-gradient-to-r from-blue-50 to-green-50 p-4 border-b border-gray-200">
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-xl font-bold text-gray-900">Recipe {idx + 1}: {recipeName}</h3>
          <div className="flex gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDoubleClickAddToNutrition(rec, idx);
              }}
              disabled={addingToNutrition[idx]}
              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 disabled:opacity-50 flex items-center"
            >
              {addingToNutrition[idx] ? (
                <>
                  <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                  Adding...
                </>
              ) : (
                <>
                  <Utensils className="w-4 h-4 mr-2" />
                  Log Nutrition
                </>
              )}
            </button>
            <button
              onClick={() => addMealToDate(new Date(), rec)}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
            >
              Add to Meal Plan
            </button>
            <button
              onClick={() => handleRegenerateRecipe(idx)}
              disabled={regeneratingIndex === idx || loading}
              className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {regeneratingIndex === idx ? 'Regenerating...' : 'Regenerate'}
            </button>
          </div>
        </div>
        
        {/* Nutrition Summary Card */}
        <div className="bg-white rounded-lg p-4 shadow-sm">
          <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
            <Utensils className="w-4 h-4 mr-2 text-green-600" />
            Nutrition & Cost Summary
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-center">
            <div className="bg-blue-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-blue-600">{macros.calories || 'N/A'}</div>
              <div className="text-sm text-blue-800">Calories</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-red-600">{String(macros.protein || '0').replace('g', '')}g</div>
              <div className="text-sm text-red-800">Protein</div>
            </div>
            <div className="bg-yellow-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-yellow-600">{String(macros.carbs || '0').replace('g', '')}g</div>
              <div className="text-sm text-yellow-800">Carbs</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-purple-600">{String(macros.fat || '0').replace('g', '')}g</div>
              <div className="text-sm text-purple-800">Fat</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3">
              <div className="text-2xl font-bold text-green-600">${typeof rec.cost_estimate === 'number' ? rec.cost_estimate.toFixed(2) : '0.00'}</div>
              <div className="text-sm text-green-800">Cost</div>
            </div>
          </div>
        </div>

        {/* Double-click hint */}
        <div className="mt-3 bg-green-50 border border-green-200 rounded-lg p-3 flex items-center">
          <CheckCircle className="w-5 h-5 text-green-600 mr-3" />
          <div className="text-sm text-green-800">
            <strong>Quick Tip:</strong> Double-click anywhere on this recipe card to automatically log it to your nutrition tracker!
          </div>
        </div>
      </div>

      {/* Rest of your existing recipe rendering code for ingredients, directions, etc. */}
      <div className="p-4">
        {/* Your existing ingredients and directions rendering */}
        {ingredients.length > 0 && (
          <div className="mb-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Ingredients</h4>
            <ul className="space-y-2">
              {ingredients.map((ing, i) => (
                <li key={i} className="flex items-center text-gray-700">
                  <span className="w-2 h-2 bg-blue-500 rounded-full mr-3"></span>
                  {ing.quantity || ''} {ing.unit || ''} {ing.name || 'Unknown ingredient'}
                </li>
              ))}
            </ul>
          </div>
        )}

        {directions.length > 0 && (
          <div className="mb-4">
            <h4 className="text-lg font-semibold text-gray-900 mb-3">Directions</h4>
            <ol className="space-y-3">
              {directions.map((step, i) => (
                <li key={i} className="flex text-gray-700">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-semibold mr-3 mt-0.5">
                    {i + 1}
                  </span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/*RecipeRatings component */}
        <RecipeRatings 
          recipeData={rec}
          userId={userId}
          onRatingSubmit={(rating, feedback) => console.log(`Recipe rated ${rating} stars`, feedback)}
        />
      </div>
    </div>
  );
};

  return (
    <div className="app-container">
      <div className="card-full">
        {/* Tab Navigation */}
        <div className="tab-navigation">
          <button
            onClick={() => setActiveTab('generate')}
            className={`tab-button ${activeTab === 'generate' ? 'active' : ''}`}
          >
            🍳 Generate Recipes
          </button>
          <button
            onClick={() => setActiveTab('meal-plan')}
            className={`tab-button ${activeTab === 'meal-plan' ? 'active' : ''}`}
          >
            📅 Meal Planning
          </button>
        </div>

        {/* Recipe Generation Tab */}
        {activeTab === 'generate' && (
          <div>
            {/* Header */}
            <div className="nav-header">
              <div>
                <h1 style={{ textAlign: 'left' }}>Generate Recipes</h1>
                <p className="subtitle" style={{ textAlign: 'left', marginBottom: 0 }}>
                  Create personalized recipes based on your preferences and budget
                </p>
              </div>
              
              <div className="nav-buttons">
                <button
                  onClick={() => navigate('/home')}
                  className="btn-secondary btn-sm"
                >
                  🏠 Home
                </button>
                <button
                  onClick={() => navigate('/preferences')}
                  className="btn-secondary btn-sm"
                >
                  Preferences
                </button>
                <button
                  onClick={() => navigate('/grocery')}
                  className="btn-success btn-sm"
                >
                  View Grocery List
                </button>
              </div>
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="error-message">
                {errorMsg}
              </div>
            )}

            {/* Recipe Generation Form */}
            <div className="recipe-card mb-4">
              <h2 className="mb-3" style={{ textAlign: 'left' }}>Generate 3 Recipes</h2>
              <p style={{ color: '#6c757d', marginBottom: '24px' }}>
                Enter what type of meals you'd like and your budget to get started
              </p>
              
              <form onSubmit={handleGenerate}>
                <div className="form-group">
                  <label htmlFor="title">Type of Meals</label>
                  <input
                    id="title"
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="eg. Quick Pasta Dishes"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="budget">Budget (USD)</label>
                  <input
                    id="budget"
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                    placeholder="e.g. 20.00"
                    required
                    disabled={loading}
                  />
                </div>

                <div className="flex gap-2">
                  <button 
                    className="btn-primary" 
                    type="submit" 
                    disabled={loading || !userId}
                    style={{ flex: 1 }}
                  >
                    {loading ? 'Generating…' : 'Generate'}
                  </button>
                  
                  {recipeResults && recipeResults.length > 0 && (
                    <button
                      type="button"
                      onClick={handleSaveToGroceryList}
                      disabled={savingToGroceryList}
                      className="btn-success"
                      style={{ 
                        flex: 1,
                        backgroundColor: '#28a745'
                      }}
                    >
                      {savingToGroceryList ? 'Adding...' : 'Generate Grocery List'}
                    </button>
                  )}
                </div>
              </form>
            </div>

            {/* Generated Recipes */}
            {recipeResults && recipeResults.length > 0 && (
              <div>
                <div style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center',
                  marginBottom: '24px'
                }}>
                  <h2 style={{ margin: 0 }}>Generated Recipes</h2>
                  <p style={{ 
                    color: '#6c757d', 
                    margin: 0,
                    fontSize: '0.875rem'
                  }}>
                    Don't like a recipe? Click "Regenerate" to get a new one!
                  </p>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  {recipeResults.map((rec, idx) => renderRecipe(rec, idx))}
                </div>
              </div>
            )}

            {/* Empty State */}
            {!recipeResults && !loading && (
              <div style={{ 
                textAlign: 'center', 
                padding: '60px 20px',
                color: '#6c757d'
              }}>
                <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🍳</div>
                <h3 style={{ marginBottom: '8px' }}>Ready to Cook?</h3>
                <p>Enter your meal preferences above to generate personalized recipes!</p>
              </div>
            )}
          </div>
        )}

        {/* Meal Planning Tab */}
        {activeTab === 'meal-plan' && (
          <div>
            {/* Meal Planning Header */}
            <div className="recipe-card mb-4">
              <div className="flex justify-between align-center mb-3">
                <div>
                  <h2 style={{ margin: 0, textAlign: 'left' }}>📅 Smart Meal Planning</h2>
                  <p style={{ color: '#6c757d', margin: '4px 0 0 0' }}>
                    Plan your weekly meals and generate grocery lists automatically
                  </p>
                </div>
                
                <div className="flex align-center gap-2">
                  <button
                    onClick={() => setShowRecipePanel(!showRecipePanel)}
                    className="btn-primary btn-sm"
                  >
                    🍳 {showRecipePanel ? 'Hide' : 'Show'} Recipes
                  </button>
                </div>
              </div>

              {/* Stats Bar */}
              <div className="nutrition-grid">
                <div className="nutrition-item">
                  <span className="nutrition-value" style={{ color: '#007bff' }}>
                    ${totalBudget.toFixed(2)}
                  </span>
                  <span className="nutrition-label">Weekly Budget</span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-value" style={{ color: '#28a745' }}>
                    {Math.floor(totalPrepTime / 60)}h {totalPrepTime % 60}m
                  </span>
                  <span className="nutrition-label">Total Prep Time</span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-value" style={{ color: '#6f42c1' }}>
                    {Object.keys(plannedMeals).length}
                  </span>
                  <span className="nutrition-label">Planned Days</span>
                </div>
                <div className="nutrition-item">
                  <span className="nutrition-value" style={{ color: '#fd7e14' }}>
                    {availableRecipes.length}
                  </span>
                  <span className="nutrition-label">Available Recipes</span>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              {/* Recipe Panel */}
              {showRecipePanel && (
                <div style={{
                  width: '320px',
                  backgroundColor: 'white',
                  borderRadius: '12px',
                  border: '2px solid #e9ecef',
                  padding: '16px',
                  height: 'fit-content'
                }}>
                  <div className="flex justify-between align-center mb-3">
                    <h3 style={{ margin: 0, fontSize: '1.125rem' }}>Your Recipes</h3>
                    <button 
                      onClick={loadAvailableRecipes} 
                      style={{
                        background: 'none',
                        border: 'none',
                        color: '#6c757d',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        padding: '4px'
                      }}
                    >
                      🔄
                    </button>
                  </div>
                  
                  <div style={{ 
                    maxHeight: '400px', 
                    overflowY: 'auto',
                    marginBottom: '16px'
                  }}>
                    {availableRecipes.length > 0 ? (
                      availableRecipes.map(recipe => (
                        <RecipeCard key={recipe.id} recipe={recipe} />
                      ))
                    ) : (
                      <div style={{ 
                        textAlign: 'center', 
                        padding: '32px 16px',
                        color: '#6c757d'
                      }}>
                        <div style={{ fontSize: '2rem', marginBottom: '8px' }}>🍳</div>
                        <p style={{ fontSize: '0.875rem', margin: 0 }}>No recipes available</p>
                        <p style={{ fontSize: '0.75rem', margin: '4px 0 0 0' }}>Generate some recipes first!</p>
                      </div>
                    )}
                  </div>

                  <button 
                    onClick={() => setActiveTab('generate')}
                    className="btn-primary"
                    style={{ width: '100%' }}
                  >
                    ➕ Generate New Recipes
                  </button>
                </div>
              )}

              {/* Calendar */}
              <div style={{ flex: 1 }}>
                <div style={{
                  backgroundColor: 'white',
                  borderRadius: '12px',
                  border: '2px solid #e9ecef'
                }}>
                  {/* Calendar Header */}
                  <div className="flex justify-between align-center" style={{ 
                    padding: '16px', 
                    borderBottom: '2px solid #f8f9fa' 
                  }}>
                    <button
                      onClick={() => navigateCalendar(-1)}
                      style={{
                        padding: '8px 12px',
                        backgroundColor: '#f8f9fa',
                        border: '2px solid #e9ecef',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        minHeight: 'auto'
                      }}
                    >
                      ←
                    </button>
                    
                    <h3 style={{ margin: 0, fontSize: '1.125rem', color: '#333' }}>
                      Week of {weekDates[0].toLocaleDateString('en-US', { 
                        month: 'long', 
                        day: 'numeric', 
                        year: 'numeric' 
                      })}
                    </h3>
                    
                    <button
                      onClick={() => navigateCalendar(1)}
                      style={{
                        padding: '8px 12px',
                        backgroundColor: '#f8f9fa',
                        border: '2px solid #e9ecef',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        minHeight: 'auto'
                      }}
                    >
                      →
                    </button>
                  </div>

                  {/* Calendar Grid */}
                  <div style={{ 
                    display: 'grid', 
                    gridTemplateColumns: 'repeat(7, 1fr)', 
                    gap: '0' 
                  }}>
                    {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                      <div key={day} style={{
                        padding: '12px',
                        borderBottom: '2px solid #f8f9fa',
                        fontSize: '0.875rem',
                        fontWeight: '600',
                        color: '#495057',
                        textAlign: 'center',
                        backgroundColor: '#f8f9fa'
                      }}>
                        {day}
                      </div>
                    ))}
                    {weekDates.map(date => (
                      <DayCell
                        key={formatDate(date)}
                        date={date}
                        meals={getMealsForDate(date)}
                      />
                    ))}
                  </div>
                </div>

                {/* Generate Grocery List Button */}
                {Object.keys(plannedMeals).length > 0 && (
                  <div style={{ marginTop: '16px', textAlign: 'center' }}>
                    <button
                      onClick={generateGroceryListFromMealPlan}
                      disabled={mealPlanLoading}
                      className="btn-success"
                      style={{ 
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}
                    >
                      🛒 {mealPlanLoading ? 'Generating...' : 'Generate Grocery List from Meal Plan'}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Prep Time Optimization */}
            {Object.keys(plannedMeals).length > 0 && (
              <div className="recipe-card mt-4">
                <h3 className="mb-3" style={{ textAlign: 'left' }}>
                  ⏱️ Prep Time Optimization Tips
                </h3>
                
                <div style={{ 
                  display: 'grid', 
                  gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
                  gap: '16px' 
                }}>
                  <div style={{
                    backgroundColor: '#e3f2fd',
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid #2196f3'
                  }}>
                    <h4 style={{ color: '#1565c0', marginBottom: '8px', fontSize: '1rem' }}>
                      Meal Prep Day
                    </h4>
                    <p style={{ 
                      fontSize: '0.875rem', 
                      color: '#1976d2', 
                      margin: '0 0 4px 0' 
                    }}>
                      Sunday: Prep ingredients in bulk to save time during the week
                    </p>
                    <p style={{ fontSize: '0.75rem', color: '#1565c0', margin: 0 }}>
                      Can save up to 45 minutes daily
                    </p>
                  </div>
                  
                  <div style={{
                    backgroundColor: '#e8f5e8',
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid #4caf50'
                  }}>
                    <h4 style={{ color: '#2e7d32', marginBottom: '8px', fontSize: '1rem' }}>
                      Batch Cooking
                    </h4>
                    <p style={{ 
                      fontSize: '0.875rem', 
                      color: '#388e3c', 
                      margin: '0 0 4px 0' 
                    }}>
                      Cook larger portions for easy leftovers and quick reheats
                    </p>
                    <p style={{ fontSize: '0.75rem', color: '#2e7d32', margin: 0 }}>
                      Perfect for busy weeknight dinners
                    </p>
                  </div>
                  
                  <div style={{
                    backgroundColor: '#fff8e1',
                    padding: '16px',
                    borderRadius: '8px',
                    border: '1px solid #ffc107'
                  }}>
                    <h4 style={{ color: '#f57c00', marginBottom: '8px', fontSize: '1rem' }}>
                      Smart Scheduling
                    </h4>
                    <p style={{ 
                      fontSize: '0.875rem', 
                      color: '#ff8f00', 
                      margin: '0 0 4px 0' 
                    }}>
                      Plan quick meals on your busiest days
                    </p>
                    <p style={{ fontSize: '0.75rem', color: '#f57c00', margin: 0 }}>
                      Based on your weekly routine
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Empty State for Meal Planning */}
            {Object.keys(plannedMeals).length === 0 && (
              <div style={{ 
                textAlign: 'center', 
                padding: '60px 20px',
                color: '#6c757d'
              }}>
                <div style={{ fontSize: '4rem', marginBottom: '16px' }}>📅</div>
                <h3 style={{ marginBottom: '8px' }}>Start Planning Your Meals</h3>
                <p style={{ marginBottom: '24px' }}>
                  Drag recipes from the panel to calendar days, or generate new recipes to get started!
                </p>
                {!showRecipePanel && (
                  <button
                    onClick={() => setShowRecipePanel(true)}
                    className="btn-primary"
                    style={{ width: 'auto', minWidth: '200px' }}
                  >
                    Show Recipe Panel
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}