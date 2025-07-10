import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';

export default function HomePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [nutritionLoading, setNutritionLoading] = useState(false);
  const [addingToNutrition, setAddingToNutrition] = useState({});
  const [errors, setErrors] = useState({});

  const [stats, setStats] = useState({
    totalRecipes: 0,
    totalGroceryItems: 0,
    totalFavorites: 0,
    recentRecipes: [],
    nutritionData: {
      todayCalories: 0,
      todayProtein: 0,
      todayCarbs: 0,
      todayFat: 0,
      todayFiber: 0,
      todayCost: 0,
      todayEntries: 0,
      weeklyAvgCalories: 0,
      weeklyTotalCost: 0,
      goalProgress: {
        calories: 0,
        protein: 0,
        carbs: 0,
        fat: 0
      },
      favoriteCuisines: []
    }
  });

  // Daily nutrition goals
  const dailyGoals = {
    calories: 2000,
    protein: 150,
    carbs: 200,
    fat: 70,
    fiber: 25,
    budget: 30
  };

  useEffect(() => {
    const checkUserAndFetchData = async () => {
      try {
        const { data: { user }, error: userError } = await supabase.auth.getUser();

        if (userError || !user) {
          console.log('No authenticated user, redirecting to sign in');
          navigate('/');
          return;
        }

        setUser(user);
        await fetchUserStats(user.id);

      } catch (error) {
        console.error('Error checking user:', error);
        navigate('/');
      } finally {
        setLoading(false);
      }
    };

    checkUserAndFetchData();
  }, [navigate]);

  const fetchUserStats = async (userId) => {
    try {
      setNutritionLoading(true);
      setErrors({});

      // Fetch recent recipes from Supabase
      let recipes = [];
      try {
        const { data: recipesData, error: recipesError } = await supabase
            .from('recipes')
            .select('id, title, created_at, cuisine, macro_estimate, cost_estimate, ingredients, directions, tags')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(6);

        if (recipesError) {
          console.error('Error fetching recipes:', recipesError);
          setErrors(prev => ({ ...prev, recipes: 'Failed to load recipes' }));
        } else {
          recipes = recipesData || [];
        }
      } catch (error) {
        console.error('Error fetching recipes:', error);
        setErrors(prev => ({ ...prev, recipes: 'Failed to connect to database' }));
      }

      // Fetch grocery items count from Supabase
      let groceryItemsCount = 0;
      try {
        const { data: groceryItems, error: groceryError } = await supabase
            .from('grocery_items')
            .select('id, name, created_at, is_purchased')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(5);

        if (groceryError) {
          console.error('Error fetching grocery items:', groceryError);
          setErrors(prev => ({ ...prev, grocery: 'Failed to load grocery items' }));
        } else {
          groceryItemsCount = groceryItems?.filter(item => !item.is_purchased).length || 0;
        }
      } catch (error) {
        console.error('Error fetching grocery items:', error);
        setErrors(prev => ({ ...prev, grocery: 'Failed to connect to database' }));
      }

      // Initialize nutrition data with defaults
      let nutritionData = {
        todayCalories: 0,
        todayProtein: 0,
        todayCarbs: 0,
        todayFat: 0,
        todayFiber: 0,
        todayCost: 0,
        todayEntries: 0,
        weeklyAvgCalories: 0,
        weeklyTotalCost: 0,
        goalProgress: { calories: 0, protein: 0, carbs: 0, fat: 0 },
        favoriteCuisines: []
      };

      // Fetch nutrition data from backend with error handling
      try {
        // Fetch today's nutrition data
        const today = new Date().toISOString().split('T')[0];
        const todayResponse = await fetch(`http://localhost:8000/daily-nutrition?user_id=${userId}&date=${today}`);

        if (todayResponse.ok) {
          const todayData = await todayResponse.json();
          const todayTotals = calculateDayTotals(todayData.logs || []);

          nutritionData.todayCalories = todayTotals.calories;
          nutritionData.todayProtein = todayTotals.protein;
          nutritionData.todayCarbs = todayTotals.carbs;
          nutritionData.todayFat = todayTotals.fat;
          nutritionData.todayFiber = todayTotals.fiber;
          nutritionData.todayCost = todayTotals.cost;
          nutritionData.todayEntries = todayData.logs.length;
        } else {
          console.log(`Failed to fetch today's nutrition: ${todayResponse.status}`);
          setErrors(prev => ({ ...prev, todayNutrition: 'Failed to load today\'s nutrition data' }));
        }
      } catch (nutritionError) {
        console.log('Could not fetch today\'s nutrition data:', nutritionError);
        setErrors(prev => ({ ...prev, todayNutrition: 'Nutrition service unavailable' }));
      }

      try {
        // Fetch weekly nutrition summary
        const weeklyResponse = await fetch(`http://localhost:8000/weekly-nutrition-summary/${userId}?days=7`);

        if (weeklyResponse.ok) {
          const weeklyData = await weeklyResponse.json();
          const summary = weeklyData.weekly_summary;

          if (summary && summary.daily_averages) {
            nutritionData.weeklyAvgCalories = summary.daily_averages.calories || 0;
            nutritionData.weeklyTotalCost = (summary.daily_averages.cost || 0) * 7;
          }
        } else {
          console.log(`Failed to fetch weekly nutrition: ${weeklyResponse.status}`);
          setErrors(prev => ({ ...prev, weeklyNutrition: 'Failed to load weekly nutrition data' }));
        }
      } catch (nutritionError) {
        console.log('Could not fetch weekly nutrition data:', nutritionError);
        setErrors(prev => ({ ...prev, weeklyNutrition: 'Weekly nutrition service unavailable' }));
      }

      try {
        // Fetch nutrition summary for cuisines
        const summaryResponse = await fetch(`http://localhost:8000/nutrition-summary?user_id=${userId}`);

        if (summaryResponse.ok) {
          const summaryData = await summaryResponse.json();
          if (summaryData.summary && summaryData.summary.insights) {
            nutritionData.favoriteCuisines = summaryData.summary.insights.favorite_cuisines || [];
          }
        } else {
          console.log(`Failed to fetch nutrition summary: ${summaryResponse.status}`);
        }
      } catch (nutritionError) {
        console.log('Could not fetch nutrition summary:', nutritionError);
      }

      // Calculate goal progress
      nutritionData.goalProgress = {
        calories: Math.min((nutritionData.todayCalories / dailyGoals.calories) * 100, 100),
        protein: Math.min((nutritionData.todayProtein / dailyGoals.protein) * 100, 100),
        carbs: Math.min((nutritionData.todayCarbs / dailyGoals.carbs) * 100, 100),
        fat: Math.min((nutritionData.todayFat / dailyGoals.fat) * 100, 100)
      };

      // Fetch favorites count
      let favoritesCount = 0;
      try {
        const favoritesResponse = await fetch(`http://localhost:8000/favorites/${userId}?limit=5`);
        if (favoritesResponse.ok) {
          const favoritesData = await favoritesResponse.json();
          favoritesCount = favoritesData.total_count || 0;
        } else {
          console.log(`Failed to fetch favorites: ${favoritesResponse.status}`);
          setErrors(prev => ({ ...prev, favorites: 'Failed to load favorites' }));
        }
      } catch (favoritesError) {
        console.log('Could not fetch favorites:', favoritesError);
        setErrors(prev => ({ ...prev, favorites: 'Favorites service unavailable' }));
      }

      // Update stats
      setStats({
        totalRecipes: recipes.length,
        totalGroceryItems: groceryItemsCount,
        totalFavorites: favoritesCount,
        recentRecipes: recipes,
        nutritionData
      });

    } catch (error) {
      console.error('Error fetching stats:', error);
      setErrors(prev => ({ ...prev, general: 'Failed to load dashboard data' }));
    } finally {
      setNutritionLoading(false);
    }
  };

  const calculateDayTotals = (logs) => {
    const totals = {
      calories: 0,
      protein: 0,
      carbs: 0,
      fat: 0,
      fiber: 0,
      cost: 0
    };

    logs.forEach(log => {
      if (log.type === 'meal' && log.recipe_data) {
        const macros = log.recipe_data.macros || {};
        totals.calories += parseFloat(macros.calories) || 0;
        totals.protein += parseFloat(String(macros.protein).replace('g', '')) || 0;
        totals.carbs += parseFloat(String(macros.carbs).replace('g', '')) || 0;
        totals.fat += parseFloat(String(macros.fat).replace('g', '')) || 0;
        totals.fiber += parseFloat(String(macros.fiber).replace('g', '')) || 0;
        totals.cost += parseFloat(log.recipe_data.cost_estimate) || 0;
      } else if (log.type === 'custom') {
        totals.calories += log.calories || 0;
        totals.protein += log.protein || 0;
        totals.carbs += log.carbs || 0;
        totals.fat += log.fat || 0;
        totals.fiber += log.fiber || 0;
      }
    });

    return totals;
  };

  const addRecipeToNutritionLog = async (recipe, recipeIndex) => {
    if (!user) {
      alert('Please sign in to track nutrition');
      return;
    }

    setAddingToNutrition(prev => ({ ...prev, [recipeIndex]: true }));

    try {
      const recipeData = {
        recipe_name: recipe.title || `Recipe ${recipeIndex + 1}`,
        macros: recipe.macro_estimate || {
          calories: 450,
          protein: '25g',
          carbs: '35g',
          fat: '15g',
          fiber: '5g'
        },
        cost_estimate: recipe.cost_estimate || 8.50,
        cuisine: recipe.cuisine || 'Unknown',
        ingredients: recipe.ingredients || [],
        directions: recipe.directions || []
      };

      const result = await fetch('http://localhost:8000/quick-log-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          recipe_data: recipeData
        })
      });

      if (result.ok) {
        // Show success notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center';
        notification.innerHTML = `
          <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
          </svg>
          Added "${recipeData.recipe_name}" to nutrition log!
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
          if (document.body.contains(notification)) {
            document.body.removeChild(notification);
          }
        }, 3000);

        // Refresh nutrition data
        await fetchUserStats(user.id);
      } else {
        const errorData = await result.json().catch(() => ({}));
        alert(`Failed to add to nutrition log: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error adding to nutrition log:', error);
      alert('Error adding to nutrition log. Please check your connection.');
    } finally {
      setAddingToNutrition(prev => ({ ...prev, [recipeIndex]: false }));
    }
  };

  const handleSignOut = async () => {
    try {
      await supabase.auth.signOut();
      navigate('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  // Progress Circle Component
  const ProgressCircle = ({ percentage, color, size = 80, strokeWidth = 6 }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDasharray = circumference;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    return (
        <div style={{ position: 'relative', width: size, height: size }}>
          <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                stroke="#e9ecef"
                strokeWidth={strokeWidth}
                fill="transparent"
            />
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                stroke={color}
                strokeWidth={strokeWidth}
                fill="transparent"
                strokeDasharray={strokeDasharray}
                strokeDashoffset={strokeDashoffset}
                style={{
                  transition: 'stroke-dashoffset 0.8s ease-in-out',
                  strokeLinecap: 'round'
                }}
            />
          </svg>
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '14px',
            fontWeight: '700',
            color: color
          }}>
            {Math.round(percentage)}%
          </div>
        </div>
    );
  };

  if (loading) {
    return (
        <div className="app-container">
          <div className="card">
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                border: '4px solid #e9ecef',
                borderTop: '4px solid #007bff',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                margin: '0 auto 16px'
              }}></div>
              <p>Loading your dashboard...</p>
            </div>
          </div>
        </div>
    );
  }

  return (
      <div className="app-container">
        <div className="card-full">
          {/* Header */}
          <div className="nav-header">
            <div>
              <h1 style={{ textAlign: 'left', marginBottom: '8px' }}>🏠 Dashboard</h1>
              <p className="subtitle" style={{ textAlign: 'left', marginBottom: 0 }}>
                Welcome back! Here's your nutrition and meal planning overview.
              </p>
            </div>
            <button onClick={handleSignOut} className="btn-danger btn-sm">
              Sign Out
            </button>
          </div>

          {/* Error Messages */}
          {Object.keys(errors).length > 0 && (
              <div className="recipe-card mb-4" style={{ backgroundColor: '#fff3cd', borderColor: '#ffeaa7' }}>
                <h3 style={{ color: '#856404', marginBottom: '12px' }}>⚠️ Some data couldn't be loaded</h3>
                <div style={{ fontSize: '0.875rem', color: '#856404' }}>
                  {Object.entries(errors).map(([key, message]) => (
                      <div key={key} style={{ marginBottom: '4px' }}>
                        • {message}
                      </div>
                  ))}
                  <div style={{ marginTop: '8px', fontStyle: 'italic' }}>
                    Don't worry - you can still use all features. Try refreshing the page if issues persist.
                  </div>
                </div>
              </div>
          )}

          {/* Today's Nutrition Overview */}
          <div className="recipe-card mb-4">
            <div className="flex justify-between align-center mb-3">
              <h2 style={{ margin: 0, textAlign: 'left' }}>📊 Today's Nutrition</h2>
              {nutritionLoading && (
                  <div style={{ fontSize: '0.875rem', color: '#6c757d', display: 'flex', alignItems: 'center' }}>
                    <div style={{
                      width: '16px',
                      height: '16px',
                      border: '2px solid #e9ecef',
                      borderTop: '2px solid #007bff',
                      borderRadius: '50%',
                      animation: 'spin 1s linear infinite',
                      marginRight: '8px'
                    }}></div>
                    Loading...
                  </div>
              )}
            </div>

            {/* Today's Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '16px',
              marginBottom: '32px'
            }}>
              <div style={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                padding: '24px',
                borderRadius: '16px',
                color: 'white',
                textAlign: 'center',
                boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)'
              }}>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '8px' }}>
                  {Math.round(stats.nutritionData.todayCalories)}
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '4px' }}>
                  Calories Today
                </div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                  Goal: {dailyGoals.calories} ({Math.round(stats.nutritionData.goalProgress.calories)}%)
                </div>
              </div>

              <div style={{
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                padding: '24px',
                borderRadius: '16px',
                color: 'white',
                textAlign: 'center',
                boxShadow: '0 8px 32px rgba(240, 147, 251, 0.3)'
              }}>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '8px' }}>
                  {Math.round(stats.nutritionData.todayProtein)}g
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '4px' }}>
                  Protein Today
                </div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                  Goal: {dailyGoals.protein}g ({Math.round(stats.nutritionData.goalProgress.protein)}%)
                </div>
              </div>

              <div style={{
                background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                padding: '24px',
                borderRadius: '16px',
                color: 'white',
                textAlign: 'center',
                boxShadow: '0 8px 32px rgba(79, 172, 254, 0.3)'
              }}>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '8px' }}>
                  ${stats.nutritionData.todayCost.toFixed(2)}
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '4px' }}>
                  Cost Today
                </div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                  Budget: ${dailyGoals.budget} ({Math.round((stats.nutritionData.todayCost / dailyGoals.budget) * 100)}%)
                </div>
              </div>

              <div style={{
                background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                padding: '24px',
                borderRadius: '16px',
                color: 'white',
                textAlign: 'center',
                boxShadow: '0 8px 32px rgba(250, 112, 154, 0.3)'
              }}>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', marginBottom: '8px' }}>
                  {stats.nutritionData.todayEntries}
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '4px' }}>
                  Entries Logged
                </div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>
                  Keep tracking!
                </div>
              </div>
            </div>

            {/* Macro Progress Circles */}
            <div>
              <h3 style={{ marginBottom: '20px', textAlign: 'left', color: '#333' }}>Daily Goal Progress</h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                gap: '24px',
                justifyItems: 'center'
              }}>
                <div style={{ textAlign: 'center' }}>
                  <ProgressCircle
                      percentage={stats.nutritionData.goalProgress.calories}
                      color="#667eea"
                      size={100}
                  />
                  <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: '600', color: '#333' }}>
                    Calories
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {Math.round(stats.nutritionData.todayCalories)} / {dailyGoals.calories}
                  </div>
                </div>

                <div style={{ textAlign: 'center' }}>
                  <ProgressCircle
                      percentage={stats.nutritionData.goalProgress.protein}
                      color="#f5576c"
                      size={100}
                  />
                  <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: '600', color: '#333' }}>
                    Protein
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {Math.round(stats.nutritionData.todayProtein)}g / {dailyGoals.protein}g
                  </div>
                </div>

                <div style={{ textAlign: 'center' }}>
                  <ProgressCircle
                      percentage={stats.nutritionData.goalProgress.carbs}
                      color="#00f2fe"
                      size={100}
                  />
                  <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: '600', color: '#333' }}>
                    Carbs
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {Math.round(stats.nutritionData.todayCarbs)}g / {dailyGoals.carbs}g
                  </div>
                </div>

                <div style={{ textAlign: 'center' }}>
                  <ProgressCircle
                      percentage={stats.nutritionData.goalProgress.fat}
                      color="#fee140"
                      size={100}
                  />
                  <div style={{ marginTop: '12px', fontSize: '14px', fontWeight: '600', color: '#333' }}>
                    Fat
                  </div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {Math.round(stats.nutritionData.todayFat)}g / {dailyGoals.fat}g
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Weekly Insights */}
          <div className="recipe-card mb-4">
            <h3 style={{ margin: '0 0 20px 0', textAlign: 'left' }}>📈 Weekly Insights</h3>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '16px'
            }}>
              <div style={{
                background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
                padding: '20px',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.2)',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#2d3748', marginBottom: '8px' }}>
                  {Math.round(stats.nutritionData.weeklyAvgCalories)}
                </div>
                <div style={{ fontSize: '0.9rem', color: '#4a5568', fontWeight: '600' }}>
                  Avg Daily Calories
                </div>
                <div style={{ fontSize: '0.75rem', color: '#718096', marginTop: '4px' }}>
                  Based on 7-day average
                </div>
              </div>

              <div style={{
                background: 'linear-gradient(135deg, #d299c2 0%, #fef9d7 100%)',
                padding: '20px',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.2)',
                textAlign: 'center'
              }}>
                <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#2d3748', marginBottom: '8px' }}>
                  ${stats.nutritionData.weeklyTotalCost.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.9rem', color: '#4a5568', fontWeight: '600' }}>
                  Weekly Food Cost
                </div>
                <div style={{ fontSize: '0.75rem', color: '#718096', marginTop: '4px' }}>
                  Budget: ${(dailyGoals.budget * 7).toFixed(2)}
                </div>
              </div>

              {stats.nutritionData.favoriteCuisines.length > 0 && (
                  <div style={{
                    background: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
                    padding: '20px',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.2)',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontSize: '1.8rem', fontWeight: '700', color: '#2d3748', marginBottom: '8px' }}>
                      {stats.nutritionData.favoriteCuisines[0]?.cuisine || 'None'}
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#4a5568', fontWeight: '600' }}>
                      Favorite Cuisine
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#718096', marginTop: '4px' }}>
                      {stats.nutritionData.favoriteCuisines[0]?.count || 0} meals logged
                    </div>
                  </div>
              )}
            </div>
          </div>

          {/* Recent Recipes */}
          <div className="recipe-card mb-4">
            <div className="flex justify-between align-center mb-3">
              <h3 style={{ margin: 0, textAlign: 'left' }}>🍳 Recent Recipes</h3>
              <button
                  onClick={() => navigate('/generate')}
                  className="btn-primary btn-sm"
              >
                Generate More
              </button>
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '20px'
            }}>
              {stats.recentRecipes.length > 0 ? (
                  stats.recentRecipes.slice(0, 4).map((recipe, index) => {
                    const isAddingNutrition = addingToNutrition[index] || false;
                    const macros = recipe.macro_estimate || {};

                    return (
                        <div key={recipe.id} style={{
                          background: 'linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%)',
                          padding: '24px',
                          borderRadius: '16px',
                          border: '2px solid #e9ecef',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease',
                          position: 'relative',
                          boxShadow: '0 4px 16px rgba(0,0,0,0.1)'
                        }}
                             onMouseEnter={(e) => {
                               e.currentTarget.style.borderColor = '#007bff';
                               e.currentTarget.style.transform = 'translateY(-4px)';
                               e.currentTarget.style.boxShadow = '0 8px 32px rgba(0,123,255,0.2)';
                             }}
                             onMouseLeave={(e) => {
                               e.currentTarget.style.borderColor = '#e9ecef';
                               e.currentTarget.style.transform = 'translateY(0)';
                               e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.1)';
                             }}>

                          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
                            <div style={{ fontSize: '3rem', marginBottom: '12px' }}>
                              {index === 0 ? '🍗' : index === 1 ? '🍤' : index === 2 ? '🥗' : '🍝'}
                            </div>

                            <h4 style={{
                              fontSize: '1.1rem',
                              fontWeight: '700',
                              color: '#1a1a1a',
                              marginBottom: '6px',
                              lineHeight: '1.3'
                            }}>
                              {recipe.title || `Recipe ${index + 1}`}
                            </h4>

                            <p style={{
                              fontSize: '0.9rem',
                              color: '#6c757d',
                              margin: '0 0 12px 0',
                              fontWeight: '500'
                            }}>
                              {recipe.cuisine || 'Unknown Cuisine'}
                            </p>
                          </div>

                          {/* Nutrition Preview */}
                          {macros && Object.keys(macros).length > 0 && (
                              <div style={{
                                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)',
                                padding: '16px',
                                borderRadius: '12px',
                                marginBottom: '16px',
                                border: '1px solid #dee2e6'
                              }}>
                                <div style={{
                                  fontSize: '0.8rem',
                                  fontWeight: '700',
                                  color: '#495057',
                                  marginBottom: '10px',
                                  textAlign: 'center'
                                }}>
                                  Nutrition Info
                                </div>
                                <div style={{
                                  display: 'grid',
                                  gridTemplateColumns: 'repeat(2, 1fr)',
                                  gap: '8px',
                                  fontSize: '0.75rem',
                                  color: '#6c757d',
                                  textAlign: 'center'
                                }}>
                                  <div style={{ fontWeight: '600' }}>
                                    <strong style={{ color: '#667eea' }}>{macros.calories || 450}</strong> cal
                                  </div>
                                  <div style={{ fontWeight: '600' }}>
                                    <strong style={{ color: '#f5576c' }}>{String(macros.protein || '25g').replace('g', '')}g</strong> protein
                                  </div>
                                  <div style={{ fontWeight: '600' }}>
                                    <strong style={{ color: '#00f2fe' }}>{String(macros.carbs || '35g').replace('g', '')}g</strong> carbs
                                  </div>
                                  <div style={{ fontWeight: '600' }}>
                                    <strong style={{ color: '#fee140' }}>{String(macros.fat || '15g').replace('g', '')}g</strong> fat
                                  </div>
                                </div>
                              </div>
                          )}

                          {/* Action Buttons */}
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {/* Nutrition Log Button */}
                            <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  addRecipeToNutritionLog(recipe, index);
                                }}
                                disabled={isAddingNutrition}
                                style={{
                                  width: '100%',
                                  padding: '12px 16px',
                                  background: isAddingNutrition
                                      ? 'linear-gradient(135deg, #6c757d 0%, #495057 100%)'
                                      : 'linear-gradient(135deg, #28a745 0%, #20c997 100%)',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '8px',
                                  fontSize: '0.85rem',
                                  cursor: isAddingNutrition ? 'not-allowed' : 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  gap: '8px',
                                  fontWeight: '600',
                                  transition: 'all 0.3s ease',
                                  boxShadow: '0 4px 12px rgba(40, 167, 69, 0.3)'
                                }}
                            >
                              {isAddingNutrition ? (
                                  <>
                                    <div style={{
                                      width: '16px',
                                      height: '16px',
                                      border: '2px solid white',
                                      borderTop: '2px solid transparent',
                                      borderRadius: '50%',
                                      animation: 'spin 1s linear infinite'
                                    }}></div>
                                    Adding...
                                  </>
                              ) : (
                                  <>
                                    <span>🍎</span>
                                    Log to Nutrition
                                  </>
                              )}
                            </button>

                            {/* View Recipe Button */}
                            <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  navigate('/generate');
                                }}
                                style={{
                                  width: '100%',
                                  padding: '10px 16px',
                                  background: 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)',
                                  color: 'white',
                                  border: 'none',
                                  borderRadius: '8px',
                                  fontSize: '0.8rem',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  gap: '6px',
                                  fontWeight: '600',
                                  transition: 'all 0.3s ease',
                                  boxShadow: '0 4px 12px rgba(0, 123, 255, 0.3)'
                                }}
                            >
                              <span>👁️</span>
                              View Details
                            </button>
                          </div>

                          {/* Date added */}
                          <div style={{
                            marginTop: '12px',
                            fontSize: '0.7rem',
                            color: '#9ca3af',
                            textAlign: 'center',
                            fontStyle: 'italic'
                          }}>
                            Added {new Date(recipe.created_at).toLocaleDateString()}
                          </div>
                        </div>
                    );
                  })
              ) : (
                  <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '60px 20px' }}>
                    <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🍳</div>
                    <h3 style={{ color: '#6c757d', marginBottom: '12px', fontSize: '1.3rem' }}>No recipes yet</h3>
                    <p style={{ color: '#9ca3af', marginBottom: '24px' }}>
                      Generate your first recipe to start tracking nutrition and building your meal plan!
                    </p>
                    <button
                        onClick={() => navigate('/generate')}
                        style={{
                          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                          color: 'white',
                          border: 'none',
                          padding: '16px 32px',
                          borderRadius: '12px',
                          fontSize: '1rem',
                          fontWeight: '600',
                          cursor: 'pointer',
                          boxShadow: '0 8px 24px rgba(102, 126, 234, 0.3)',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-2px)';
                          e.currentTarget.style.boxShadow = '0 12px 32px rgba(102, 126, 234, 0.4)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = '0 8px 24px rgba(102, 126, 234, 0.3)';
                        }}
                    >
                      Generate Your First Recipe
                    </button>
                  </div>
              )}
            </div>
          </div>

          {/* Quick Action Navigation Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '20px',
            marginTop: '32px'
          }}>
            {/* Generate Recipes */}
            <div
                onClick={() => navigate('/generate')}
                style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  padding: '32px 24px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  textAlign: 'center',
                  color: 'white',
                  boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)',
                  border: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 16px 48px rgba(102, 126, 234, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = '0 8px 32px rgba(102, 126, 234, 0.3)';
                }}
            >
              <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>🍳</div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.3rem', fontWeight: '700' }}>
                Generate Recipes
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.9, lineHeight: '1.4' }}>
                Create personalized recipes based on your preferences and budget
              </p>
            </div>

            {/* Nutrition Tracker */}
            <div
                onClick={() => navigate('/nutrition')}
                style={{
                  background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
                  padding: '32px 24px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  textAlign: 'center',
                  color: 'white',
                  boxShadow: '0 8px 32px rgba(79, 172, 254, 0.3)',
                  border: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 16px 48px rgba(79, 172, 254, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = '0 8px 32px rgba(79, 172, 254, 0.3)';
                }}
            >
              <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>🍎</div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.3rem', fontWeight: '700' }}>
                Nutrition Tracker
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.9, lineHeight: '1.4' }}>
                Track calories, macros, and costs from your logged meals
              </p>
            </div>

            {/* Grocery List */}
            <div
                onClick={() => navigate('/grocery')}
                style={{
                  background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
                  padding: '32px 24px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  textAlign: 'center',
                  color: 'white',
                  boxShadow: '0 8px 32px rgba(250, 112, 154, 0.3)',
                  border: 'none',
                  position: 'relative'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 16px 48px rgba(250, 112, 154, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = '0 8px 32px rgba(250, 112, 154, 0.3)';
                }}
            >
              <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>🛒</div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.3rem', fontWeight: '700' }}>
                Grocery List
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.9, lineHeight: '1.4' }}>
                Manage shopping lists from your generated recipes
              </p>
              {stats.totalGroceryItems > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '16px',
                    right: '16px',
                    backgroundColor: 'rgba(255,255,255,0.3)',
                    color: 'white',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '0.8rem',
                    fontWeight: '700',
                    border: '2px solid rgba(255,255,255,0.5)'
                  }}>
                    {stats.totalGroceryItems} items
                  </div>
              )}
            </div>

            {/* Favorites */}
            <div
                onClick={() => navigate('/favorites')}
                style={{
                  background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                  padding: '32px 24px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  textAlign: 'center',
                  color: 'white',
                  boxShadow: '0 8px 32px rgba(240, 147, 251, 0.3)',
                  border: 'none',
                  position: 'relative'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 16px 48px rgba(240, 147, 251, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = '0 8px 32px rgba(240, 147, 251, 0.3)';
                }}
            >
              <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>❤️</div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.3rem', fontWeight: '700' }}>
                Favorites
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.9, lineHeight: '1.4' }}>
                Access your saved favorite recipes and collections
              </p>
              {stats.totalFavorites > 0 && (
                  <div style={{
                    position: 'absolute',
                    top: '16px',
                    right: '16px',
                    backgroundColor: 'rgba(255,255,255,0.3)',
                    color: 'white',
                    padding: '6px 12px',
                    borderRadius: '20px',
                    fontSize: '0.8rem',
                    fontWeight: '700',
                    border: '2px solid rgba(255,255,255,0.5)'
                  }}>
                    {stats.totalFavorites} saved
                  </div>
              )}
            </div>

            {/* Preferences */}
            <div
                onClick={() => navigate('/preferences')}
                style={{
                  background: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
                  padding: '32px 24px',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  textAlign: 'center',
                  color: '#2d3748',
                  boxShadow: '0 8px 32px rgba(168, 237, 234, 0.3)',
                  border: 'none'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-8px) scale(1.02)';
                  e.currentTarget.style.boxShadow = '0 16px 48px rgba(168, 237, 234, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'translateY(0) scale(1)';
                  e.currentTarget.style.boxShadow = '0 8px 32px rgba(168, 237, 234, 0.3)';
                }}
            >
              <div style={{ fontSize: '3.5rem', marginBottom: '16px' }}>⚙️</div>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '1.3rem', fontWeight: '700' }}>
                Preferences
              </h3>
              <p style={{ margin: 0, fontSize: '0.9rem', opacity: 0.8, lineHeight: '1.4' }}>
                Set dietary restrictions, budget, and cooking preferences
              </p>
            </div>
          </div>

          {/* Add CSS for animations */}
          <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
        </div>
      </div>
  );
}