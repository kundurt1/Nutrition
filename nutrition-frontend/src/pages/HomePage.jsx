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
    recentActivity: [],
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
        
        // Fetch user stats
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
        .limit(30); // Get last 30 meal logs

      // Calculate nutrition insights
      const nutritionInsights = calculateNutritionInsights(mealLogs || [], recipes || []);

      setStats({
        totalRecipes: recipes?.length || 0,
        totalGroceryItems: groceryItems?.filter(item => !item.is_purchased).length || 0,
        recentRecipes: recipes || [],
        recentGroceryItems: groceryItems || [],
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

    // Find favorite cuisines from meal logs
    const cuisineCount = {};
    mealLogs.forEach(meal => {
      const cuisine = meal.recipes?.cuisine || 'Unknown';
      cuisineCount[cuisine] = (cuisineCount[cuisine] || 0) + 1;
    });

    const favoriteCuisines = Object.entries(cuisineCount)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 3)
      .map(([cuisine, count]) => ({ cuisine, count }));

    // Find favorite meals (most frequently logged recipes)
    const mealCount = {};
    mealLogs.forEach(meal => {
      const title = meal.recipes?.title || 'Unknown';
      mealCount[title] = (mealCount[title] || 0) + 1;
    });

    const favoriteMeals = Object.entries(mealCount)
      .sort(([,a], [,b]) => b - a)
      .slice(0, 3)
      .map(([title, count]) => ({ title, count }));

    return {
      totalCaloriesToday: Math.round(totalCaloriesToday),
      totalCaloriesWeek: Math.round(totalCaloriesWeek),
      avgCaloriesPerDay,
      favoriteCuisines,
      favoriteMeals,
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
      <div className="card">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="card" style={{ maxWidth: '800px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '32px',
        paddingBottom: '16px',
        borderBottom: '2px solid #f0f0f0'
      }}>
        <div>
          <h1 style={{ margin: '0 0 8px 0', color: '#333' }}>Nutrition App</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '16px' }}>
            Welcome back! Plan your meals and manage your grocery list.
          </p>
        </div>
        <button
          onClick={handleSignOut}
          style={{
            padding: '8px 16px',
            backgroundColor: '#f44336',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          Sign Out
        </button>
      </div>

      {/* Enhanced Stats Dashboard */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
        gap: '16px', 
        marginBottom: '32px' 
      }}>
        <div style={{
          padding: '20px',
          backgroundColor: '#e3f2fd',
          borderRadius: '8px',
          textAlign: 'center',
          border: '1px solid #2196F3'
        }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#1976d2', fontSize: '24px' }}>
            {stats.totalRecipes}
          </h3>
          <p style={{ margin: 0, color: '#1976d2', fontSize: '14px' }}>
            Recipes Created
          </p>
        </div>
        
        <div style={{
          padding: '20px',
          backgroundColor: '#e8f5e8',
          borderRadius: '8px',
          textAlign: 'center',
          border: '1px solid #4CAF50'
        }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#388e3c', fontSize: '24px' }}>
            {stats.totalGroceryItems}
          </h3>
          <p style={{ margin: 0, color: '#388e3c', fontSize: '14px' }}>
            Items to Buy
          </p>
        </div>

        <div style={{
          padding: '20px',
          backgroundColor: '#fff3e0',
          borderRadius: '8px',
          textAlign: 'center',
          border: '1px solid #ff9800'
        }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#f57c00', fontSize: '24px' }}>
            {stats.nutritionInsights.totalCaloriesToday}
          </h3>
          <p style={{ margin: 0, color: '#f57c00', fontSize: '14px' }}>
            Calories Today
          </p>
        </div>

        <div style={{
          padding: '20px',
          backgroundColor: '#f3e5f5',
          borderRadius: '8px',
          textAlign: 'center',
          border: '1px solid #9c27b0'
        }}>
          <h3 style={{ margin: '0 0 8px 0', color: '#7b1fa2', fontSize: '24px' }}>
            {stats.nutritionInsights.avgCaloriesPerDay}
          </h3>
          <p style={{ margin: 0, color: '#7b1fa2', fontSize: '14px' }}>
            Avg Calories/Day
          </p>
        </div>
      </div>

      {/* Nutrition Insights Section */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
        gap: '20px', 
        marginBottom: '32px' 
      }}>
        {/* Weekly Nutrition Breakdown */}
        <div style={{
          padding: '20px',
          backgroundColor: '#f9f9f9',
          borderRadius: '8px',
          border: '1px solid #ddd'
        }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '18px' }}>
            📊 Weekly Nutrition
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff', borderRadius: '6px' }}>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#e91e63' }}>
                {stats.nutritionInsights.nutritionBreakdown.protein}g
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>Protein</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff', borderRadius: '6px' }}>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#2196f3' }}>
                {stats.nutritionInsights.nutritionBreakdown.carbs}g
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>Carbs</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff', borderRadius: '6px' }}>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#ff9800' }}>
                {stats.nutritionInsights.nutritionBreakdown.fat}g
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>Fat</div>
            </div>
            <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff', borderRadius: '6px' }}>
              <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#4caf50' }}>
                {stats.nutritionInsights.nutritionBreakdown.fiber}g
              </div>
              <div style={{ fontSize: '12px', color: '#666' }}>Fiber</div>
            </div>
          </div>
          <div style={{ 
            marginTop: '12px', 
            padding: '8px', 
            backgroundColor: '#e3f2fd', 
            borderRadius: '4px', 
            textAlign: 'center',
            fontSize: '14px',
            color: '#1976d2'
          }}>
            Total Week: {stats.nutritionInsights.totalCaloriesWeek} calories
          </div>
        </div>

        {/* Favorite Cuisines */}
        <div style={{
          padding: '20px',
          backgroundColor: '#f9f9f9',
          borderRadius: '8px',
          border: '1px solid #ddd'
        }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '18px' }}>
            🌎 Favorite Cuisines
          </h3>
          {stats.nutritionInsights.favoriteCuisines.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {stats.nutritionInsights.favoriteCuisines.map((item, index) => (
                <div key={index} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: '#fff',
                  borderRadius: '6px',
                  border: '1px solid #eee'
                }}>
                  <span style={{ fontWeight: 'bold', color: '#333' }}>
                    {item.cuisine}
                  </span>
                  <span style={{
                    backgroundColor: '#4caf50',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px'
                  }}>
                    {item.count}x
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: '14px', textAlign: 'center', margin: 0 }}>
              Start logging meals to see your favorite cuisines!
            </p>
          )}
        </div>

        {/* Favorite Meals */}
        <div style={{
          padding: '20px',
          backgroundColor: '#f9f9f9',
          borderRadius: '8px',
          border: '1px solid #ddd'
        }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '18px' }}>
            ❤️ Favorite Meals
          </h3>
          {stats.nutritionInsights.favoriteMeals.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {stats.nutritionInsights.favoriteMeals.map((item, index) => (
                <div key={index} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 12px',
                  backgroundColor: '#fff',
                  borderRadius: '6px',
                  border: '1px solid #eee'
                }}>
                  <span style={{ fontWeight: 'bold', color: '#333', fontSize: '14px' }}>
                    {item.title.length > 25 ? item.title.substring(0, 25) + '...' : item.title}
                  </span>
                  <span style={{
                    backgroundColor: '#e91e63',
                    color: 'white',
                    padding: '2px 8px',
                    borderRadius: '12px',
                    fontSize: '12px'
                  }}>
                    {item.count}x
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#666', fontSize: '14px', textAlign: 'center', margin: 0 }}>
              Start logging meals to see your favorites!
            </p>
          )}
        </div>
      </div>

      {/* Main Navigation Cards */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', 
        gap: '20px', 
        marginBottom: '32px' 
      }}>
        {/* Generate Recipes Card */}
        <div 
          onClick={() => navigate('/generate')}
          style={{
            padding: '24px',
            border: '2px solid #2196F3',
            borderRadius: '12px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            backgroundColor: '#fff',
            textAlign: 'center'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#e3f2fd';
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(33, 150, 243, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#fff';
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🍳</div>
          <h3 style={{ margin: '0 0 12px 0', color: '#1976d2', fontSize: '20px' }}>
            Generate Recipes
          </h3>
          <p style={{ margin: 0, color: '#666', fontSize: '14px', lineHeight: '1.4' }}>
            Create personalized recipes based on your budget and dietary preferences
          </p>
          {stats.recentRecipes && stats.recentRecipes.length > 0 && (
            <div style={{ marginTop: '12px', fontSize: '12px', color: '#888' }}>
              Last created: {new Date(stats.recentRecipes[0].created_at).toLocaleDateString()}
            </div>
          )}
        </div>

        {/* Grocery List Card */}
        <div 
          onClick={() => navigate('/grocery')}
          style={{
            padding: '24px',
            border: '2px solid #4CAF50',
            borderRadius: '12px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            backgroundColor: '#fff',
            textAlign: 'center'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#e8f5e8';
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(76, 175, 80, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#fff';
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🛒</div>
          <h3 style={{ margin: '0 0 12px 0', color: '#388e3c', fontSize: '20px' }}>
            Grocery List
          </h3>
          <p style={{ margin: 0, color: '#666', fontSize: '14px', lineHeight: '1.4' }}>
            Manage your shopping list and track items from your generated recipes
          </p>
          {stats.totalGroceryItems > 0 && (
            <div style={{ marginTop: '12px', fontSize: '12px', color: '#888' }}>
              {stats.totalGroceryItems} items waiting to be purchased
            </div>
          )}
        </div>

        {/* Preferences Card */}
        <div 
          onClick={() => navigate('/preferences')}
          style={{
            padding: '24px',
            border: '2px solid #ff9800',
            borderRadius: '12px',
            cursor: 'pointer',
            transition: 'all 0.3s ease',
            backgroundColor: '#fff',
            textAlign: 'center'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#fff3e0';
            e.currentTarget.style.transform = 'translateY(-2px)';
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(255, 152, 0, 0.3)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = '#fff';
            e.currentTarget.style.transform = 'translateY(0)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        >
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>⚙️</div>
          <h3 style={{ margin: '0 0 12px 0', color: '#f57c00', fontSize: '20px' }}>
            Preferences
          </h3>
          <p style={{ margin: 0, color: '#666', fontSize: '14px', lineHeight: '1.4' }}>
            Set your dietary restrictions, budget preferences, and allergies
          </p>
        </div>
      </div>

      {/* Recent Activity */}
      {(stats.recentRecipes?.length > 0 || stats.recentGroceryItems?.length > 0) && (
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f9f9f9', 
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h3 style={{ margin: '0 0 16px 0', color: '#333' }}>📈 Recent Activity</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Recent Recipes */}
            {stats.recentRecipes?.length > 0 && (
              <div>
                <h4 style={{ margin: '0 0 8px 0', color: '#1976d2', fontSize: '16px' }}>
                  🍳 Latest Recipes
                </h4>
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                  {stats.recentRecipes.slice(0, 3).map((recipe, index) => (
                    <li key={recipe.id} style={{ 
                      padding: '8px 0', 
                      fontSize: '14px', 
                      color: '#666',
                      borderBottom: index < 2 ? '1px solid #eee' : 'none'
                    }}>
                      <div style={{ fontWeight: 'bold', color: '#333' }}>{recipe.title}</div>
                      <div style={{ fontSize: '12px', color: '#888' }}>
                        {recipe.cuisine} • {new Date(recipe.created_at).toLocaleDateString()}
                        {recipe.macro_estimate?.calories && (
                          <span style={{ marginLeft: '8px', color: '#4caf50' }}>
                            {recipe.macro_estimate.calories} cal
                          </span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recent Grocery Items */}
            {stats.recentGroceryItems?.length > 0 && (
              <div>
                <h4 style={{ margin: '0 0 8px 0', color: '#388e3c', fontSize: '16px' }}>
                  🛒 Recent Grocery Items
                </h4>
                <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                  {stats.recentGroceryItems.slice(0, 3).map((item, index) => (
                    <li key={item.id} style={{ 
                      padding: '8px 0', 
                      fontSize: '14px', 
                      color: '#666',
                      borderBottom: index < 2 ? '1px solid #eee' : 'none',
                      textDecoration: item.is_purchased ? 'line-through' : 'none'
                    }}>
                      <div style={{ fontWeight: 'bold', color: item.is_purchased ? '#4caf50' : '#333' }}>
                        {item.name} {item.is_purchased ? '✓' : ''}
                      </div>
                      <div style={{ fontSize: '12px', color: '#888' }}>
                        {new Date(item.created_at).toLocaleDateString()}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div style={{ 
        display: 'flex', 
        gap: '12px', 
        justifyContent: 'center',
        marginTop: '20px'
      }}>
        <button
          onClick={() => navigate('/generate')}
          style={{
            padding: '12px 24px',
            backgroundColor: '#2196F3',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Start Cooking 🍳
        </button>
        
        <button
          onClick={() => navigate('/grocery')}
          style={{
            padding: '12px 24px',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Go Shopping 🛒
        </button>
      </div>
    </div>
  );
}