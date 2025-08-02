import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import RecipeRatings from '../components/RecipeRatings';
import RecipeScaling from '../components/RecipeScaling';
import { Utensils, CheckCircle, Calendar, ChefHat, DollarSign, Clock, Users, Brain, Sparkles, Share2 } from 'lucide-react';

export default function GenerateRecipe() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [activeTab, setActiveTab] = useState('generate');

  // Recipe Generation State
  const [title, setTitle] = useState('');
  const [budget, setBudget] = useState('');
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

  // Meal Planning State
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('week');
  const [plannedMeals, setPlannedMeals] = useState({});
  const [availableRecipes, setAvailableRecipes] = useState([]);
  const [showRecipePanel, setShowRecipePanel] = useState(true);
  const [draggedRecipe, setDraggedRecipe] = useState(null);
  const [mealPlanLoading, setMealPlanLoading] = useState(false);

  const [addingToNutrition, setAddingToNutrition] = useState({});

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

  // Load meal plans and available recipes when switching to meal planning tab
  useEffect(() => {
    if (activeTab === 'meal-plan' && userId) {
      loadMealPlans();
      loadAvailableRecipes();
    }
  }, [activeTab, userId]);

  // Optimized nutrition logging function
  const addRecipeToNutritionLog = useCallback(async (userId, recipeData) => {
    try {
      // Validate input data
      if (!userId || !recipeData) {
        throw new Error('Missing user ID or recipe data');
      }

      const response = await fetch('http://localhost:8000/quick-log-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          recipe_data: {
            ...recipeData,
            recipe_name: recipeData.recipe_name || recipeData.title || 'Unknown Recipe',
            timestamp: new Date().toISOString()
          }
        })
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Server error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      return { success: true, ...result };

    } catch (error) {
      console.error('Error logging recipe to nutrition:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }, []);

  // Enhanced recipe generation with advanced AI
  const handleGenerate = async (e) => {
    e?.preventDefault();
    setErrorMsg('');
    setRecipeResults(null);
    setAiExplanation('');
    setThoughtSteps([]);

    // Input validation
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

    // Show AI thinking animation for advanced mode
    if (useAdvancedAI) {
      setShowAIThinking(true);

      // Simulate thinking steps
      const steps = [
        { text: "Analyzing your dietary preferences and restrictions", icon: "🔍" },
        { text: "Optimizing recipes for your budget constraints", icon: "💰" },
        { text: "Selecting complementary ingredients for balanced nutrition", icon: "🥗" },
        { text: "Calculating macros and nutritional balance", icon: "📊" },
        { text: "Finalizing cooking instructions for best results", icon: "👨‍🍳" }
      ];

      // Show steps progressively
      for (let i = 0; i < steps.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 600));
        setThoughtSteps(prev => [...prev, { ...steps[i], completed: true }]);
      }
    }

    try {
      const payload = {
        title: title.trim(),
        budget: budgetNum,
        user_id: userId,
        use_advanced: useAdvancedAI  // Add advanced AI flag
      };

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), useAdvancedAI ? 45000 : 30000); // Longer timeout for advanced mode

      const res = await fetch('http://localhost:8000/generate-recipe-with-advanced-preferences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

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

      // Extract AI explanation if present (from advanced mode)
      if (data.ai_explanation) {
        setAiExplanation(data.ai_explanation);
      }

      // Validate and clean recipe data
      const cleanedRecipes = data.recipes.map((recipe, index) => ({
        ...recipe,
        id: recipe.id || `recipe_${Date.now()}_${index}`,
        recipe_name: recipe.recipe_name || recipe.title || `Recipe ${index + 1}`,
        ingredients: Array.isArray(recipe.ingredients) ? recipe.ingredients : [],
        directions: Array.isArray(recipe.directions) ? recipe.directions : [],
        macros: recipe.macros || {},
        tags: Array.isArray(recipe.tags) ? recipe.tags : [],
        ai_insights: recipe.ai_insights || null  // Advanced AI insights
      }));

      setRecipeResults(cleanedRecipes);

    } catch (err) {
      console.error('Recipe generation error:', err);
      if (err.name === 'AbortError') {
        setErrorMsg('Request timed out. Please try again or switch to quick mode.');
      } else {
        setErrorMsg(`Error: ${err.message}`);
      }
    } finally {
      setLoading(false);
      setShowAIThinking(false);
    }
  };

  // Enhanced regeneration with better state management
  const handleRegenerateRecipe = async (recipeIndex) => {
    if (!recipeResults || !userId || regeneratingIndex !== null) return;

    setRegeneratingIndex(recipeIndex);
    setErrorMsg('');

    try {
      const currentRecipes = recipeResults.map(r => r.recipe_name || r.title || 'Recipe');

      const payload = {
        title: title.trim(),
        budget: parseFloat(budget),
        user_id: userId,
        regenerate_single: true,
        exclude_recipes: currentRecipes,
        use_advanced: useAdvancedAI  // Use same AI mode
      };

      const res = await fetch('http://localhost:8000/generate-single-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to regenerate recipe');
      }

      const data = await res.json();

      if (data && data.recipe) {
        setRecipeResults(prevResults => {
          const newResults = [...prevResults];
          newResults[recipeIndex] = {
            ...data.recipe,
            id: data.recipe.id || `recipe_${Date.now()}_${recipeIndex}`,
            recipe_name: data.recipe.recipe_name || data.recipe.title || `Recipe ${recipeIndex + 1}`
          };
          return newResults;
        });
      } else {
        throw new Error('Invalid recipe data received');
      }

    } catch (err) {
      console.error('Recipe regeneration error:', err);
      setErrorMsg(`Error regenerating recipe: ${err.message}`);
    } finally {
      setRegeneratingIndex(null);
    }
  };

  // Enhanced nutrition logging with better UX
  const handleDoubleClickAddToNutrition = async (recipe, recipeIndex) => {
    if (!userId) {
      alert('Please sign in to track nutrition');
      return;
    }

    if (addingToNutrition[recipeIndex]) {
      return; // Prevent double clicks
    }

    setAddingToNutrition(prev => ({ ...prev, [recipeIndex]: true }));

    try {
      const result = await addRecipeToNutritionLog(userId, recipe);

      if (result.success) {
        // Enhanced success notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-6 py-3 rounded-lg shadow-lg z-50 flex items-center max-w-sm';
        notification.innerHTML = `
          <svg class="w-5 h-5 mr-3 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
          </svg>
          <div>
            <div class="font-semibold">Added to nutrition log!</div>
            <div class="text-sm opacity-90">${recipe.recipe_name || 'Recipe'}</div>
          </div>
        `;
        document.body.appendChild(notification);

        // Auto-remove notification after 4 seconds
        setTimeout(() => {
          if (notification.parentNode) {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => {
              if (notification.parentNode) {
                document.body.removeChild(notification);
              }
            }, 300);
          }
        }, 4000);
      } else {
        alert('Failed to add to nutrition log: ' + (result.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error adding to nutrition log:', error);
      alert('Error adding to nutrition log: ' + error.message);
    } finally {
      setAddingToNutrition(prev => ({ ...prev, [recipeIndex]: false }));
    }
  };

  // Enhanced grocery list saving
  const handleSaveToGroceryList = async () => {
    if (!recipeResults || !userId) return;

    setSavingToGroceryList(true);
    setErrorMsg('');

    try {
      const allGroceryItems = [];

      recipeResults.forEach((recipe, index) => {
        if (recipe.grocery_list && Array.isArray(recipe.grocery_list)) {
          recipe.grocery_list.forEach(item => {
            allGroceryItems.push({
              item_name: item.item || item.name || item.item_name || 'Unknown item',
              quantity: parseFloat(item.quantity) || 1,
              estimated_cost: parseFloat(item.estimated_cost) || parseFloat(item.cost) || 0,
              category: item.category || "Recipe Generated",
              source_recipe: recipe.recipe_name || `Recipe ${index + 1}`
            });
          });
        }
      });

      if (allGroceryItems.length === 0) {
        setErrorMsg('No grocery items found in recipes. Try regenerating recipes.');
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
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save grocery list');
      }

      const data = await res.json();

      const shouldNavigate = window.confirm(
          `Successfully added ${data.inserted_items || allGroceryItems.length} items to your grocery list!\n\nTotal estimated cost: $${allGroceryItems.reduce((sum, item) => sum + item.estimated_cost, 0).toFixed(2)}\n\nWould you like to view your grocery list now?`
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

  // Meal Planning Functions with better error handling
  const loadMealPlans = useCallback(async () => {
    if (!userId) return;

    try {
      const response = await fetch(`http://localhost:8000/meal-plans/${userId}`);
      if (response.ok) {
        const data = await response.json();
        setPlannedMeals(data.meal_plans || {});
      } else {
        console.error('Failed to load meal plans:', response.statusText);
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
        setAvailableRecipes(data.recipes || []);
      } else {
        console.error('Failed to load available recipes:', response.statusText);
      }
    } catch (error) {
      console.error('Error loading available recipes:', error);
    }
  }, [userId]);

  const saveMealPlan = useCallback(async (dateKey, meals) => {
    if (!userId) return;

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
        console.error('Failed to save meal plan:', response.statusText);
      }
    } catch (error) {
      console.error('Error saving meal plan:', error);
    }
  }, [userId]);

  // Calendar utility functions
  const getWeekDates = useCallback(() => {
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
  }, [currentDate]);

  const formatDate = useCallback((date) => {
    return date.toISOString().split('T')[0];
  }, []);

  const getMealsForDate = useCallback((date) => {
    const dateKey = formatDate(date);
    return plannedMeals[dateKey] || [];
  }, [plannedMeals, formatDate]);

  const addMealToDate = useCallback(async (date, meal, mealType = 'dinner') => {
    const dateKey = formatDate(date);
    const currentMeals = plannedMeals[dateKey] || [];
    const newMeal = {
      ...meal,
      mealType,
      id: `meal_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      added_at: new Date().toISOString()
    };
    const updatedMeals = [...currentMeals, newMeal];

    setPlannedMeals(prev => ({
      ...prev,
      [dateKey]: updatedMeals
    }));

    await saveMealPlan(dateKey, updatedMeals);
  }, [plannedMeals, formatDate, saveMealPlan]);

  const removeMealFromDate = useCallback(async (date, mealId) => {
    const dateKey = formatDate(date);
    const currentMeals = plannedMeals[dateKey] || [];
    const updatedMeals = currentMeals.filter(meal => meal.id !== mealId);

    setPlannedMeals(prev => ({
      ...prev,
      [dateKey]: updatedMeals
    }));

    await saveMealPlan(dateKey, updatedMeals);
  }, [plannedMeals, formatDate, saveMealPlan]);

  // Drag and drop handlers
  const handleDragStart = useCallback((e, recipe) => {
    setDraggedRecipe(recipe);
    e.dataTransfer.effectAllowed = 'copy';
    e.dataTransfer.setData('text/plain', recipe.id || recipe.recipe_name);
  }, []);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback((e, date) => {
    e.preventDefault();
    if (draggedRecipe) {
      addMealToDate(date, draggedRecipe);
      setDraggedRecipe(null);
    }
  }, [draggedRecipe, addMealToDate]);

  const generateGroceryListFromMealPlan = async () => {
    try {
      setMealPlanLoading(true);
      setErrorMsg('');

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
            `Successfully added ${data.items_added || 0} items to your grocery list!\n\nEstimated total cost: $${data.total_cost?.toFixed(2) || '0.00'}\n\nWould you like to view your grocery list now?`
        );

        if (shouldNavigate) {
          navigate('/grocery');
        }
      } else {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to generate grocery list');
      }
    } catch (error) {
      console.error('Error generating grocery list from meal plan:', error);
      setErrorMsg('Failed to generate grocery list from meal plan: ' + error.message);
    } finally {
      setMealPlanLoading(false);
    }
  };

  const navigateCalendar = useCallback((direction) => {
    const newDate = new Date(currentDate);
    if (viewMode === 'week') {
      newDate.setDate(currentDate.getDate() + (direction * 7));
    } else {
      newDate.setMonth(currentDate.getMonth() + direction);
    }
    setCurrentDate(newDate);
  }, [currentDate, viewMode]);

  // Enhanced UI Components
  const RecipeCard = ({ recipe, isDraggable = true }) => (
      <div
          className={`recipe-card ${isDraggable ? 'cursor-grab hover:shadow-md active:cursor-grabbing' : ''}`}
          style={{
            padding: '12px',
            margin: '8px 0',
            cursor: isDraggable ? 'grab' : 'default',
            transition: 'all 0.2s ease',
            border: '1px solid #e9ecef',
            borderRadius: '8px'
          }}
          draggable={isDraggable}
          onDragStart={(e) => isDraggable && handleDragStart(e, recipe)}
      >
        <div className="flex justify-between align-center mb-2">
          <h4 style={{
            fontSize: '0.875rem',
            fontWeight: '600',
            margin: 0,
            lineHeight: '1.2',
            color: '#333'
          }}>
            {recipe.recipe_name || recipe.title || 'Unknown Recipe'}
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
          <span>⏱️ {recipe.prep_time || recipe.prepTime || '30'}m</span>
          <span>💰 ${(recipe.cost_estimate || recipe.cost || 0).toFixed ? (recipe.cost_estimate || recipe.cost || 0).toFixed(2) : '0.00'}</span>
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
          {recipe.cuisine || 'Unknown'}
        </span>
          <span style={{ color: '#6c757d' }}>
          {recipe.macros?.calories || recipe.calories || 'N/A'} cal
        </span>
        </div>

        {recipe.tags?.slice(0, 2).map(tag => (
            <span key={tag} className="tag" style={{
              fontSize: '0.6rem',
              padding: '2px 6px',
              margin: '4px 2px 0 0',
              display: 'inline-block',
              backgroundColor: '#e3f2fd',
              color: '#1976d2',
              borderRadius: '4px'
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
              borderColor: isToday ? '#007bff' : '#e9ecef',
              transition: 'all 0.2s ease'
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
                    {meal.recipe_name || meal.name || 'Unknown Meal'}
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
                        opacity: 0,
                        transition: 'opacity 0.2s ease'
                      }}
                      onMouseEnter={(e) => e.target.style.opacity = 1}
                      onMouseLeave={(e) => e.target.style.opacity = 0}
                      title="Remove meal"
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

  // Enhanced recipe rendering with AI insights
  const renderRecipe = (rec, idx) => {
    const recipeName = rec.recipe_name || rec.title || `Recipe ${idx + 1}`;
    const ingredients = Array.isArray(rec.ingredients) ? rec.ingredients : [];
    const directions = Array.isArray(rec.directions) ? rec.directions : [];
    const macros = rec.macros || {};
    const tags = Array.isArray(rec.tags) ? rec.tags : [];

    return (
        <div
            key={rec.id || idx}
            className="mb-8 border border-gray-200 rounded-lg overflow-hidden shadow-sm cursor-pointer"
            onDoubleClick={() => handleDoubleClickAddToNutrition(rec, idx)}
            title="Double-click to add to nutrition log"
            style={{ transition: 'all 0.2s ease' }}
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
                    className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700 disabled:opacity-50 flex items-center transition-colors"
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
                    className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 transition-colors flex items-center"
                >
                  <Calendar className="w-4 h-4 mr-2" />
                  Add to Meal Plan
                </button>
                <button
                    onClick={() => handleRegenerateRecipe(idx)}
                    disabled={regeneratingIndex === idx || loading}
                    className="bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 disabled:opacity-50 transition-colors"
                >
                  {regeneratingIndex === idx ? 'Regenerating...' : 'Regenerate'}
                </button>
              </div>
            </div>

            {/* AI Insights Badge (if using advanced mode) */}
            {rec.ai_insights && (
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 mb-3 flex items-start">
                  <Brain className="w-5 h-5 text-purple-600 mr-3 flex-shrink-0 mt-1" />
                  <div className="text-sm text-purple-800">
                    <strong>AI Insights:</strong> {rec.ai_insights}
                  </div>
                </div>
            )}

            {/* Enhanced Nutrition Summary Card */}
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

          {/* Recipe Scaling Component */}
          <div className="border-b border-gray-200">
            <RecipeScaling
                recipe={{
                  name: recipeName,
                  original_servings: rec.servings || 4,
                  ingredients: ingredients,
                  cost_estimate: rec.cost_estimate,
                  macros: macros,
                  directions: directions,
                  cuisine: rec.cuisine,
                  tags: tags,
                  ...rec
                }}
                onRecipeUpdate={(scaledRecipe) => {
                  console.log('Recipe scaled:', scaledRecipe);
                  setRecipeResults(prevResults => {
                    const newResults = [...prevResults];
                    newResults[idx] = { ...newResults[idx], ...scaledRecipe };
                    return newResults;
                  });
                }}
            />
          </div>

          {/* Recipe Content */}
          <div className="p-4">
            {/* Ingredients */}
            {ingredients.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                    <ChefHat className="w-4 h-4 mr-2 text-blue-600" />
                    Ingredients ({ingredients.length})
                  </h4>
                  <ul className="space-y-2">
                    {ingredients.map((ing, i) => (
                        <li key={i} className="flex items-center text-gray-700 hover:bg-gray-50 p-2 rounded transition-colors">
                          <span className="w-2 h-2 bg-blue-500 rounded-full mr-3 flex-shrink-0"></span>
                          <span className="font-medium text-blue-600 mr-2 min-w-0 flex-shrink-0">
                        {ing.quantity || ''} {ing.unit || ''}
                      </span>
                          <span className="flex-1">{ing.name || 'Unknown ingredient'}</span>
                          {ing.cost_per_unit && (
                              <span className="text-sm text-green-600 ml-2">
                          ${(parseFloat(ing.cost_per_unit) || 0).toFixed(2)}
                        </span>
                          )}
                        </li>
                    ))}
                  </ul>
                </div>
            )}

            {/* Directions */}
            {directions.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-lg font-semibold text-gray-900 mb-3 flex items-center">
                    <Clock className="w-4 h-4 mr-2 text-green-600" />
                    Directions ({directions.length} steps)
                  </h4>
                  <ol className="space-y-3">
                    {directions.map((step, i) => (
                        <li key={i} className="flex text-gray-700 hover:bg-gray-50 p-3 rounded transition-colors">
                      <span className="flex-shrink-0 w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-semibold mr-3 mt-0.5">
                        {i + 1}
                      </span>
                          <span className="flex-1">{step}</span>
                        </li>
                    ))}
                  </ol>
                </div>
            )}

            {/* Tags */}
            {tags.length > 0 && (
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">Tags:</h4>
                  <div className="flex flex-wrap gap-2">
                    {tags.map(tag => (
                        <span key={tag} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                      {tag}
                    </span>
                    ))}
                  </div>
                </div>
            )}

            {/* Recipe Ratings component */}
            <RecipeRatings
                recipeData={rec}
                userId={userId}
                onRatingSubmit={(rating, feedback) => console.log(`Recipe rated ${rating} stars`, feedback)}
            />
          </div>
          <button
              onClick={() => navigate('/import-recipe')}
              className="btn-secondary w-full"
          >
            <Share2 className="w-4 h-4 mr-2" />
            Import from Social Media
          </button>
        </div>
    );
  };

  // Error message component
  const ErrorMessage = ({ message, onDismiss }) => (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4 flex items-center justify-between">
        <div className="flex items-center">
          <div className="w-5 h-5 text-red-500 mr-3">⚠️</div>
          <span className="text-red-800">{message}</span>
        </div>
        {onDismiss && (
            <button
                onClick={onDismiss}
                className="text-red-500 hover:text-red-700 ml-3"
            >
              ×
            </button>
        )}
      </div>
  );

  // Loading component
  const LoadingSpinner = ({ text = "Loading..." }) => (
      <div className="flex items-center justify-center py-8">
        <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mr-3"></div>
        <span className="text-gray-600">{text}</span>
      </div>
  );

  return (
      <div className="app-container">
        <div className="card-full">
          {/* Enhanced Tab Navigation */}
          <div className="tab-navigation" style={{ borderBottom: '2px solid #f8f9fa', marginBottom: '24px' }}>
            <button
                onClick={() => setActiveTab('generate')}
                className={`tab-button ${activeTab === 'generate' ? 'active' : ''}`}
                style={{
                  padding: '12px 24px',
                  border: 'none',
                  backgroundColor: activeTab === 'generate' ? '#007bff' : 'transparent',
                  color: activeTab === 'generate' ? 'white' : '#6c757d',
                  borderRadius: '8px 8px 0 0',
                  fontWeight: '600',
                  transition: 'all 0.2s ease'
                }}
            >
              🍳 Generate Recipes
            </button>
            <button
                onClick={() => setActiveTab('meal-plan')}
                className={`tab-button ${activeTab === 'meal-plan' ? 'active' : ''}`}
                style={{
                  padding: '12px 24px',
                  border: 'none',
                  backgroundColor: activeTab === 'meal-plan' ? '#007bff' : 'transparent',
                  color: activeTab === 'meal-plan' ? 'white' : '#6c757d',
                  borderRadius: '8px 8px 0 0',
                  fontWeight: '600',
                  transition: 'all 0.2s ease',
                  marginLeft: '4px'
                }}
            >
              📅 Meal Planning
            </button>
          </div>

          {/* Recipe Generation Tab */}
          {activeTab === 'generate' && (
              <div>
                {/* Enhanced Header */}
                <div className="nav-header">
                  <div>
                    <h1 style={{ textAlign: 'left', display: 'flex', alignItems: 'center' }}>
                      <ChefHat className="w-8 h-8 mr-3 text-blue-600" />
                      Generate Recipes
                    </h1>
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
                      ⚙️ Preferences
                    </button>
                    <button
                        onClick={() => navigate('/grocery')}
                        className="btn-success btn-sm"
                    >
                      🛒 View Grocery List
                    </button>
                  </div>
                </div>

                {/* Error Message */}
                {errorMsg && (
                    <ErrorMessage
                        message={errorMsg}
                        onDismiss={() => setErrorMsg('')}
                    />
                )}

                {/* AI Mode Toggle */}
                <div className="recipe-card mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold mb-2 flex items-center">
                        <Brain className="w-5 h-5 mr-2 text-purple-600" />
                        AI Generation Mode
                      </h3>
                      <p className="text-sm text-gray-600">
                        Advanced mode uses sophisticated reasoning for better results
                      </p>
                    </div>
                    <label className="flex items-center cursor-pointer">
                      <input
                          type="checkbox"
                          checked={useAdvancedAI}
                          onChange={(e) => setUseAdvancedAI(e.target.checked)}
                          className="sr-only"
                      />
                      <div className={`relative w-14 h-8 transition-colors rounded-full ${
                          useAdvancedAI ? 'bg-purple-600' : 'bg-gray-300'
                      }`}>
                        <div className={`absolute top-1 left-1 w-6 h-6 transition-transform bg-white rounded-full ${
                            useAdvancedAI ? 'translate-x-6' : ''
                        }`} />
                      </div>
                      <span className="ml-3 font-medium flex items-center">
                        {useAdvancedAI ? (
                            <>
                              <Sparkles className="w-4 h-4 mr-2 text-purple-600" />
                              Advanced AI
                            </>
                        ) : (
                            <>
                              ⚡ Quick Mode
                            </>
                        )}
                      </span>
                    </label>
                  </div>
                </div>

                {/* Enhanced Recipe Generation Form */}
                <div className="recipe-card mb-4">
                  <h2 className="mb-3" style={{ textAlign: 'left', display: 'flex', alignItems: 'center' }}>
                    <Users className="w-6 h-6 mr-2 text-green-600" />
                    Generate 3 Recipes
                  </h2>
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
                          placeholder="e.g., Quick Pasta Dishes, Healthy Breakfast Options, Budget-Friendly Dinners"
                          required
                          disabled={loading}
                          style={{ fontSize: '1rem' }}
                      />
                    </div>

                    <div className="form-group">
                      <label htmlFor="budget" style={{ display: 'flex', alignItems: 'center' }}>
                        <DollarSign className="w-4 h-4 mr-2 text-green-600" />
                        Budget (USD)
                      </label>
                      <input
                          id="budget"
                          type="number"
                          step="0.01"
                          min="0.01"
                          max="1000"
                          value={budget}
                          onChange={(e) => setBudget(e.target.value)}
                          placeholder="e.g. 20.00"
                          required
                          disabled={loading}
                          style={{ fontSize: '1rem' }}
                      />
                    </div>

                    <div className="flex gap-2">
                      <button
                          className="btn-primary"
                          type="submit"
                          disabled={loading || !userId}
                          style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                      >
                        {loading ? (
                            <>
                              <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                              Generating…
                            </>
                        ) : (
                            <>
                              <ChefHat className="w-4 h-4 mr-2" />
                              Generate Recipes
                            </>
                        )}
                      </button>

                      {recipeResults && recipeResults.length > 0 && (
                          <button
                              type="button"
                              onClick={handleSaveToGroceryList}
                              disabled={savingToGroceryList}
                              className="btn-success"
                              style={{
                                flex: 1,
                                backgroundColor: '#28a745',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center'
                              }}
                          >
                            {savingToGroceryList ? (
                                <>
                                  <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                                  Adding...
                                </>
                            ) : (
                                <>
                                  🛒 Generate Grocery List
                                </>
                            )}
                          </button>
                      )}
                    </div>
                  </form>
                </div>

                {/* AI Thinking Animation */}
                {loading && showAIThinking && (
                    <div className="recipe-card mb-4 bg-gradient-to-r from-purple-50 to-blue-50">
                      <div className="text-center py-8">
                        <div className="text-6xl mb-4 animate-pulse">🤔</div>
                        <h3 className="text-xl font-semibold mb-2">AI is thinking deeply...</h3>
                        <p className="text-gray-600 mb-4">
                          Analyzing your preferences and creating optimized recipes
                        </p>
                        <div className="space-y-2 text-left max-w-md mx-auto">
                          {thoughtSteps.map((step, i) => (
                              <div key={i} className={`flex items-center space-x-2 transition-all duration-500 ${
                                  step.completed ? 'text-green-600' : 'text-gray-400'
                              }`}>
                                <span className="text-xl">{step.icon}</span>
                                <span className={`${step.completed ? 'font-medium' : ''}`}>{step.text}</span>
                                {step.completed && <CheckCircle className="w-4 h-4" />}
                              </div>
                          ))}
                        </div>
                      </div>
                    </div>
                )}

                {/* Standard Loading State */}
                {loading && !showAIThinking && (
                    <div className="recipe-card">
                      <LoadingSpinner text="Generating your personalized recipes..." />
                    </div>
                )}

                {/* AI Explanation (if available) */}
                {aiExplanation && !loading && (
                    <div className="recipe-card mb-4 bg-gradient-to-r from-purple-50 to-blue-50">
                      <div className="flex items-start">
                        <Brain className="w-6 h-6 text-purple-600 mr-3 flex-shrink-0 mt-1" />
                        <div>
                          <h3 className="font-semibold text-purple-900 mb-2">AI Recipe Analysis</h3>
                          <p className="text-purple-800 text-sm">{aiExplanation}</p>
                        </div>
                      </div>
                    </div>
                )}

                {/* Generated Recipes */}
                {recipeResults && recipeResults.length > 0 && (
                    <div>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '24px'
                      }}>
                        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
                          <ChefHat className="w-6 h-6 mr-2 text-blue-600" />
                          Generated Recipes ({recipeResults.length})
                        </h2>
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

                {/* Enhanced Empty State */}
                {!recipeResults && !loading && (
                    <div style={{
                      textAlign: 'center',
                      padding: '60px 20px',
                      color: '#6c757d'
                    }}>
                      <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🍳</div>
                      <h3 style={{ marginBottom: '8px', color: '#333' }}>Ready to Cook Something Amazing?</h3>
                      <p style={{ marginBottom: '24px', maxWidth: '400px', margin: '0 auto 24px' }}>
                        Enter your meal preferences and budget above to generate personalized recipes tailored just for you!
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.875rem', padding: '8px 12px', backgroundColor: '#f8f9fa', borderRadius: '20px' }}>
                    🥗 Healthy Options
                  </span>
                        <span style={{ fontSize: '0.875rem', padding: '8px 12px', backgroundColor: '#f8f9fa', borderRadius: '20px' }}>
                    ⚡ Quick Meals
                  </span>
                        <span style={{ fontSize: '0.875rem', padding: '8px 12px', backgroundColor: '#f8f9fa', borderRadius: '20px' }}>
                    💰 Budget-Friendly
                  </span>
                      </div>
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
                      <h2 style={{ margin: 0, textAlign: 'left', display: 'flex', alignItems: 'center' }}>
                        <Calendar className="w-6 h-6 mr-2 text-blue-600" />
                        Smart Meal Planning
                      </h2>
                      <p style={{ color: '#6c757d', margin: '4px 0 0 0' }}>
                        Plan your weekly meals and generate grocery lists automatically
                      </p>
                    </div>

                    <div className="flex align-center gap-2">
                      <button
                          onClick={() => setShowRecipePanel(!showRecipePanel)}
                          className="btn-primary btn-sm"
                          style={{ display: 'flex', alignItems: 'center' }}
                      >
                        <ChefHat className="w-4 h-4 mr-2" />
                        {showRecipePanel ? 'Hide' : 'Show'} Recipes
                      </button>
                    </div>
                  </div>

                  {/* Enhanced Stats Bar */}
                  <div className="nutrition-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
                    <div className="nutrition-item" style={{ textAlign: 'center', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                  <span className="nutrition-value" style={{ color: '#007bff', fontSize: '1.5rem', fontWeight: 'bold', display: 'block' }}>
                    ${mealPlanStats.totalBudget.toFixed(2)}
                  </span>
                      <span className="nutrition-label" style={{ color: '#6c757d', fontSize: '0.875rem' }}>Weekly Budget</span>
                    </div>
                    <div className="nutrition-item" style={{ textAlign: 'center', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                  <span className="nutrition-value" style={{ color: '#28a745', fontSize: '1.5rem', fontWeight: 'bold', display: 'block' }}>
                    {Math.floor(mealPlanStats.totalPrepTime / 60)}h {mealPlanStats.totalPrepTime % 60}m
                  </span>
                      <span className="nutrition-label" style={{ color: '#6c757d', fontSize: '0.875rem' }}>Total Prep Time</span>
                    </div>
                    <div className="nutrition-item" style={{ textAlign: 'center', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                  <span className="nutrition-value" style={{ color: '#6f42c1', fontSize: '1.5rem', fontWeight: 'bold', display: 'block' }}>
                    {mealPlanStats.plannedDaysCount}
                  </span>
                      <span className="nutrition-label" style={{ color: '#6c757d', fontSize: '0.875rem' }}>Planned Days</span>
                    </div>
                    <div className="nutrition-item" style={{ textAlign: 'center', padding: '16px', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
                  <span className="nutrition-value" style={{ color: '#fd7e14', fontSize: '1.5rem', fontWeight: 'bold', display: 'block' }}>
                    {availableRecipes.length}
                  </span>
                      <span className="nutrition-label" style={{ color: '#6c757d', fontSize: '0.875rem' }}>Available Recipes</span>
                    </div>
                  </div>
                </div>

                <div className="flex gap-3">
                  {/* Enhanced Recipe Panel */}
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
                          <h3 style={{ margin: 0, fontSize: '1.125rem', display: 'flex', alignItems: 'center' }}>
                            <ChefHat className="w-4 h-4 mr-2 text-blue-600" />
                            Your Recipes
                          </h3>
                          <button
                              onClick={loadAvailableRecipes}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: '#6c757d',
                                cursor: 'pointer',
                                fontSize: '1rem',
                                padding: '4px',
                                borderRadius: '4px',
                                transition: 'all 0.2s ease'
                              }}
                              onMouseEnter={(e) => e.target.style.backgroundColor = '#f8f9fa'}
                              onMouseLeave={(e) => e.target.style.backgroundColor = 'transparent'}
                              title="Refresh recipes"
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
                                  <RecipeCard key={recipe.id || recipe.recipe_name} recipe={recipe} />
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
                            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          <ChefHat className="w-4 h-4 mr-2" />
                          Generate New Recipes
                        </button>
                      </div>
                  )}

                  {/* Enhanced Calendar */}
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
                              minHeight: 'auto',
                              transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.target.style.backgroundColor = '#e9ecef'}
                            onMouseLeave={(e) => e.target.style.backgroundColor = '#f8f9fa'}
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
                              minHeight: 'auto',
                              transition: 'all 0.2s ease'
                            }}
                            onMouseEnter={(e) => e.target.style.backgroundColor = '#e9ecef'}
                            onMouseLeave={(e) => e.target.style.backgroundColor = '#f8f9fa'}
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

                    {/* Enhanced Generate Grocery List Button */}
                    {mealPlanStats.plannedDaysCount > 0 && (
                        <div style={{ marginTop: '16px', textAlign: 'center' }}>
                          <button
                              onClick={generateGroceryListFromMealPlan}
                              disabled={mealPlanLoading}
                              className="btn-success"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '8px',
                                padding: '12px 24px',
                                fontSize: '1rem'
                              }}
                          >
                            {mealPlanLoading ? (
                                <>
                                  <div className="w-4 h-4 border border-white border-t-transparent rounded-full animate-spin"></div>
                                  Generating...
                                </>
                            ) : (
                                <>
                                  🛒 Generate Grocery List from Meal Plan
                                  <span style={{ fontSize: '0.875rem', opacity: 0.8 }}>
                            ({mealPlanStats.totalMealsCount} meals)
                          </span>
                                </>
                            )}
                          </button>
                        </div>
                    )}
                  </div>
                </div>

                {/* Enhanced Prep Time Optimization */}
                {mealPlanStats.plannedDaysCount > 0 && (
                    <div className="recipe-card mt-4">
                      <h3 className="mb-3" style={{ textAlign: 'left', display: 'flex', alignItems: 'center' }}>
                        <Clock className="w-5 h-5 mr-2 text-orange-600" />
                        Prep Time Optimization Tips
                      </h3>

                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                        gap: '16px'
                      }}>
                        <div style={{
                          backgroundColor: '#e3f2fd',
                          padding: '20px',
                          borderRadius: '12px',
                          border: '1px solid #2196f3'
                        }}>
                          <h4 style={{ color: '#1565c0', marginBottom: '8px', fontSize: '1rem', display: 'flex', alignItems: 'center' }}>
                            📅 Meal Prep Day
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
                          padding: '20px',
                          borderRadius: '12px',
                          border: '1px solid #4caf50'
                        }}>
                          <h4 style={{ color: '#2e7d32', marginBottom: '8px', fontSize: '1rem', display: 'flex', alignItems: 'center' }}>
                            🍲 Batch Cooking
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
                          padding: '20px',
                          borderRadius: '12px',
                          border: '1px solid #ffc107'
                        }}>
                          <h4 style={{ color: '#f57c00', marginBottom: '8px', fontSize: '1rem', display: 'flex', alignItems: 'center' }}>
                            🎯 Smart Scheduling
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

                {/* Enhanced Empty State for Meal Planning */}
                {mealPlanStats.plannedDaysCount === 0 && (
                    <div style={{
                      textAlign: 'center',
                      padding: '60px 20px',
                      color: '#6c757d'
                    }}>
                      <div style={{ fontSize: '4rem', marginBottom: '16px' }}>📅</div>
                      <h3 style={{ marginBottom: '8px', color: '#333' }}>Start Planning Your Weekly Meals</h3>
                      <p style={{ marginBottom: '24px', maxWidth: '500px', margin: '0 auto 24px' }}>
                        Drag recipes from the panel to calendar days, or generate new recipes to get started!
                        Plan your week ahead and save time on daily cooking decisions.
                      </p>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' }}>
                        {!showRecipePanel && (
                            <button
                                onClick={() => setShowRecipePanel(true)}
                                className="btn-primary"
                                style={{ width: 'auto', minWidth: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                            >
                              <ChefHat className="w-4 h-4 mr-2" />
                              Show Recipe Panel
                            </button>
                        )}
                        <button
                            onClick={() => setActiveTab('generate')}
                            className="btn-secondary"
                            style={{ width: 'auto', minWidth: '200px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >
                          <Users className="w-4 h-4 mr-2" />
                          Generate Recipes First
                        </button>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'center', gap: '16px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '0.875rem', padding: '8px 12px', backgroundColor: '#f8f9fa', borderRadius: '20px' }}>
                    📋 Weekly Planning
                  </span>
                        <span style={{ fontSize: '0.875rem', padding: '8px 12px', backgroundColor: '#f8f9fa', borderRadius: '20px' }}>
                    🛒 Auto Grocery Lists
                  </span>
                        <span style={{ fontSize: '0.875rem', padding: '8px 12px', backgroundColor: '#f8f9fa', borderRadius: '20px' }}>
                    ⏰ Time Optimization
                  </span>
                      </div>
                    </div>
                )}
              </div>
          )}
        </div>

        {/* Enhanced Global Notifications */}
        <style jsx>{`
        .notification-enter {
          transform: translateX(100%);
          opacity: 0;
        }
        .notification-enter-active {
          transform: translateX(0);
          opacity: 1;
          transition: all 0.3s ease;
        }
        .notification-exit {
          transform: translateX(0);
          opacity: 1;
        }
        .notification-exit-active {
          transform: translateX(100%);
          opacity: 0;
          transition: all 0.3s ease;
        }
        
        .recipe-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .tab-button:hover {
          background-color: #e9ecef !important;
        }
        
        .btn-primary:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 123, 255, 0.3);
        }
        
        .btn-secondary:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .btn-success:hover:not(:disabled) {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(40, 167, 69, 0.3);
        }
        
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .recipe-card {
          animation: fadeIn 0.3s ease-out;
        }
        
        @media (max-width: 768px) {
          .nav-header {
            flex-direction: column;
            gap: 16px;
          }
          
          .nav-buttons {
            flex-wrap: wrap;
            justify-content: center;
          }
          
          .nutrition-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
          
          .flex.gap-3 {
            flex-direction: column;
          }
          
          .recipe-card .flex.gap-2 {
            flex-direction: column;
          }
        }
        
        @media (max-width: 480px) {
          .nutrition-grid {
            grid-template-columns: 1fr !important;
          }
          
          .tab-navigation {
            flex-direction: column;
          }
          
          .tab-button {
            border-radius: 8px !important;
            margin-bottom: 4px;
          }
        }
      `}</style>
      </div>
  );
}