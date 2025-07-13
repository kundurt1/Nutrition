// nutrition-frontend/src/components/RecipeScaling.jsx

import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';

const RecipeScaling = ({ recipe, onRecipeUpdate }) => {
    const [userId, setUserId] = useState(null);
    const [servings, setServings] = useState(recipe?.original_servings || 4);
    const [scaledRecipe, setScaledRecipe] = useState(null);
    const [loading, setLoading] = useState(false);
    const [nutritionComparison, setNutritionComparison] = useState(null);
    const [showUnitConverter, setShowUnitConverter] = useState(false);
    const [unitConversions, setUnitConversions] = useState({});
    const [groceryList, setGroceryList] = useState(null);
    const [analytics, setAnalytics] = useState(null);

    useEffect(() => {
        const fetchUser = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            if (user) setUserId(user.id);
        };
        fetchUser();
    }, []);

    useEffect(() => {
        if (recipe && servings !== recipe.original_servings) {
            handleScale();
        }
    }, [servings]);

    const handleScale = async () => {
        if (!userId || !recipe) return;

        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/recipe-scaling/scale-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recipe_name: recipe.name,
                    new_servings: servings,
                    user_id: userId
                })
            });

            if (response.ok) {
                const data = await response.json();
                setScaledRecipe(data.recipe);
                onRecipeUpdate && onRecipeUpdate(data.recipe);
            }
        } catch (error) {
            console.error('Error scaling recipe:', error);
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
                    recipe_name: recipe.name,
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
                    recipe_name: recipe.name,
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
                    recipe_name: recipe.name,
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
                    recipe_name: recipe.name,
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

    const currentRecipe = scaledRecipe || recipe;

    return (
        <div className="recipe-card mb-4">
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
                            style={{
                                padding: '8px 12px',
                                backgroundColor: '#f8f9fa',
                                border: '2px solid #e9ecef',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                minHeight: 'auto'
                            }}
                        >
                            -
                        </button>
                        <input
                            type="number"
                            value={servings}
                            onChange={(e) => setServings(Math.max(1, parseInt(e.target.value) || 1))}
                            min="1"
                            style={{
                                width: '80px',
                                textAlign: 'center',
                                padding: '8px'
                            }}
                        />
                        <button
                            onClick={() => setServings(servings + 1)}
                            style={{
                                padding: '8px 12px',
                                backgroundColor: '#f8f9fa',
                                border: '2px solid #e9ecef',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                minHeight: 'auto'
                            }}
                        >
                            +
                        </button>
                    </div>
                </div>

                <div className="form-group">
                    <label>Quick Serving Sizes</label>
                    <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {[2, 4, 6, 8, 12].map(size => (
                            <button
                                key={size}
                                onClick={() => setServings(size)}
                                style={{
                                    padding: '6px 12px',
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
                            {recipe?.original_servings && servings !== recipe.original_servings && (
                                <span style={{ color: '#666', fontSize: '0.875rem' }}>
                  {' '}(was {recipe.original_servings})
                </span>
                            )}
                        </div>
                        <div>
                            <strong>Scaling Factor:</strong> {scaledRecipe ?
                            (servings / (recipe?.original_servings || 4)).toFixed(2) + 'x' : '1x'}
                        </div>
                        <div>
                            <strong>Total Cost:</strong> ${((currentRecipe.cost_estimate || 0) * servings / (recipe?.original_servings || 4)).toFixed(2)}
                        </div>
                        <div>
                            <strong>Cost/Serving:</strong> ${((currentRecipe.cost_estimate || 0) / servings).toFixed(2)}
                        </div>
                    </div>
                </div>
            )}

            {/* Scaled Ingredients */}
            {currentRecipe?.ingredients && (
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
                <span>
                  <strong>{ingredient.quantity?.toFixed(2) || ingredient.quantity}</strong> {ingredient.unit} {ingredient.name}
                </span>
                                <span style={{ fontSize: '0.875rem', color: '#28a745' }}>
                  ${((ingredient.quantity || 0) * (ingredient.cost_per_unit || 0)).toFixed(2)}
                </span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Nutrition Comparison */}
            {nutritionComparison && (
                <div className="recipe-section">
                    <h4>📈 Nutrition Comparison Across Serving Sizes</h4>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                            <tr style={{ backgroundColor: '#f8f9fa' }}>
                                <th style={{ padding: '8px', border: '1px solid #e9ecef' }}>Servings</th>
                                <th style={{ padding: '8px', border: '1px solid #e9ecef' }}>Cal/Serving</th>
                                <th style={{ padding: '8px', border: '1px solid #e9ecef' }}>Protein/Serving</th>
                                <th style={{ padding: '8px', border: '1px solid #e9ecef' }}>Total Cost</th>
                                <th style={{ padding: '8px', border: '1px solid #e9ecef' }}>Cost/Serving</th>
                            </tr>
                            </thead>
                            <tbody>
                            {Object.entries(nutritionComparison).map(([key, data]) => (
                                <tr key={key} style={{
                                    backgroundColor: data.total_servings === servings ? '#e3f2fd' : 'white'
                                }}>
                                    <td style={{ padding: '8px', border: '1px solid #e9ecef', textAlign: 'center' }}>
                                        {data.total_servings}
                                    </td>
                                    <td style={{ padding: '8px', border: '1px solid #e9ecef', textAlign: 'center' }}>
                                        {data.per_serving?.calories || 0}
                                    </td>
                                    <td style={{ padding: '8px', border: '1px solid #e9ecef', textAlign: 'center' }}>
                                        {data.per_serving?.protein || 0}g
                                    </td>
                                    <td style={{ padding: '8px', border: '1px solid #e9ecef', textAlign: 'center' }}>
                                        ${data.total_cost?.toFixed(2) || '0.00'}
                                    </td>
                                    <td style={{ padding: '8px', border: '1px solid #e9ecef', textAlign: 'center' }}>
                                        ${data.cost_per_serving?.toFixed(2) || '0.00'}
                                    </td>
                                </tr>
                            ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Grocery List */}
            {groceryList && (
                <div className="recipe-section">
                    <h4>🛒 Grocery List ({servings} servings)</h4>
                    <div style={{
                        marginBottom: '12px',
                        padding: '8px 12px',
                        backgroundColor: '#d4edda',
                        borderRadius: '6px',
                        color: '#155724'
                    }}>
                        <strong>Total Cost: ${groceryList.total_cost?.toFixed(2)}</strong> •
                        <span> {groceryList.total_items} items</span>
                    </div>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                        gap: '8px'
                    }}>
                        {groceryList.grocery_list?.map((item, index) => (
                            <div key={index} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: '8px 12px',
                                backgroundColor: '#f8f9fa',
                                borderRadius: '6px',
                                border: '1px solid #e9ecef'
                            }}>
                                <div>
                                    <div><strong>{item.name}</strong></div>
                                    <div style={{ fontSize: '0.875rem', color: '#666' }}>
                                        {item.quantity} {item.unit}
                                    </div>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ color: '#28a745', fontWeight: 'bold' }}>
                                        ${item.total_cost?.toFixed(2)}
                                    </div>
                                    <div style={{ fontSize: '0.875rem', color: '#666' }}>
                                        ${item.cost_per_unit?.toFixed(2)}/{item.unit}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recipe Analytics */}
            {analytics && (
                <div className="recipe-section">
                    <h4>📊 Recipe Analytics</h4>

                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: '16px',
                        marginBottom: '16px'
                    }}>
                        <div style={{
                            padding: '16px',
                            backgroundColor: '#f8f9fa',
                            borderRadius: '8px',
                            textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#007bff' }}>
                                {analytics.total_time} min
                            </div>
                            <div style={{ fontSize: '0.875rem', color: '#666' }}>Total Time</div>
                        </div>

                        <div style={{
                            padding: '16px',
                            backgroundColor: '#f8f9fa',
                            borderRadius: '8px',
                            textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#28a745' }}>
                                ${analytics.cost_analysis?.cost_per_calorie?.toFixed(4)}
                            </div>
                            <div style={{ fontSize: '0.875rem', color: '#666' }}>Cost per Calorie</div>
                        </div>

                        <div style={{
                            padding: '16px',
                            backgroundColor: '#f8f9fa',
                            borderRadius: '8px',
                            textAlign: 'center'
                        }}>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ffc107' }}>
                                {analytics.ingredient_count}
                            </div>
                            <div style={{ fontSize: '0.875rem', color: '#666' }}>Ingredients</div>
                        </div>
                    </div>

                    {/* Macro Breakdown */}
                    {analytics.macro_percentages && (
                        <div>
                            <h5>Macronutrient Breakdown</h5>
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(3, 1fr)',
                                gap: '12px'
                            }}>
                                {Object.entries(analytics.macro_percentages).map(([macro, percentage]) => (
                                    <div key={macro} style={{ textAlign: 'center' }}>
                                        <div style={{
                                            width: '60px',
                                            height: '60px',
                                            borderRadius: '50%',
                                            background: `conic-gradient(
                        ${macro === 'protein_percent' ? '#e91e63' :
                                                macro === 'carbs_percent' ? '#2196f3' : '#ff9800'} 
                        ${percentage * 3.6}deg, 
                        #e9ecef 0deg)`,
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            margin: '0 auto 8px',
                                            position: 'relative'
                                        }}>
                                            <div style={{
                                                width: '40px',
                                                height: '40px',
                                                backgroundColor: 'white',
                                                borderRadius: '50%',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                fontSize: '12px',
                                                fontWeight: '600'
                                            }}>
                                                {percentage?.toFixed(0)}%
                                            </div>
                                        </div>
                                        <div style={{ fontSize: '0.875rem', textTransform: 'capitalize' }}>
                                            {macro.replace('_percent', '')}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Action Buttons */}
            <div style={{
                display: 'flex',
                gap: '12px',
                marginTop: '20px',
                flexWrap: 'wrap'
            }}>
                <button
                    onClick={() => setShowUnitConverter(!showUnitConverter)}
                    className="btn-secondary"
                    style={{ flex: '1', minWidth: '150px' }}
                >
                    🔄 Convert Units
                </button>

                <button
                    onClick={generateNutritionComparison}
                    className="btn-primary"
                    style={{ flex: '1', minWidth: '150px' }}
                >
                    📈 Compare Nutrition
                </button>

                <button
                    onClick={generateGroceryList}
                    className="btn-success"
                    style={{ flex: '1', minWidth: '150px' }}
                >
                    🛒 Generate Grocery List
                </button>
            </div>

            {/* Unit Converter Panel */}
            {showUnitConverter && (
                <div style={{
                    marginTop: '20px',
                    padding: '16px',
                    backgroundColor: '#fff3cd',
                    borderRadius: '8px',
                    border: '1px solid #ffeaa7'
                }}>
                    <h5>🔄 Unit Converter</h5>
                    <p style={{ fontSize: '0.875rem', color: '#856404' }}>
                        Convert ingredients to different units. Changes will be applied to the recipe.
                    </p>

                    {currentRecipe?.ingredients?.map((ingredient, index) => (
                        <div key={index} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '12px',
                            marginBottom: '8px',
                            padding: '8px',
                            backgroundColor: 'white',
                            borderRadius: '6px'
                        }}>
                            <span style={{ flex: 1 }}>{ingredient.name}</span>
                            <span style={{ width: '80px' }}>{ingredient.quantity} {ingredient.unit}</span>
                            <select
                                onChange={(e) => {
                                    if (e.target.value) {
                                        setUnitConversions(prev => ({
                                            ...prev,
                                            [ingredient.name]: e.target.value
                                        }));
                                    }
                                }}
                                style={{ width: '100px', padding: '4px' }}
                            >
                                <option value="">Convert to...</option>
                                <option value="cups">cups</option>
                                <option value="ml">ml</option>
                                <option value="g">grams</option>
                                <option value="oz">oz</option>
                                <option value="lb">pounds</option>
                                <option value="tsp">tsp</option>
                                <option value="tbsp">tbsp</option>
                            </select>
                        </div>
                    ))}

                    {Object.keys(unitConversions).length > 0 && (
                        <button
                            onClick={async () => {
                                try {
                                    const response = await fetch('http://localhost:8000/recipe-scaling/convert-units', {
                                        method: 'POST',
                                        headers: { 'Content-Type': 'application/json' },
                                        body: JSON.stringify({
                                            recipe_name: recipe.name,
                                            unit_conversions: unitConversions,
                                            user_id: userId
                                        })
                                    });

                                    if (response.ok) {
                                        alert('Units converted successfully!');
                                        setUnitConversions({});
                                        setShowUnitConverter(false);
                                        // Refresh the recipe
                                        handleScale();
                                    }
                                } catch (error) {
                                    console.error('Error converting units:', error);
                                }
                            }}
                            className="btn-warning"
                            style={{ marginTop: '12px' }}
                        >
                            Apply Unit Conversions
                        </button>
                    )}
                </div>
            )}

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