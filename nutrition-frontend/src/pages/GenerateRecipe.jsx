import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import RecipeRatings from '../components/RecipeRatings'; 

export default function GenerateRecipe() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [title, setTitle] = useState('');
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [recipeResults, setRecipeResults] = useState(null);
  const [regeneratingIndex, setRegeneratingIndex] = useState(null);
  const [showGroceryList, setShowGroceryList] = useState(false);
  const [savingToGroceryList, setSavingToGroceryList] = useState(false);

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

  const handleGenerate = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setRecipeResults(null);
    setShowGroceryList(false);

    // Validation
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
        headers: { 
          'Content-Type': 'application/json',
        },
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
      
      // Validate response structure
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
    if (!userId || !title || !budget) {
      setErrorMsg('Missing required information for regeneration.');
      return;
    }

    setRegeneratingIndex(recipeIndex);
    setErrorMsg('');

    try {
      const payload = {
        title: title.trim(),
        budget: parseFloat(budget),
        user_id: userId,
        regenerate_single: true,
        exclude_recipes: recipeResults.slice(0, recipeIndex).concat(recipeResults.slice(recipeIndex + 1))
      };
      
      const res = await fetch('http://localhost:8000/generate-single-recipe', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
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
      
      if (data && data.recipe) {
        const updatedRecipes = [...recipeResults];
        updatedRecipes[recipeIndex] = data.recipe;
        setRecipeResults(updatedRecipes);
      } else {
        throw new Error('Invalid response format from server');
      }
      
    } catch (err) {
      console.error('Recipe regeneration error:', err);
      setErrorMsg(`Error regenerating recipe: ${err.message}`);
    } finally {
      setRegeneratingIndex(null);
    }
  };

  // Helper functions for ingredient consolidation
  const normalizeIngredientName = (name) => {
    if (!name) return 'unknown';
    
    let normalized = name.toLowerCase().trim();
    
    const descriptorsToRemove = [
      'diced', 'chopped', 'sliced', 'minced', 'crushed', 'grated',
      'fresh', 'dried', 'frozen', 'canned', 'cooked', 'raw',
      'boneless', 'skinless', 'lean', 'ground', 'whole',
      'large', 'medium', 'small', 'extra', 'jumbo',
      'organic', 'free-range', 'grass-fed'
    ];
    
    descriptorsToRemove.forEach(descriptor => {
      const regex = new RegExp(`\\b${descriptor}\\s+`, 'gi');
      normalized = normalized.replace(regex, '');
    });
    
    const ingredientMappings = {
      'chicken breast': 'chicken',
      'chicken thigh': 'chicken',
      'chicken thighs': 'chicken',
      'chicken leg': 'chicken',
      'chicken drumstick': 'chicken',
      'chicken wing': 'chicken',
      'chicken tender': 'chicken',
      'ground beef': 'beef',
      'beef chuck': 'beef',
      'beef sirloin': 'beef',
      'steak': 'beef',
      'beef steak': 'beef',
      'pork chop': 'pork',
      'pork shoulder': 'pork',
      'pork loin': 'pork',
      'yellow onion': 'onion',
      'white onion': 'onion',
      'red onion': 'onion',
      'sweet onion': 'onion',
      'roma tomato': 'tomato',
      'cherry tomato': 'tomato',
      'grape tomato': 'tomato',
      'beefsteak tomato': 'tomato',
      'bell pepper': 'bell pepper',
      'red bell pepper': 'bell pepper',
      'green bell pepper': 'bell pepper',
      'yellow bell pepper': 'bell pepper',
      'garlic clove': 'garlic',
      'garlic bulb': 'garlic'
    };
    
    for (const [variant, base] of Object.entries(ingredientMappings)) {
      if (normalized.includes(variant)) {
        normalized = base;
        break;
      }
    }
    
    normalized = normalized.replace(/\s+/g, ' ').trim();
    return normalized || name.toLowerCase();
  };

  const getDisplayName = (normalizedName, originalName) => {
    const capitalize = (str) => str.charAt(0).toUpperCase() + str.slice(1);
    
    const commonIngredients = [
      'chicken', 'beef', 'pork', 'fish', 'turkey', 'lamb',
      'onion', 'tomato', 'garlic', 'carrot', 'celery',
      'bread', 'cheese', 'milk', 'eggs'
    ];
    
    if (commonIngredients.includes(normalizedName)) {
      return capitalize(normalizedName);
    }
    
    return capitalize(originalName);
  };

  const generateConsolidatedGroceryList = () => {
    if (!recipeResults || recipeResults.length === 0) return [];

    const consolidatedItems = {};

    recipeResults.forEach(recipe => {
      const groceryList = recipe.grocery_list || [];
      groceryList.forEach(item => {
        const originalName = item.item || 'Unknown item';
        const normalizedName = normalizeIngredientName(originalName);
        const quantity = item.quantity || 1;
        const cost = item.estimated_cost || 0;

        if (consolidatedItems[normalizedName]) {
          consolidatedItems[normalizedName].quantity += quantity;
          consolidatedItems[normalizedName].estimated_cost += cost;
          
          if (!consolidatedItems[normalizedName].originalNames.includes(originalName)) {
            consolidatedItems[normalizedName].originalNames.push(originalName);
          }
        } else {
          consolidatedItems[normalizedName] = {
            item: getDisplayName(normalizedName, originalName),
            displayName: getDisplayName(normalizedName, originalName),
            quantity: quantity,
            estimated_cost: cost,
            originalNames: [originalName]
          };
        }
      });
    });

    return Object.values(consolidatedItems).map(item => ({
      ...item,
      estimated_cost: Math.round(item.estimated_cost * 100) / 100
    }));
  };

  const getTotalGroceryCost = () => {
    const groceryList = generateConsolidatedGroceryList();
    return groceryList.reduce((total, item) => total + item.estimated_cost, 0).toFixed(2);
  };

  const saveToGroceryList = async () => {
    if (!userId || !recipeResults || recipeResults.length === 0) {
      setErrorMsg('No recipes or user information available.');
      return;
    }

    setSavingToGroceryList(true);
    setErrorMsg('');

    try {
      const groceryList = generateConsolidatedGroceryList();
      
      const payload = {
        user_id: userId,
        grocery_items: groceryList.map(item => ({
          item_name: item.item,
          quantity: item.quantity,
          estimated_cost: item.estimated_cost,
          category: 'Recipe Generated',
          is_purchased: false
        }))
      };

      const res = await fetch('http://localhost:8000/save-grocery-list', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
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

      const shouldNavigate = window.confirm(
        `Successfully added ${groceryList.length} items to your grocery list! Would you like to view your grocery list now?`
      );
      
      if (shouldNavigate) {
        navigate('/grocery');
      }
      
    } catch (err) {
      console.error('Save to grocery list error:', err);
      setErrorMsg(`Error saving to grocery list: ${err.message}`);
    } finally {
      setSavingToGroceryList(false);
    }
  };

  const handleRatingSubmit = (rating, feedback) => {
    console.log(`Recipe rated ${rating} stars`, feedback);
    // Optional: Show a brief success message or update UI
  };

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

        {groceryList.length > 0 && (
          <>
            <h4>Grocery List for This Recipe</h4>
            <ul>
              {groceryList.map((item, i) => (
                <li key={i}>
                  {item.quantity || 1} × {item.item || 'Unknown item'} — 
                  ${typeof item.estimated_cost === 'number' ? item.estimated_cost.toFixed(2) : '0.00'}
                </li>
              ))}
            </ul>
          </>
        )}
        
        <p style={{ fontStyle: 'italic' }}>
          Estimated cost: ${typeof rec.cost_estimate === 'number' ? rec.cost_estimate.toFixed(2) : '0.00'}
        </p>

        {/* ADD THE RATING COMPONENT HERE */}
        <RecipeRating 
          recipeData={rec}
          userId={userId}
          onRatingSubmit={handleRatingSubmit}
        />
      </div>
    );
  };

  const renderConsolidatedGroceryList = () => {
    const groceryList = generateConsolidatedGroceryList();
    
    return (
      <div style={{ marginTop: '32px', border: '2px solid #4CAF50', padding: '16px', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
        <h3 style={{ color: '#4CAF50', marginBottom: '16px' }}>Consolidated Grocery List</h3>
        <p style={{ marginBottom: '16px', color: '#666' }}>
          This list combines similar ingredients from your selected recipes:
        </p>
        
        {groceryList.length > 0 ? (
          <>
            <ul style={{ marginBottom: '16px' }}>
              {groceryList.map((item, i) => (
                <li key={i} style={{ marginBottom: '8px' }}>
                  <strong>{item.quantity}</strong> × {item.displayName} — 
                  <span style={{ color: '#4CAF50', fontWeight: 'bold' }}>
                    ${item.estimated_cost.toFixed(2)}
                  </span>
                  {item.originalNames && item.originalNames.length > 1 && (
                    <span style={{ fontSize: '12px', color: '#888', marginLeft: '8px' }}>
                      (combines: {item.originalNames.join(', ')})
                    </span>
                  )}
                </li>
              ))}
            </ul>
            <div style={{ borderTop: '1px solid #ddd', paddingTop: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <p style={{ fontSize: '18px', fontWeight: 'bold', color: '#4CAF50', margin: 0 }}>
                  Total Estimated Cost: ${getTotalGroceryCost()}
                </p>
                <button
                  onClick={saveToGroceryList}
                  disabled={savingToGroceryList}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: savingToGroceryList ? '#ccc' : '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: savingToGroceryList ? 'not-allowed' : 'pointer',
                    fontSize: '14px',
                    fontWeight: 'bold',
                    marginRight: '12px'
                  }}
                >
                  {savingToGroceryList ? 'Saving...' : 'Save to Grocery List'}
                </button>
                <button
                  onClick={() => navigate('/grocery')}
                  style={{
                    padding: '10px 20px',
                    backgroundColor: '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '14px',
                    fontWeight: 'bold'
                  }}
                >
                  View Grocery List
                </button>
              </div>
            </div>
          </>
        ) : (
          <p style={{ color: '#666' }}>No grocery items found.</p>
        )}
      </div>
    );
  };

  return (
    <div className="card">
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
        <>
          <div style={{ marginTop: '24px', marginBottom: '16px', display: 'flex', gap: '12px' }}>
            <button
              onClick={() => setShowGroceryList(!showGroceryList)}
              style={{
                padding: '12px 24px',
                backgroundColor: showGroceryList ? '#ff9800' : '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              {showGroceryList ? 'Hide Grocery List' : 'Generate Grocery List'}
            </button>
            <span style={{ 
              padding: '12px 16px', 
              backgroundColor: '#e3f2fd', 
              borderRadius: '4px',
              color: '#1976d2',
              fontSize: '14px',
              alignSelf: 'center'
            }}>
              Total recipes: {recipeResults.length}
            </span>
          </div>

          {showGroceryList && renderConsolidatedGroceryList()}

          <div style={{ marginTop: '24px', textAlign: 'left' }}>
            <h3>Generated Recipes</h3>
            <p style={{ color: '#666', marginBottom: '16px' }}>
              Don't like a recipe? Click "Regenerate" to get a new one or rate it below!
            </p>
            {recipeResults.map((rec, idx) => renderRecipe(rec, idx))}
          </div>
        </>
      )}

      {recipeResults && recipeResults.length === 0 && (
        <div style={{ marginTop: '24px', textAlign: 'center', color: '#666' }}>
          No recipes were generated. Please try again with different parameters.
        </div>
      )}
    </div>
  );
}