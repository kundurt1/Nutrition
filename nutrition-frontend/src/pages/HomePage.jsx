// src/pages/HomePage.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';

export default function HomePage() {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalRecipes: 0,
    totalGroceryItems: 0,
    totalFavorites: 0,
    recentActivity: [],
    recentFavorites: [],
    nutritionInsights: {
      totalCaloriesToday: 0,
      totalCaloriesWeek: 0,
      avgCaloriesPerDay: 0,
      favoriteCuisines: [],
      favoriteMeals: [],
      nutritionBreakdown: {
        protein: 0,
        carbs: 0,
        fat: 0,
        fiber: 0
      }
    }
  });

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
      // Fetch recipe count
      const { data: recipes, error: recipesError } = await supabase
        .from('recipes')
        .select('id, title, created_at, cuisine, macro_estimate')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(10);

      // Fetch grocery items count
      const { data: groceryItems, error: groceryError } = await supabase
        .from('grocery_items')
        .select('id, name, created_at, is_purchased')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .limit(5);

      // Fetch meal logs for nutrition insights
      const { data: mealLogs, error: mealError } = await supabase
        .from('meal_logs')
        .select('id, recipe_id, date, created_at, recipes!inner(title, cuisine, macro_estimate)')
        .eq('user_id', userId)
        .order('date', { ascending: false })
        .limit(30);

      // Fetch favorites count and recent favorites
      let favoritesCount = 0;
      let recentFavorites = [];
      
      try {
        const favoritesResponse = await fetch(`http://localhost:8000/favorites/${userId}?limit=5`);
        if (favoritesResponse.ok) {
          const favoritesData = await favoritesResponse.json();
          favoritesCount = favoritesData.total_count || 0;
          recentFavorites = favoritesData.favorites || [];
        }
      } catch (favoritesError) {
        console.log('Could not fetch favorites (this is OK if backend is not running):', favoritesError);
      }

      // Calculate nutrition insights
      const nutritionInsights = calculateNutritionInsights(mealLogs || [], recipes || []);

      setStats({
        totalRecipes: recipes?.length || 0,
        totalGroceryItems: groceryItems?.filter(item => !item.is_purchased).length || 0,
        totalFavorites: favoritesCount,
        recentRecipes: recipes || [],
        recentGroceryItems: groceryItems || [],
        recentFavorites: recentFavorites,
        nutritionInsights
      });

    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const calculateNutritionInsights = (mealLogs, allRecipes) => {
    const today = new Date().toISOString().split('T')[0];
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    const weekAgoStr = weekAgo.toISOString().split('T')[0];

    // Calculate calories for today and this week
    const todayMeals = mealLogs.filter(meal => meal.date === today);
    const weekMeals = mealLogs.filter(meal => meal.date >= weekAgoStr);

    const totalCaloriesToday = todayMeals.reduce((sum, meal) => {
      const calories = meal.recipes?.macro_estimate?.calories || 0;
      return sum + calories;
    }, 0);

    const totalCaloriesWeek = weekMeals.reduce((sum, meal) => {
      const calories = meal.recipes?.macro_estimate?.calories || 0;
      return sum + calories;
    }, 0);

    const avgCaloriesPerDay = weekMeals.length > 0 ? Math.round(totalCaloriesWeek / 7) : 0;

    // Calculate nutrition breakdown for the week
    const nutritionBreakdown = weekMeals.reduce((acc, meal) => {
      const macros = meal.recipes?.macro_estimate || {};
      acc.protein += parseFloat(macros.protein) || 0;
      acc.carbs += parseFloat(macros.carbs) || 0;
      acc.fat += parseFloat(macros.fat) || 0;
      acc.fiber += parseFloat(macros.fiber) || 0;
      return acc;
    }, { protein: 0, carbs: 0, fat: 0, fiber: 0 });

    return {
      totalCaloriesToday: Math.round(totalCaloriesToday),
      totalCaloriesWeek: Math.round(totalCaloriesWeek),
      avgCaloriesPerDay,
      nutritionBreakdown: {
        protein: Math.round(nutritionBreakdown.protein),
        carbs: Math.round(nutritionBreakdown.carbs),
        fat: Math.round(nutritionBreakdown.fat),
        fiber: Math.round(nutritionBreakdown.fiber)
      }
    };
  };

  const handleSignOut = async () => {
    try {
      await supabase.auth.signOut();
      navigate('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  if (loading) {
    return (
      <div className="app-container">
        <div className="card">
          <p className="text-center">Loading...</p>
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
            <h1 style={{ textAlign: 'left', marginBottom: '8px' }}>Home Page</h1>
            <p className="subtitle" style={{ textAlign: 'left', marginBottom: 0 }}>
              Welcome back! Plan your meals and manage your grocery list.
            </p>
          </div>
          <button
            onClick={handleSignOut}
            className="btn-danger btn-sm"
          >
            Sign Out
          </button>
        </div>

        {/* Daily Insights Section */}
        <div className="recipe-card mb-4">
          <h2 className="mb-3" style={{ textAlign: 'left' }}>Daily Insights</h2>
          
          <div className="nutrition-grid mb-3">
            <div className="nutrition-item">
              <span className="nutrition-value" style={{ color: '#e91e63' }}>
                {stats.nutritionInsights.nutritionBreakdown.protein}g
              </span>
              <span className="nutrition-label">Protein</span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-value" style={{ color: '#ff9800' }}>
                {stats.nutritionInsights.nutritionBreakdown.fat}g
              </span>
              <span className="nutrition-label">Fats</span>
            </div>
            <div className="nutrition-item">
              <span className="nutrition-value" style={{ color: '#2196f3' }}>
                {stats.nutritionInsights.nutritionBreakdown.carbs}g
              </span>
              <span className="nutrition-label">Carbohydrates</span>
            </div>
          </div>

          {/* Progress bars */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '20px' }}>
            {[
              { label: 'Protein', value: 65, color: '#e91e63' },
              { label: 'Fats', value: 65, color: '#ff9800' },
              { label: 'Carbs', value: 65, color: '#2196f3' }
            ].map((macro, index) => (
              <div key={index} style={{ textAlign: 'center' }}>
                <div style={{
                  width: '80px',
                  height: '80px',
                  borderRadius: '50%',
                  background: `conic-gradient(${macro.color} ${macro.value * 3.6}deg, #e9ecef 0deg)`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 8px',
                  position: 'relative'
                }}>
                  <div style={{
                    width: '60px',
                    height: '60px',
                    backgroundColor: 'white',
                    borderRadius: '50%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '14px',
                    fontWeight: '600',
                    color: macro.color
                  }}>
                    {macro.value}%
                  </div>
                </div>
                <div style={{ fontSize: '14px', color: '#6c757d' }}>{macro.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Recipes Section */}
        <div className="recipe-card mb-4">
          <h3 className="mb-3" style={{ textAlign: 'left' }}>Recent Recipes</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {stats.recentRecipes.length > 0 ? (
              stats.recentRecipes.slice(0, 4).map((recipe, index) => (
                <div key={recipe.id} style={{
                  backgroundColor: '#f8f9fa',
                  padding: '20px',
                  borderRadius: '12px',
                  border: '2px solid #e9ecef',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }} 
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#007bff';
                  e.currentTarget.style.backgroundColor = '#f0f8ff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#e9ecef';
                  e.currentTarget.style.backgroundColor = '#f8f9fa';
                }}>
                  <div style={{ fontSize: '2rem', marginBottom: '12px' }}>
                    {index === 0 ? '🍗' : index === 1 ? '🍤' : index === 2 ? '🥗' : '🍝'}
                  </div>
                  <h4 style={{ 
                    fontSize: '1rem', 
                    fontWeight: '600', 
                    color: '#1a1a1a',
                    marginBottom: '4px'
                  }}>
                    {recipe.title || `Recipe ${index + 1}`}
                  </h4>
                  <p style={{ 
                    fontSize: '0.875rem', 
                    color: '#6c757d', 
                    margin: 0 
                  }}>
                    {recipe.cuisine || 'Unknown'}
                  </p>
                </div>
              ))
            ) : (
              <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px' }}>
                <p style={{ color: '#6c757d', marginBottom: '16px' }}>No recipes yet</p>
                <button 
                  onClick={() => navigate('/generate')}
                  className="btn-primary"
                  style={{ width: 'auto', minWidth: '200px' }}
                >
                  Generate Your First Recipe
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Calorie Tracker Section */}
        <div className="recipe-card mb-4">
          <div style={{
            backgroundColor: '#f8f9fa',
            padding: '40px',
            borderRadius: '12px',
            border: '2px solid #e9ecef',
            textAlign: 'center',
            cursor: 'pointer',
            transition: 'all 0.2s ease'
          }}
          onClick={() => navigate('/nutrition')}
          onMouseEnter={(e) => {
            e.currentTarget.style.borderColor = '#28a745';
            e.currentTarget.style.backgroundColor = '#f0fff4';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.borderColor = '#e9ecef';
            e.currentTarget.style.backgroundColor = '#f8f9fa';
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>📊</div>
            <h3 style={{ 
              fontSize: '1.5rem', 
              fontWeight: '600', 
              color: '#1a1a1a',
              marginBottom: '8px'
            }}>
              Calorie Tracker
            </h3>
            <p style={{ 
              fontSize: '1rem', 
              color: '#6c757d', 
              margin: 0 
            }}>
              Today: {stats.nutritionInsights.totalCaloriesToday} calories
            </p>
          </div>
        </div>

        {/* Navigation Buttons */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', 
          gap: '16px',
          marginTop: '32px'
        }}>
          <button
            onClick={() => navigate('/preferences')}
            className="btn-secondary"
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              padding: '20px',
              height: 'auto',
              gap: '8px'
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>⚙️</span>
            Preferences
          </button>
          
          <button
            onClick={() => navigate('/generate')}
            className="btn-primary"
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              padding: '20px',
              height: 'auto',
              gap: '8px'
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>🍳</span>
            Generate Recipes
          </button>
          
          <button
            onClick={() => navigate('/grocery')}
            className="btn-success"
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              alignItems: 'center', 
              padding: '20px',
              height: 'auto',
              gap: '8px'
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>🛒</span>
            Grocery List
          </button>
        </div>
      </div>
    </div>
  );
}