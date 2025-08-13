import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';

const RecipeScaling = ({ recipe, onRecipeUpdate }) => {
    const [userId, setUserId] = useState(null);  // Start with null instead of test user
    const [servings, setServings] = useState(recipe?.servings || recipe?.original_servings || 4);
    const [scaledRecipe, setScaledRecipe] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [nutritionComparison, setNutritionComparison] = useState(null);
    const [showUnitConverter, setShowUnitConverter] = useState(false);
    const [unitConversions, setUnitConversions] = useState({});
    const [groceryList, setGroceryList] = useState(null);
    const [analytics, setAnalytics] = useState(null);

    // Fetch the real user ID from Supabase auth
    useEffect(() => {
        const fetchUser = async () => {
            try {
                const { data: { user }, error } = await supabase.auth.getUser();
                if (error) {
                    console.error('Error fetching user:', error);
                    setError('Please log in to use recipe scaling');
                    return;
                }
                if (user) {
                    console.log('User authenticated:', user.id);
                    setUserId(user.id);
                } else {
                    console.log('No user found - user needs to log in');
                    setError('Please log in to use recipe scaling');
                }
            } catch (error) {
                console.error('Error in fetchUser:', error);
                setError('Authentication error');
            }
        };
        fetchUser();
    }, []);

    // Get the correct recipe name field
    const getRecipeName = () => {
        return recipe?.title || recipe?.recipe_name || recipe?.name || 'Unknown Recipe';
    };

    useEffect(() => {
        // Only scale if we have a user ID and the servings have changed
        if (userId && recipe && servings !== (recipe.servings || recipe.original_servings || 4)) {
            handleScale();
        }
    }, [servings, userId]); // Add userId as dependency

    const handleScale = async () => {
        // Check if we have all required data
        if (!userId) {
            console.error('No user ID available');
            setError('Please log in to scale recipes');
            return;
        }

        if (!recipe) {
            console.error('No recipe provided');
            setError('No recipe to scale');
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const recipeName = getRecipeName();
            console.log('Scaling recipe:', recipeName, 'to', servings, 'servings for user:', userId);

            const response = await fetch('http://localhost:8000/recipe-scaling/scale-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipe_name: recipeName,
                    new_servings: servings,
                    user_id: userId
                })
            });

            if (!response.ok) {
                const errorData = await response.text();
                console.error('Error response:', errorData);
                throw new Error(`Failed to scale recipe: ${response.status}`);
            }

            const data = await response.json();
            console.log('Scaled recipe data:', data);

            setScaledRecipe(data.recipe);
            onRecipeUpdate && onRecipeUpdate(data.recipe);
        } catch (error) {
            console.error('Error scaling recipe:', error);
            setError(error.message);
        } finally {
            setLoading(false);
        }
    };

    const generateNutritionComparison = async () => {
        if (!userId || !recipe) return;

        try {
            const response = await fetch('http://localhost:8000/recipe-scaling/nutrition-comparison', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipe_name: getRecipeName(),
                    serving_sizes: [2, 4, 6, 8, 12],
                    user_id: userId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setNutritionComparison(data.comparisons);
            }
        } catch (error) {
            console.error('Error getting nutrition comparison:', error);
        }
    };

    const generateGroceryList = async () => {
        if (!userId || !recipe) return;

        try {
            const response = await fetch('http://localhost:8000/recipe-scaling/grocery-list', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipe_name: getRecipeName(),
                    servings: servings,
                    user_id: userId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setGroceryList(data);
            }
        } catch (error) {
            console.error('Error generating grocery list:', error);
        }
    };

    const getRecipeAnalytics = async () => {
        if (!userId || !recipe) return;

        try {
            const response = await fetch('http://localhost:8000/recipe-scaling/recipe-analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipe_name: getRecipeName(),
                    user_id: userId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setAnalytics(data);
            }
        } catch (error) {
            console.error('Error getting analytics:', error);
        }
    };

    const optimizeServings = async () => {
        const targetCalories = prompt('Enter target calories per serving:');
        if (!targetCalories || !userId || !recipe) return;

        try {
            const response = await fetch('http://localhost:8000/recipe-scaling/optimize-servings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipe_name: getRecipeName(),
                    target_calories_per_serving: parseFloat(targetCalories),
                    user_id: userId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setServings(data.optimal_servings);
                alert(data.message);
            }
        } catch (error) {
            console.error('Error optimizing servings:', error);
        }
    };

    // Format ingredient for display
    const formatIngredient = (ingredient) => {
        if (typeof ingredient === 'string') return ingredient;

        const parts = [];
        if (ingredient.quantity) {
            parts.push(typeof ingredient.quantity === 'number'
                ? ingredient.quantity.toFixed(2).replace(/\.00$/, '')
                : ingredient.quantity);
        }
        if (ingredient.unit) {
            parts.push(ingredient.unit);
        }
        if (ingredient.name) {
            parts.push(ingredient.name);
        }
        return parts.join(' ');
    };

    const currentRecipe = scaledRecipe || recipe;
    const originalServings = recipe?.servings || recipe?.original_servings || 4;
    const scalingFactor = servings / originalServings;

    // If no user is logged in, show a message
    if (!userId) {
        return (
            <div className="recipe-card mb-4">
                <div style={{
                    padding: '20px',
                    textAlign: 'center',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '8px',
                    border: '1px solid #dee2e6'
                }}>
                    <h4 style={{ color: '#6c757d', marginBottom: '10px' }}>
                        🔒 Authentication Required
                    </h4>
                    <p style={{ color: '#6c757d' }}>
                        Please log in to use the recipe scaling feature
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="recipe-card mb-4" style={{ position: 'relative' }}>
            <div className="recipe-header">
                <h3 style={{ margin: 0 }}>🔄 Recipe Scaling & Portion Control</h3>
                <div className="recipe-actions">
                    <button onClick={generateNutritionComparison} className="btn-secondary btn-sm">
                        Compare Nutrition
                    </button>
                    <button onClick={generateGroceryList} className="btn-primary btn-sm">
                        Grocery List
                    </button>
                    <button onClick={getRecipeAnalytics} className="btn-warning btn-sm">
                        Analytics
                    </button>
                </div>
            </div>

            {error && (
                <div style={{
                    backgroundColor: '#f8d7da',
                    color: '#721c24',
                    padding: '10px',
                    borderRadius: '6px',
                    marginBottom: '20px',
                    border: '1px solid #f5c6cb'
                }}>
                    {error}
                </div>
            )}

            {/* Serving Size Controls */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '16px',
                marginBottom: '20px'
            }}>
                <div className="form-group">
                    <label>Number of Servings</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <button
                            onClick={() => setServings(Math.max(1, servings - 1))}
                            className="btn-sm"
                            style={{ padding: '4px 8px' }}
                        >
                            -
                        </button>
                        <input
                            type="number"
                            value={servings}
                            onChange={(e) => setServings(Math.max(1, parseInt(e.target.value) || 1))}
                            style={{ width: '60px', textAlign: 'center' }}
                        />
                        <button
                            onClick={() => setServings(servings + 1)}
                            className="btn-sm"
                            style={{ padding: '4px 8px' }}
                        >
                            +
                        </button>
                    </div>
                </div>

                <div className="form-group">
                    <label>Quick Serving Sizes</label>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        {[2, 4, 6, 8, 12].map(size => (
                            <button
                                key={size}
                                onClick={() => setServings(size)}
                                className="btn-sm"
                                style={{
                                    backgroundColor: servings === size ? '#007bff' : '#f8f9fa',
                                    color: servings === size ? 'white' : '#495057',
                                    border: '2px solid #e9ecef',
                                    borderRadius: '16px',
                                    cursor: 'pointer',
                                    fontSize: '0.875rem',
                                    minHeight: 'auto'
                                }}
                            >
                                {size}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="form-group">
                    <label>Smart Optimization</label>
                    <button onClick={optimizeServings} className="btn-success" style={{ width: '100%' }}>
                        🎯 Optimize for Target Calories
                    </button>
                </div>
            </div>

            {/* Scaling Information */}
            {currentRecipe && (
                <div style={{
                    backgroundColor: '#e3f2fd',
                    padding: '16px',
                    borderRadius: '8px',
                    marginBottom: '20px'
                }}>
                    <h4 style={{ color: '#1976d2', marginBottom: '12px' }}>
                        📊 Scaled Recipe Information
                    </h4>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                        gap: '16px'
                    }}>
                        <div>
                            <strong>Servings:</strong> {servings}
                            {originalServings && servings !== originalServings && (
                                <span style={{ color: '#666', fontSize: '0.875rem' }}>
                                    {' '}(was {originalServings})
                                </span>
                            )}
                        </div>
                        <div>
                            <strong>Scaling Factor:</strong> {scalingFactor.toFixed(2)}x
                        </div>
                        <div>
                            <strong>Total Cost:</strong> ${((currentRecipe.cost_estimate || 0) * scalingFactor).toFixed(2)}
                        </div>
                        <div>
                            <strong>Cost/Serving:</strong> ${((currentRecipe.cost_estimate || 0) / servings).toFixed(2)}
                        </div>
                    </div>
                </div>
            )}

            {/* Scaled Ingredients */}
            {currentRecipe?.ingredients && currentRecipe.ingredients.length > 0 && (
                <div className="recipe-section">
                    <h4>📝 Scaled Ingredients ({servings} servings)</h4>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                        gap: '8px'
                    }}>
                        {currentRecipe.ingredients.map((ingredient, index) => (
                            <div key={index} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '8px 12px',
                                backgroundColor: '#f8f9fa',
                                borderRadius: '6px',
                                border: '1px solid #e9ecef'
                            }}>
                                <span>{formatIngredient(ingredient)}</span>
                                {ingredient.cost_per_unit && (
                                    <span style={{ fontSize: '0.875rem', color: '#28a745' }}>
                                        ${((ingredient.quantity || 0) * (ingredient.cost_per_unit || 0)).toFixed(2)}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Additional action buttons */}
            <div style={{
                display: 'flex',
                gap: '12px',
                marginTop: '20px',
                flexWrap: 'wrap'
            }}>
                <button
                    onClick={() => setShowUnitConverter(!showUnitConverter)}
                    className="btn-secondary"
                >
                    🔄 Convert Units
                </button>
            </div>

            {loading && (
                <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    backgroundColor: 'rgba(255, 255, 255, 0.8)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    borderRadius: '12px'
                }}>
                    <div>Scaling recipe...</div>
                </div>
            )}
        </div>
    );
};

export default RecipeScaling;