import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import RecipeRating from '../components/RecipeRatings'; // Import the rating component
import RecipeScaling from '../components/RecipeScaling';
import { Utensils, ChefHat, DollarSign, Clock, Users, Brain } from 'lucide-react';

export default function GenerateRecipe() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [activeTab, setActiveTab] = useState('generate');

  // Recipe Generation State
  const [title, setTitle] = useState('');
  const [budget, setBudget] = useState('');
  const [numRecipes, setNumRecipes] = useState(3); // NEW: 1 or 3
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [recipeResults, setRecipeResults] = useState(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);
  const [savingToGroceryList, setSavingToGroceryList] = useState(false);

  // Advanced AI State
  const [useAdvancedAI, setUseAdvancedAI] = useState(true);
  const [showAIThinking, setShowAIThinking] = useState(false);
  const [thoughtSteps, setThoughtSteps] = useState([]);
  const [aiExplanation, setAiExplanation] = useState('');

  // Recent Recipes State
  const [recentRecipes, setRecentRecipes] = useState([]);
  const [recentRecipesLoading, setRecentRecipesLoading] = useState(false);

  // Meal Planning State
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('week');
  const [plannedMeals, setPlannedMeals] = useState({});
  const [availableRecipes, setAvailableRecipes] = useState([]);
  const [showRecipePanel, setShowRecipePanel] = useState(true);
  const [draggedRecipe, setDraggedRecipe] = useState(null);
  const [mealPlanLoading, setMealPlanLoading] = useState(false);
  const [addingToNutrition, setAddingToNutrition] = useState({});

  // Helper to stringify ingredient objects consistently
  const formatIngredient = (ing) => {
    if (typeof ing === 'string') return ing;
    if (ing && typeof ing === 'object') {
      const { name, quantity, unit } = ing;
      const qty = [quantity, unit].filter(Boolean).join(' ');
      return [qty, name].filter(Boolean).join(' ').trim();
    }
    return '';
  };

  // Load user's recent recipes from the last week
  const loadRecentRecipes = useCallback(async () => {
    if (!userId) return;

    setRecentRecipesLoading(true);
    try {
      const oneWeekAgo = new Date();
      oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
      const oneWeekAgoStr = oneWeekAgo.toISOString().split('T')[0];

      const response = await fetch(`http://localhost:8000/user-recipes/${userId}?start_date=${oneWeekAgoStr}&limit=50`);

      if (response.ok) {
        const data = await response.json();
        // Normalize ingredients so UI never receives raw objects
        const normalized = (data.recipes || []).map((r, i) => ({
          ...r,
          id: r.id || r.recipe_id || `recent_${Date.now()}_${i}`,
          recipe_name: r.recipe_name || r.title || `Recipe ${i + 1}`,
          ingredients: Array.isArray(r.ingredients) ? r.ingredients.map(formatIngredient) : [],
          directions: Array.isArray(r.directions) ? r.directions : [],
          cost_estimate: Number(r.cost_estimate || r.cost || 0),
        }));
        setRecentRecipes(normalized);
      } else {
        console.error('Failed to load recent recipes:', response.status);
        setRecentRecipes([]);
      }
    } catch (error) {
      console.error('Error loading recent recipes:', error);
      setRecentRecipes([]);
    } finally {
      setRecentRecipesLoading(false);
    }
  }, [userId]);

  // Memoized calculations for performance
  const mealPlanStats = useMemo(() => {
    const meals = Object.values(plannedMeals).flat();
    return {
      totalBudget: meals.reduce((sum, meal) => sum + (parseFloat(meal.cost) || parseFloat(meal.cost_estimate) || 0), 0),
      totalPrepTime: meals.reduce((sum, meal) => sum + (parseInt(meal.prepTime) || parseInt(meal.prep_time) || 0) + (parseInt(meal.cookTime) || parseInt(meal.cook_time) || 0), 0),
      plannedDaysCount: Object.keys(plannedMeals).length,
      totalMealsCount: meals.length
    };
  }, [plannedMeals]);

  const getWeekDates = (date) => {
    const week = [];
    const startOfWeek = new Date(date);
    const day = startOfWeek.getDay();
    const diff = startOfWeek.getDate() - day;
    startOfWeek.setDate(diff);

    for (let i = 0; i < 7; i++) {
      const day = new Date(startOfWeek);
      day.setDate(startOfWeek.getDate() + i);
      week.push(day);
    }
    return week;
  };

  // Compute week dates based on currentDate
  const weekDates = useMemo(() => getWeekDates(currentDate), [currentDate]);

  // Navigate calendar by weeks
  const navigateCalendar = useCallback((direction) => {
    setCurrentDate(prev => {
      const newDate = new Date(prev);
      newDate.setDate(newDate.getDate() + (direction * 7));
      return newDate;
    });
  }, []);

  // Get meals for a specific date
  const getMealsForDate = useCallback((date) => {
    const dateKey = date.toISOString().split('T')[0];
    return plannedMeals[dateKey] || [];
  }, [plannedMeals]);

  // Drag and drop handlers
  const handleDragStart = useCallback((e, recipe) => {
    setDraggedRecipe(recipe);
    e.dataTransfer.effectAllowed = 'copy';
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback(async (e, date) => {
    e.preventDefault();

    if (!draggedRecipe || !userId) return;

    const dateKey = date.toISOString().split('T')[0];

    // Add meal to local state
    setPlannedMeals(prev => ({
      ...prev,
      [dateKey]: [...(prev[dateKey] || []), {
        ...draggedRecipe,
        id: draggedRecipe.id || Date.now(),
        date: dateKey
      }]
    }));

    // Save to backend
    await saveMealPlan(dateKey, draggedRecipe);

    setDraggedRecipe(null);
  }, [draggedRecipe, userId]);

  // Remove meal from date
  const removeMealFromDate = useCallback(async (date, mealId) => {
    const dateKey = date.toISOString().split('T')[0];

    // Update local state
    setPlannedMeals(prev => ({
      ...prev,
      [dateKey]: (prev[dateKey] || []).filter(meal => meal.id !== mealId)
    }));

    // Save to backend
    try {
      await fetch(`http://localhost:8000/meal-plans/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          meal_plans: {
            ...plannedMeals,
            [dateKey]: (plannedMeals[dateKey] || []).filter(meal => meal.id !== mealId)
          }
        })
      });
    } catch (error) {
      console.error('Error removing meal:', error);
    }
  }, [userId, plannedMeals]);

  // Save meal plan
  const saveMealPlan = async (dateKey, recipe) => {
    try {
      await fetch(`http://localhost:8000/meal-plans/${userId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          meal_plans: {
            ...plannedMeals,
            [dateKey]: [...(plannedMeals[dateKey] || []), recipe]
          }
        })
      });
    } catch (error) {
      console.error('Error saving meal plan:', error);
    }
  };

  // Generate grocery list from meal plans
  const generateGroceryList = useCallback(async () => {
    if (!userId || Object.keys(plannedMeals).length === 0) {
      alert('Please add some meals to your meal plan first!');
      return;
    }

    setMealPlanLoading(true);
    try {
      const response = await fetch('http://localhost:8000/generate-grocery-list-from-meal-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          meal_plans: plannedMeals
        })
      });

      if (response.ok) {
        const data = await response.json();
        alert(`Grocery list generated with ${data.items_count || 0} items!`);
        navigate('/grocery');
      } else {
        alert('Failed to generate grocery list');
      }
    } catch (error) {
      console.error('Error generating grocery list:', error);
      alert('Error generating grocery list');
    } finally {
      setMealPlanLoading(false);
    }
  }, [userId, plannedMeals, navigate]);

  // Load meal plans
  const loadMealPlans = useCallback(async () => {
    if (!userId) return;
    try {
      const response = await fetch(`http://localhost:8000/meal-plans/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setPlannedMeals(data.meal_plans || {});
      }
    } catch (error) {
      console.error('Error loading meal plans:', error);
    }
  }, [userId]);

  const loadAvailableRecipes = useCallback(async () => {
    if (!userId) return;

    try {
      const response = await fetch(`http://localhost:8000/user-recipes/${userId}?limit=20`);

      if (response.ok) {
        const data = await response.json();
        const savedRecipes = data.recipes || [];
        const generatedRecipes = recipeResults || [];

        const recipeMap = new Map();

        savedRecipes.forEach(recipe => {
          const id = recipe.id || recipe.recipe_id || `saved-${Date.now()}-${Math.random()}`;
          recipeMap.set(id, {
            ...recipe,
            id,
            recipe_name: recipe.recipe_name || recipe.title || 'Unnamed Recipe',
            cost_estimate: parseFloat(recipe.cost_estimate || recipe.cost || 0),
            prep_time: recipe.prep_time || recipe.prepTime || '30 min',
            cook_time: recipe.cook_time || recipe.cookTime || '30 min'
          });
        });

        generatedRecipes.forEach(recipe => {
          const id = recipe.id || `generated-${Date.now()}-${Math.random()}`;
          recipeMap.set(id, {
            ...recipe,
            id,
            recipe_name: recipe.recipe_name || recipe.title || 'Unnamed Recipe',
            cost_estimate: parseFloat(recipe.cost_estimate || recipe.cost || 0),
            prep_time: recipe.prep_time || recipe.prepTime || '30 min',
            cook_time: recipe.cook_time || recipe.cookTime || '30 min'
          });
        });

        const allRecipes = Array.from(recipeMap.values());
        setAvailableRecipes(allRecipes);

      } else {
        console.error('Failed to load recipes from backend:', response.status);
        setAvailableRecipes(recipeResults || []);
      }
    } catch (error) {
      console.error('Error loading available recipes:', error);
      setAvailableRecipes(recipeResults || []);
    }
  }, [userId, recipeResults]);

  // Effects
  useEffect(() => {
    if (activeTab === 'meal-plan' && userId) {
      loadMealPlans();
      loadAvailableRecipes();
    }
  }, [activeTab, userId]);

  useEffect(() => {
    if (activeTab === 'recent' && userId) {
      loadRecentRecipes();
    }
  }, [activeTab, userId, loadRecentRecipes]);

  useEffect(() => {
    if (recipeResults && recipeResults.length > 0) {
      if (activeTab === 'meal-plan') {
        loadAvailableRecipes();
      }
    }
  }, [recipeResults, activeTab]);

  // Authentication and user setup
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

  // Recipe generation function
  const generateRecipes = async () => {
    if (!title.trim()) {
      setErrorMsg('Please enter a recipe title or description');
      return;
    }

    if (!userId) {
      setErrorMsg('You must be signed in to generate recipes');
      return;
    }

    setLoading(true);
    setErrorMsg('');
    setRecipeResults(null);
    setAiExplanation('');

    if (useAdvancedAI) {
      setShowAIThinking(true);
      setThoughtSteps([]);
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    try {
      const payload = {
        user_id: userId,
        title: title.trim(),
        budget: budget ? parseFloat(budget) : null,
        advanced_ai: useAdvancedAI,
        num_recipes: numRecipes  // <-- new field from dropdown/select
      };

      const res = await fetch('http://localhost:8000/generate-recipe-with-advanced-preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!res.ok) {
        let errorMessage = 'Failed to generate recipes';
        try {
          const errJson = await res.json();
          if (Array.isArray(errJson.detail)) {
            errorMessage = errJson.detail.map(
                err => `${err.loc?.join('.')}: ${err.msg}`
            ).join(', ');
          } else if (typeof errJson.detail === 'string') {
            errorMessage = errJson.detail;
          } else {
            errorMessage = JSON.stringify(errJson.detail);
          }
        } catch (parseError) {
          console.error('Error parsing error response:', parseError);
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();

      if (!data || !Array.isArray(data.recipes)) {
        throw new Error('Invalid response format from server');
      }

      if (data.ai_explanation) {
        setAiExplanation(data.ai_explanation);
      }

      // Normalize generated recipes so ingredients are strings
      const cleanedRecipes = data.recipes.map((recipe, index) => ({
        ...recipe,
        id: recipe.id || recipe.recipe_id || `recipe_${Date.now()}_${index}`,
        recipe_name: recipe.recipe_name || recipe.title || `Recipe ${index + 1}`,
        ingredients: Array.isArray(recipe.ingredients)
            ? recipe.ingredients.map(formatIngredient)
            : [],
        directions: Array.isArray(recipe.directions) ? recipe.directions : [],
        macros: recipe.macros || {},
        tags: Array.isArray(recipe.tags) ? recipe.tags : [],
        ai_insights: recipe.ai_insights || null,
        cost_estimate: Number(recipe.cost_estimate || recipe.cost || 0),
        cuisine: recipe.cuisine || 'Unknown',
        difficulty: recipe.difficulty || 'Medium'
      }));

      setRecipeResults(cleanedRecipes);

    } catch (err) {
      console.error('❌ Recipe generation error:', err);

      if (err.name === 'AbortError') {
        setErrorMsg('Request timed out. Please try again or switch to quick mode.');
      } else if (err.message.includes('422')) {
        setErrorMsg('Invalid request format. Please try again or contact support if the issue persists.');
      } else if (err.message.includes('500')) {
        setErrorMsg('Server error. Please try again in a few moments.');
      } else {
        setErrorMsg(`Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
      setShowAIThinking(false);
      clearTimeout(timeoutId);
    }
  };

  // Add to nutrition log
  const addToNutritionLog = async (recipe) => {
    if (!userId || !recipe) return;

    const recipeId = recipe.id;
    if (addingToNutrition[recipeId]) return;

    setAddingToNutrition(prev => ({ ...prev, [recipeId]: true }));

    try {
      const recipeData = {
        recipe_name: recipe.recipe_name || recipe.title || `Recipe`,
        macros: recipe.macros || recipe.macro_estimate || {
          calories: 0,
          protein: '0g',
          carbs: '0g',
          fat: '0g',
          fiber: '0g'
        },
        cost_estimate: recipe.cost_estimate || 0,
        cuisine: recipe.cuisine || 'Unknown',
        ingredients: recipe.ingredients || [],
        directions: recipe.directions || []
      };

      // Use correct endpoint
      const response = await fetch('http://localhost:8000/quick-log-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          recipe_data: recipeData
        })
      });

      if (response.ok) {
        alert('Added to nutrition log!');
      } else {
        const errorData = await response.json();
        alert(`Failed to add to nutrition log: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error adding to nutrition log:', error);
      alert('Error adding to nutrition log. Please try again.');
    } finally {
      setAddingToNutrition(prev => ({ ...prev, [recipeId]: false }));
    }
  };

  // Recipe render function with rating system
  const renderRecipe = (recipe, index) => {
    const recipeId = recipe.id || `recipe_${index}`;
    const isRegenerating = regeneratingIndex === index;
    const isAddingToLog = addingToNutrition[recipeId];

    return (
        <div
            key={recipeId}
            style={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
            }}
        >
          {/* Recipe Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
            <h3 style={{
              fontSize: '1.25rem',
              fontWeight: 'bold',
              color: '#111827',
              margin: 0,
              lineHeight: '1.6'
            }}>
              {recipe.recipe_name}
            </h3>
            <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
              {/* Action buttons */}
              <button
                  onClick={() => addToNutritionLog(recipe)}
                  disabled={isAddingToLog}
                  style={{
                    padding: '6px 12px',
                    backgroundColor: isAddingToLog ? '#9ca3af' : '#10b981',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    cursor: isAddingToLog ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
              >
                <Utensils size={12} />
                {isAddingToLog ? 'Adding...' : 'Add to Log'}
              </button>
            </div>
          </div>

          {/* Recipe Info */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '12px',
            marginBottom: '16px',
            padding: '12px',
            backgroundColor: '#f8fafc',
            borderRadius: '8px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Clock size={16} style={{ color: '#6b7280' }} />
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>
              {(parseInt(recipe.prep_time) || 0) + (parseInt(recipe.cook_time) || 0)} min
            </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <DollarSign size={16} style={{ color: '#6b7280' }} />
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>
              ${Number(recipe.cost_estimate || 0).toFixed(2)}
            </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Users size={16} style={{ color: '#6b7280' }} />
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>
              {recipe.servings || 4} servings
            </span>
            </div>
            {recipe.macros?.calories && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ fontSize: '0.875rem', color: '#374151' }}>
                {Math.round(recipe.macros.calories)} cal
              </span>
                </div>
            )}
          </div>

          {/* Ingredients */}
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>
              Ingredients:
            </h4>
            <ul style={{ paddingLeft: '20px', margin: 0 }}>
              {(recipe.ingredients || []).map((ing, idx) => (
                  <li key={idx} style={{ marginBottom: '4px', fontSize: '0.875rem', color: '#374151' }}>
                    {formatIngredient(ing)}
                  </li>
              ))}
            </ul>
          </div>

          {/* Directions */}
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '8px', color: '#111827' }}>
              Instructions:
            </h4>
            <ol style={{ paddingLeft: '20px', margin: 0 }}>
              {(recipe.directions || []).map((direction, idx) => (
                  <li key={idx} style={{ marginBottom: '8px', fontSize: '0.875rem', color: '#374151', lineHeight: '1.5' }}>
                    {direction}
                  </li>
              ))}
            </ol>
          </div>

          {/* Recipe Scaling Component */}
          {recipe.ingredients && recipe.ingredients.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <RecipeScaling recipe={recipe} />
              </div>
          )}

          {/* AI Insights */}
          {recipe.ai_insights && (
              <div style={{
                backgroundColor: '#f0f4ff',
                border: '1px solid #c7d2fe',
                borderRadius: '8px',
                padding: '12px',
                marginBottom: '16px'
              }}>
                <h4 style={{
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  color: '#3730a3',
                  marginBottom: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}>
                  <Brain size={14} />
                  AI Chef Notes:
                </h4>
                <p style={{ fontSize: '0.875rem', color: '#374151', margin: 0, lineHeight: '1.5' }}>
                  {recipe.ai_insights}
                </p>
              </div>
          )}

          {/* Tags */}
          {recipe.tags && recipe.tags.length > 0 && (
              <div style={{ marginBottom: '16px' }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {recipe.tags.map((tag, idx) => (
                      <span
                          key={idx}
                          style={{
                            padding: '2px 8px',
                            backgroundColor: '#dbeafe',
                            color: '#1e40af',
                            fontSize: '0.75rem',
                            borderRadius: '9999px'
                          }}
                      >
                  {tag}
                </span>
                  ))}
                </div>
              </div>
          )}

          {/* Rating System */}
          <RecipeRating
              recipeData={recipe}
              userId={userId}
              onRatingSubmit={(rating, feedback) => {
                console.log(`Recipe ${recipe.recipe_name} rated: ${rating} stars`, feedback);
                if (activeTab === 'recent') {
                  loadRecentRecipes();
                }
              }}
          />
        </div>
    );
  };

  // Main render
  return (
      <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
        <div style={{
          backgroundColor: 'white',
          borderRadius: '12px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden'
        }}>
          {/* Tab Navigation */}
          <div style={{
            borderBottom: '2px solid #f8fafc',
            marginBottom: '24px',
            display: 'flex'
          }}>
            <button
                onClick={() => setActiveTab('generate')}
                style={{
                  padding: '12px 24px',
                  border: 'none',
                  backgroundColor: activeTab === 'generate' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'generate' ? 'white' : '#6b7280',
                  borderRadius: '8px 8px 0 0',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
            >
              🍳 Generate Recipes
            </button>
            <button
                onClick={() => setActiveTab('recent')}
                style={{
                  padding: '12px 24px',
                  border: 'none',
                  backgroundColor: activeTab === 'recent' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'recent' ? 'white' : '#6b7280',
                  borderRadius: '8px 8px 0 0',
                  fontWeight: '600',
                  marginLeft: '4px',
                  cursor: 'pointer'
                }}
            >
              📊 Recent Recipes
            </button>
            <button
                onClick={() => setActiveTab('meal-plan')}
                style={{
                  padding: '12px 24px',
                  border: 'none',
                  backgroundColor: activeTab === 'meal-plan' ? '#3b82f6' : 'transparent',
                  color: activeTab === 'meal-plan' ? 'white' : '#6b7280',
                  borderRadius: '8px 8px 0 0',
                  fontWeight: '600',
                  marginLeft: '4px',
                  cursor: 'pointer'
                }}
            >
              📅 Meal Planning
            </button>
          </div>

          {/* Recipe Generation Tab */}
          {activeTab === 'generate' && (
              <div style={{ padding: '24px' }}>
                {/* Header */}
                <div style={{ marginBottom: '32px' }}>
                  <h1 style={{
                    fontSize: '2rem',
                    fontWeight: 'bold',
                    color: '#111827',
                    margin: 0,
                    display: 'flex',
                    alignItems: 'center'
                  }}>
                    <ChefHat size={32} style={{ marginRight: '12px', color: '#2563eb' }} />
                    Generate Recipes
                  </h1>
                  <p style={{ color: '#6b7280', marginTop: '8px' }}>
                    Create delicious recipes tailored to your budget and preferences.
                  </p>
                </div>

                {/* Input Form */}
                <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
                  <input
                      type="text"
                      placeholder="Enter recipe title or description"
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      style={{
                        flex: 1,
                        minWidth: '260px',
                        padding: '12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '8px',
                        fontSize: '1rem'
                      }}
                  />
                  <input
                      type="number"
                      placeholder="Budget ($)"
                      value={budget}
                      onChange={(e) => setBudget(e.target.value)}
                      style={{
                        width: '150px',
                        padding: '12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '8px',
                        fontSize: '1rem'
                      }}
                  />
                  {/* NEW: selector for number of recipes */}
                  <select
                      value={numRecipes}
                      onChange={(e) => setNumRecipes(Number(e.target.value))}
                      style={{
                        width: '150px',
                        padding: '12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '8px',
                        fontSize: '1rem',
                        background: 'white'
                      }}
                  >
                    <option value={1}>Generate 1</option>
                    <option value={3}>Generate 3</option>
                  </select>

                  <button
                      onClick={generateRecipes}
                      disabled={loading}
                      style={{
                        padding: '12px 24px',
                        backgroundColor: loading ? '#9ca3af' : '#3b82f6',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontWeight: '600'
                      }}
                  >
                    {loading ? 'Generating...' : 'Generate'}
                  </button>
                </div>

                {/* Error message */}
                {errorMsg && (
                    <div style={{
                      backgroundColor: '#fee2e2',
                      color: '#991b1b',
                      padding: '8px 12px',
                      borderRadius: '8px',
                      marginBottom: '16px'
                    }}>
                      {errorMsg}
                    </div>
                )}

                {/* Generated Recipes */}
                {recipeResults && recipeResults.length > 0 && (
                    <div style={{ display: 'grid', gap: '16px' }}>
                      {recipeResults.map((recipe, index) => renderRecipe(recipe, index))}
                    </div>
                )}
              </div>
          )}

          {/* Recent Recipes Tab */}
          {activeTab === 'recent' && (
              <div style={{ padding: '24px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '16px' }}>
                  Your Recent Recipes
                </h2>
                {recentRecipesLoading ? (
                    <p>Loading recent recipes...</p>
                ) : recentRecipes.length > 0 ? (
                    <div style={{ display: 'grid', gap: '16px' }}>
                      {recentRecipes.map((recipe, index) => renderRecipe(recipe, index))}
                    </div>
                ) : (
                    <p>No recent recipes found.</p>
                )}
              </div>
          )}

          {/* Meal Planning Tab */}
          {activeTab === 'meal-plan' && (
              <div style={{ padding: '24px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '16px' }}>
                  Meal Planning
                </h2>

                {/* Calendar Navigation */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                  <button onClick={() => navigateCalendar(-1)} style={{ padding: '6px 12px' }}>
                    ← Previous Week
                  </button>
                  <strong>Week of {weekDates[0].toLocaleDateString()}</strong>
                  <button onClick={() => navigateCalendar(1)} style={{ padding: '6px 12px' }}>
                    Next Week →
                  </button>
                </div>

                {/* Week Grid */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(7, 1fr)',
                  gap: '8px'
                }}>
                  {weekDates.map((date) => (
                      <div
                          key={date.toISOString()}
                          onDragOver={handleDragOver}
                          onDrop={(e) => handleDrop(e, date)}
                          style={{
                            backgroundColor: '#f9fafb',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '8px',
                            minHeight: '150px'
                          }}
                      >
                        <strong>{date.toLocaleDateString('en-US', { weekday: 'short' })}</strong>
                        <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {getMealsForDate(date).map((meal) => (
                              <div
                                  key={meal.id}
                                  style={{
                                    backgroundColor: 'white',
                                    border: '1px solid #d1d5db',
                                    borderRadius: '4px',
                                    padding: '4px',
                                    fontSize: '0.875rem',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                  }}
                              >
                                {meal.recipe_name}
                                <button
                                    onClick={() => removeMealFromDate(date, meal.id)}
                                    style={{
                                      background: 'none',
                                      border: 'none',
                                      color: '#ef4444',
                                      cursor: 'pointer'
                                    }}
                                >
                                  ✕
                                </button>
                              </div>
                          ))}
                        </div>
                      </div>
                  ))}
                </div>

                {/* Grocery List Button */}
                <div style={{ marginTop: '16px' }}>
                  <button
                      onClick={generateGroceryList}
                      disabled={mealPlanLoading}
                      style={{
                        padding: '10px 20px',
                        backgroundColor: mealPlanLoading ? '#9ca3af' : '#10b981',
                        color: 'white',
                        border: 'none',
                        borderRadius: '8px',
                        fontWeight: '600',
                        cursor: mealPlanLoading ? 'not-allowed' : 'pointer'
                      }}
                  >
                    {mealPlanLoading ? 'Generating...' : 'Generate Grocery List'}
                  </button>
                </div>

                {/* Available Recipes for Dragging */}
                <h3 style={{ marginTop: '24px', fontWeight: 'bold' }}>Available Recipes</h3>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
                  gap: '12px',
                  marginTop: '12px'
                }}>
                  {availableRecipes.map((recipe) => (
                      <div
                          key={recipe.id}
                          draggable
                          onDragStart={(e) => handleDragStart(e, recipe)}
                          style={{
                            backgroundColor: 'white',
                            border: '1px solid #d1d5db',
                            borderRadius: '8px',
                            padding: '8px',
                            cursor: 'grab'
                          }}
                      >
                        {recipe.recipe_name}
                      </div>
                  ))}
                </div>
              </div>
          )}
        </div>
      </div>
  );
}
