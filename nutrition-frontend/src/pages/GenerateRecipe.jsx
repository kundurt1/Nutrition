import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import RecipeRatings from '../components/RecipeRatings';
import { Calendar, Clock, DollarSign, Users, ChefHat, ShoppingCart, Plus, X, Star, RefreshCw } from 'lucide-react';

export default function GenerateRecipe() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [activeTab, setActiveTab] = useState('generate'); // 'generate' or 'meal-plan'
  
  // Recipe Generation State
  const [title, setTitle] = useState('');
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [recipeResults, setRecipeResults] = useState(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);
  const [showGroceryList, setShowGroceryList] = useState(false);
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

  // Existing recipe generation functions...
  const handleGenerate = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setRecipeResults(null);
    setShowGroceryList(false);

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

    // Save to backend
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

    // Save to backend
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
      className={`bg-white border rounded-lg p-3 shadow-sm transition-all duration-200 ${
        isDraggable ? 'cursor-grab hover:shadow-md active:cursor-grabbing' : ''
      }`}
      draggable={isDraggable}
      onDragStart={(e) => isDraggable && handleDragStart(e, recipe)}
    >
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-semibold text-sm text-gray-800 line-clamp-2">{recipe.recipe_name || recipe.title}</h4>
        <div className="flex items-center text-xs text-yellow-600">
          <Star className="w-3 h-3 fill-current" />
          <span className="ml-1">{recipe.rating || 4.0}</span>
        </div>
      </div>
      
      <div className="space-y-1 text-xs text-gray-600">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Clock className="w-3 h-3 mr-1" />
            <span>{recipe.prep_time || '30m'}</span>
          </div>
          <div className="flex items-center">
            <DollarSign className="w-3 h-3 mr-1" />
            <span>${recipe.cost_estimate || recipe.cost}</span>
          </div>
        </div>
        
        <div className="flex items-center justify-between">
          <span className="text-xs bg-gray-100 px-2 py-1 rounded">{recipe.cuisine}</span>
          <span className="text-xs text-gray-500">{recipe.macros?.calories || recipe.calories} cal</span>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 mt-2">
        {recipe.tags?.slice(0, 2).map(tag => (
          <span key={tag} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
            {tag}
          </span>
        ))}
      </div>
    </div>
  );

  const DayCell = ({ date, meals }) => {
    const isToday = formatDate(date) === formatDate(new Date());
    const isCurrentMonth = date.getMonth() === currentDate.getMonth();
    
    return (
      <div
        className={`min-h-24 border border-gray-200 p-2 ${
          isCurrentMonth ? 'bg-white' : 'bg-gray-50'
        } ${isToday ? 'bg-blue-50 border-blue-300' : ''}`}
        onDragOver={handleDragOver}
        onDrop={(e) => handleDrop(e, date)}
      >
        <div className="flex justify-between items-center mb-1">
          <span className={`text-sm font-medium ${
            isToday ? 'text-blue-600' : isCurrentMonth ? 'text-gray-900' : 'text-gray-400'
          }`}>
            {date.getDate()}
          </span>
          {meals.length > 0 && (
            <span className="text-xs bg-green-100 text-green-700 px-1 rounded">
              {meals.length}
            </span>
          )}
        </div>
        
        <div className="space-y-1">
          {meals.slice(0, 2).map(meal => (
            <div key={meal.id} className="relative group">
              <div className="text-xs bg-blue-100 text-blue-800 p-1 rounded truncate">
                {meal.recipe_name || meal.name}
              </div>
              <button
                onClick={() => removeMealFromDate(date, meal.id)}
                className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full opacity-0 group-hover:opacity-100 transition-opacity text-xs flex items-center justify-center"
              >
                <X className="w-2 h-2" />
              </button>
            </div>
          ))}
          {meals.length > 2 && (
            <div className="text-xs text-gray-500">+{meals.length - 2} more</div>
          )}
        </div>
      </div>
    );
  };

  const weekDates = getWeekDates();

  // Existing recipe generation render functions...
  const renderRecipe = (rec, idx) => {
    const recipeName = rec.recipe_name || rec.recipe_text?.split('\n')[0] || `Recipe ${idx + 1}`;
    const ingredients = rec.ingredients || [];
    const directions = rec.directions || [];
    const macros = rec.macros || {};
    const tags = rec.tags || [];
    const groceryList = rec.grocery_list || [];
    
    return (
      <div key={idx} style={{ marginBottom: '32px', border: '1px solid #ddd', padding: '16px', borderRadius: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3>Recipe {idx + 1}: {recipeName}</h3>
          <div className="flex gap-2">
            <button
              onClick={() => addMealToDate(new Date(), rec)}
              className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700"
            >
              Add to Meal Plan
            </button>
            <button
              onClick={() => handleRegenerateRecipe(idx)}
              disabled={regeneratingIndex === idx || loading}
              style={{
                padding: '8px 16px',
                backgroundColor: regeneratingIndex === idx ? '#ccc' : '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: regeneratingIndex === idx ? 'not-allowed' : 'pointer',
                fontSize: '14px'
              }}
            >
              {regeneratingIndex === idx ? 'Regenerating...' : 'Regenerate'}
            </button>
          </div>
        </div>

        {/* Rest of recipe rendering... */}
        {ingredients.length > 0 && (
          <>
            <h4>Ingredients</h4>
            <ul>
              {ingredients.map((ing, i) => (
                <li key={i}>
                  {ing.quantity || ''} {ing.unit || ''} {ing.name || 'Unknown ingredient'}
                </li>
              ))}
            </ul>
          </>
        )}

        {directions.length > 0 && (
          <>
            <h4>Directions</h4>
            <ol>
              {directions.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </>
        )}

        <h4>Nutrition</h4>
        <ul style={{ marginBottom: '16px' }}>
          <li>Calories: {macros.calories || 'N/A'}</li>
          <li>Protein: {macros.protein || 'N/A'}</li>
          <li>Carbs: {macros.carbs || 'N/A'}</li>
          <li>Fat: {macros.fat || 'N/A'}</li>
          <li>Fiber: {macros.fiber || 'N/A'}</li>
        </ul>

        <p><strong>Tags:</strong> {tags.length > 0 ? tags.join(', ') : 'None'}</p>
        <p><strong>Cuisine:</strong> {rec.cuisine || 'Not specified'}</p>
        <p><strong>Diet:</strong> {rec.diet || 'Not specified'}</p>

        <p style={{ fontStyle: 'italic' }}>
          Estimated cost: ${typeof rec.cost_estimate === 'number' ? rec.cost_estimate.toFixed(2) : '0.00'}
        </p>

        <RecipeRatings 
          recipeData={rec}
          userId={userId}
          onRatingSubmit={(rating, feedback) => console.log(`Recipe rated ${rating} stars`, feedback)}
        />
      </div>
    );
  };

  return (
    <div className="card" style={{ maxWidth: '1200px' }}>
      {/* Tab Navigation */}
      <div className="flex border-b border-gray-200 mb-6">
        <button
          onClick={() => setActiveTab('generate')}
          className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'generate'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <ChefHat className="w-4 h-4 inline mr-2" />
          Generate Recipes
        </button>
        <button
          onClick={() => setActiveTab('meal-plan')}
          className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'meal-plan'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Calendar className="w-4 h-4 inline mr-2" />
          Meal Planning
        </button>
      </div>

      {/* Recipe Generation Tab */}
      {activeTab === 'generate' && (
        <div>
          {/* Navigation Header */}
          <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h2>Generate 3 Recipes</h2>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => navigate('/home')}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#2196F3',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                🏠 Home
              </button>
              <button
                onClick={() => navigate('/preferences')}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#9E9E9E',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                Preferences
              </button>
              <button
                onClick={() => navigate('/grocery')}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                View Grocery List
              </button>
            </div>
          </div>

          {errorMsg && (
            <div style={{ 
              color: 'red', 
              marginBottom: '12px', 
              padding: '8px', 
              backgroundColor: '#ffebee', 
              borderRadius: '4px',
              border: '1px solid #ffcdd2'
            }}>
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleGenerate}>
            <div className="form-group">
              <label htmlFor="title">Recipe Title</label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Quick Pasta Dishes"
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

            <button 
              className="primary" 
              type="submit" 
              disabled={loading || !userId}
            >
              {loading ? 'Generating…' : 'Generate 3 Recipes'}
            </button>
          </form>

          {recipeResults && recipeResults.length > 0 && (
            <div style={{ marginTop: '24px', textAlign: 'left' }}>
              <h3>Generated Recipes</h3>
              <p style={{ color: '#666', marginBottom: '16px' }}>
                Don't like a recipe? Click "Regenerate" to get a new one or add it to your meal plan!
              </p>
              {recipeResults.map((rec, idx) => renderRecipe(rec, idx))}
            </div>
          )}
        </div>
      )}

      {/* Meal Planning Tab */}
      {activeTab === 'meal-plan' && (
        <div>
          {/* Meal Planning Header */}
          <div className="bg-gray-50 rounded-lg p-6 mb-6">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900 flex items-center">
                  <Calendar className="w-6 h-6 mr-3 text-blue-600" />
                  Smart Meal Planning
                </h2>
                <p className="text-gray-600 mt-1">Plan your weekly meals and generate grocery lists automatically</p>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className="flex bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('week')}
                    className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                      viewMode === 'week' 
                        ? 'bg-white text-gray-900 shadow-sm' 
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    Week
                  </button>
                </div>
                
                <button
                  onClick={() => setShowRecipePanel(!showRecipePanel)}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                >
                  <ChefHat className="w-4 h-4 mr-2" />
                  {showRecipePanel ? 'Hide' : 'Show'} Recipes
                </button>
              </div>
            </div>

            {/* Stats Bar */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-200">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">${totalBudget.toFixed(2)}</div>
                <div className="text-sm text-gray-600">Weekly Budget</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{Math.floor(totalPrepTime / 60)}h {totalPrepTime % 60}m</div>
                <div className="text-sm text-gray-600">Total Prep Time</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{Object.keys(plannedMeals).length}</div>
                <div className="text-sm text-gray-600">Planned Days</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">{availableRecipes.length}</div>
                <div className="text-sm text-gray-600">Available Recipes</div>
              </div>
            </div>
          </div>

          <div className="flex gap-6">
            {/* Recipe Panel */}
            {showRecipePanel && (
              <div className="w-80 bg-white rounded-lg shadow-sm p-4 border border-gray-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">Your Recipes</h3>
                  <button onClick={loadAvailableRecipes} className="text-gray-400 hover:text-gray-600">
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
                
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {availableRecipes.length > 0 ? (
                    availableRecipes.map(recipe => (
                      <RecipeCard key={recipe.id} recipe={recipe} />
                    ))
                  ) : (
                    <div className="text-center py-8 text-gray-500">
                      <ChefHat className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p>No recipes available</p>
                      <p className="text-sm">Generate some recipes first!</p>
                    </div>
                  )}
                </div>

                <button 
                  onClick={() => setActiveTab('generate')}
                  className="w-full mt-4 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Generate New Recipes
                </button>
              </div>
            )}

            {/* Calendar */}
            <div className="flex-1">
              <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                {/* Calendar Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-200">
                  <button
                    onClick={() => navigateCalendar(-1)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    ←
                  </button>
                  
                  <h3 className="text-lg font-semibold text-gray-900">
                    Week of {weekDates[0].toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                  </h3>
                  
                  <button
                    onClick={() => navigateCalendar(1)}
                    className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    →
                  </button>
                </div>

                {/* Calendar Grid */}
                <div className="grid grid-cols-7 gap-0">
                  {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
                    <div key={day} className="p-3 border-b border-gray-200 font-medium text-sm text-gray-700 text-center">
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
                <div className="mt-4 text-center">
                  <button
                    onClick={generateGroceryListFromMealPlan}
                    disabled={mealPlanLoading}
                    className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 transition-colors flex items-center mx-auto"
                  >
                    <ShoppingCart className="w-4 h-4 mr-2" />
                    {mealPlanLoading ? 'Generating...' : 'Generate Grocery List from Meal Plan'}
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Prep Time Optimization */}
          {Object.keys(plannedMeals).length > 0 && (
            <div className="mt-6 bg-white rounded-lg shadow-sm p-6 border border-gray-200">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center">
                <Clock className="w-5 h-5 mr-2 text-blue-600" />
                Prep Time Optimization Tips
              </h3>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h4 className="font-medium text-blue-900 mb-2">Meal Prep Day</h4>
                  <p className="text-sm text-blue-700">Sunday: Prep ingredients in bulk to save time during the week</p>
                  <p className="text-xs text-blue-600 mt-1">Can save up to 45 minutes daily</p>
                </div>
                
                <div className="bg-green-50 p-4 rounded-lg">
                  <h4 className="font-medium text-green-900 mb-2">Batch Cooking</h4>
                  <p className="text-sm text-green-700">Cook larger portions for easy leftovers and quick reheats</p>
                  <p className="text-xs text-green-600 mt-1">Perfect for busy weeknight dinners</p>
                </div>
                
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h4 className="font-medium text-yellow-900 mb-2">Smart Scheduling</h4>
                  <p className="text-sm text-yellow-700">Plan quick meals on your busiest days</p>
                  <p className="text-xs text-yellow-600 mt-1">Based on your weekly routine</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Additional functions that were referenced but cut off...
const handleRegenerateRecipe = async (recipeIndex) => {
  // Implementation for regenerating recipes
  console.log('Regenerating recipe at index:', recipeIndex);
};