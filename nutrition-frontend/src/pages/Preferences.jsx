// src/pages/Preferences.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Preferences() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  
  // Basic preferences
  const [budget, setBudget] = useState('20-30');
  const [allergies, setAllergies] = useState('');
  const [diet, setDiet] = useState('');
  
  // Advanced dietary restrictions
  const [dietaryRestrictions, setDietaryRestrictions] = useState({
    glutenFree: false,
    dairyFree: false,
    nutFree: false,
    lowSodium: false,
    lowSugar: false,
    lowFat: false,
    highProtein: false,
    vegetarian: false,
    vegan: false,
    keto: false,
    paleo: false,
    wholeFoods: false
  });
  
  // Macro targets
  const [macroTargets, setMacroTargets] = useState({
    calories: '2000',
    protein: '150',
    carbs: '200',
    fat: '70',
    fiber: '25',
    enableTargets: true
  });
  
  // Cuisine preferences
  const [cuisinePreferences, setCuisinePreferences] = useState({
    preferred: ['Italian', 'Mediterranean'],
    disliked: ['Spicy']
  });
  
  // Cooking constraints
  const [cookingConstraints, setCookingConstraints] = useState({
    maxCookTime: '45',
    maxPrepTime: '15',
    maxIngredients: '10',
    difficultyLevel: 'intermediate',
    kitchenEquipment: ['Oven', 'Stovetop', 'Microwave']
  });

  const availableCuisines = [
    'Italian', 'Mexican', 'Chinese', 'Japanese', 'Indian', 'Thai', 'Mediterranean', 
    'French', 'American', 'Korean', 'Vietnamese', 'Greek', 'Middle Eastern', 
    'Spanish', 'Brazilian', 'German', 'British', 'African', 'Caribbean'
  ];

  const kitchenEquipmentOptions = [
    'Oven', 'Stovetop', 'Microwave', 'Air Fryer', 'Slow Cooker', 'Instant Pot',
    'Blender', 'Food Processor', 'Stand Mixer', 'Grill', 'Toaster Oven'
  ];

  const difficultyLevels = [
    { value: 'beginner', label: 'Beginner (10-15 min)' },
    { value: 'intermediate', label: 'Intermediate (20-45 min)' },
    { value: 'advanced', label: 'Advanced (45+ min)' }
  ];

  const handleDietaryRestrictionChange = (restriction) => {
    setDietaryRestrictions(prev => ({
      ...prev,
      [restriction]: !prev[restriction]
    }));
  };

  const handleCuisinePreference = (cuisine, type) => {
    setCuisinePreferences(prev => {
      const newPreferred = type === 'preferred' 
        ? (prev.preferred.includes(cuisine) 
          ? prev.preferred.filter(c => c !== cuisine)
          : [...prev.preferred, cuisine])
        : prev.preferred.filter(c => c !== cuisine);
      
      const newDisliked = type === 'disliked'
        ? (prev.disliked.includes(cuisine)
          ? prev.disliked.filter(c => c !== cuisine)
          : [...prev.disliked, cuisine])
        : prev.disliked.filter(c => c !== cuisine);

      return {
        preferred: newPreferred,
        disliked: newDisliked
      };
    });
  };

  const handleEquipmentChange = (equipment) => {
    setCookingConstraints(prev => ({
      ...prev,
      kitchenEquipment: prev.kitchenEquipment.includes(equipment)
        ? prev.kitchenEquipment.filter(e => e !== equipment)
        : [...prev.kitchenEquipment, equipment]
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    
    // Simulate save operation
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const preferenceData = {
      budget: budget.trim(),
      allergies: allergies.trim(),
      diet: diet,
      dietary_restrictions: dietaryRestrictions,
      macro_targets: macroTargets,
      cuisine_preferences: cuisinePreferences,
      cooking_constraints: cookingConstraints,
      updated_at: new Date().toISOString()
    };

    console.log('Saving advanced preferences:', preferenceData);
    alert('Advanced preferences saved successfully!');
    setSaving(false);
    
    // Navigate to home after saving
    navigate('/home');
  };

  const getActiveRestrictions = () => {
    return Object.entries(dietaryRestrictions)
      .filter(([_, active]) => active)
      .map(([key, _]) => key);
  };

  if (loading) {
    return (
      <div className="app-container">
        <div className="card">
          <p className="text-center">Loading preferences...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="card-large">
        {/* Header */}
        <div className="nav-header">
          <div>
            <h1>⚙️ Set your preferences</h1>
            <p className="subtitle">Customize your dietary restrictions, macro targets, and cooking preferences</p>
          </div>
          
          <div className="nav-buttons">
            <button 
              onClick={() => navigate('/home')}
              className="btn-secondary btn-sm"
            >
              🏠 Home
            </button>
          </div>
        </div>

        {/* Basic Preferences Section */}
        <div className="recipe-card mb-4">
          <h3 className="mb-3">💰 Basic Preferences</h3>
          
          <div className="flex gap-3 mb-3" style={{ flexDirection: 'column' }}>
            <div className="form-group">
              <label>What is your budget range</label>
              <input
                type="text"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                placeholder="50-100"
              />
            </div>
            
            <div className="form-group">
              <label>Enter any allergies or foods you want to avoid</label>
              <input
                type="text"
                value={allergies}
                onChange={(e) => setAllergies(e.target.value)}
                placeholder="Shellfish, Eggs, Soy"
              />
            </div>

            <div className="form-group">
              <label>Is there a particular diet you want to follow</label>
              <select
                value={diet}
                onChange={(e) => setDiet(e.target.value)}
              >
                <option value="">Select...</option>
                <option value="balanced">Balanced</option>
                <option value="low-carb">Low Carb</option>
                <option value="high-protein">High Protein</option>
                <option value="mediterranean">Mediterranean</option>
                <option value="plant-based">Plant Based</option>
              </select>
            </div>
          </div>
        </div>

        {/* Dietary Restrictions Section */}
        <div className="recipe-card mb-4">
          <h3 className="mb-3">🥗 Dietary Restrictions</h3>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: '12px' 
          }}>
            {Object.entries({
              glutenFree: 'Gluten-Free',
              dairyFree: 'Dairy-Free', 
              nutFree: 'Nut-Free',
              lowSodium: 'Low Sodium',
              lowSugar: 'Low Sugar',
              lowFat: 'Low Fat',
              highProtein: 'High Protein',
              vegetarian: 'Vegetarian',
              vegan: 'Vegan',
              keto: 'Keto',
              paleo: 'Paleo',
              wholeFoods: 'Whole Foods Only'
            }).map(([key, label]) => (
              <label key={key} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                padding: '12px', 
                backgroundColor: dietaryRestrictions[key] ? '#e3f2fd' : '#f8f9fa',
                borderRadius: '8px',
                border: `2px solid ${dietaryRestrictions[key] ? '#007bff' : '#e9ecef'}`,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}>
                <input
                  type="checkbox"
                  checked={dietaryRestrictions[key]}
                  onChange={() => handleDietaryRestrictionChange(key)}
                  style={{ marginRight: '8px' }}
                />
                <span style={{ fontWeight: '500' }}>{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Macro Targets Section */}
        <div className="recipe-card mb-4">
          <div className="flex align-center mb-3">
            <h3 style={{ margin: '0 16px 0 0' }}>🎯 Macro Targets</h3>
            <label style={{ 
              display: 'flex', 
              alignItems: 'center', 
              cursor: 'pointer',
              margin: 0 
            }}>
              <input
                type="checkbox"
                checked={macroTargets.enableTargets}
                onChange={(e) => setMacroTargets(prev => ({ ...prev, enableTargets: e.target.checked }))}
                style={{ marginRight: '8px' }}
              />
              <span>Enable macro tracking</span>
            </label>
          </div>
          
          {macroTargets.enableTargets && (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
              gap: '16px' 
            }}>
              {[
                { key: 'calories', label: 'Calories', placeholder: 'e.g. 2000' },
                { key: 'protein', label: 'Protein (g)', placeholder: 'e.g. 150' },
                { key: 'carbs', label: 'Carbs (g)', placeholder: 'e.g. 200' },
                { key: 'fat', label: 'Fat (g)', placeholder: 'e.g. 70' },
                { key: 'fiber', label: 'Fiber (g)', placeholder: 'e.g. 25' }
              ].map(({ key, label, placeholder }) => (
                <div key={key} className="form-group">
                  <label style={{ fontSize: '0.9rem' }}>{label}</label>
                  <input
                    type="number"
                    value={macroTargets[key]}
                    onChange={(e) => setMacroTargets(prev => ({ ...prev, [key]: e.target.value }))}
                    placeholder={placeholder}
                  />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cuisine Preferences Section */}
        <div className="recipe-card mb-4">
          <h3 className="mb-3">🌍 Cuisine Preferences</h3>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
            gap: '8px' 
          }}>
            {availableCuisines.map(cuisine => {
              const isPreferred = cuisinePreferences.preferred.includes(cuisine);
              const isDisliked = cuisinePreferences.disliked.includes(cuisine);
              
              return (
                <div key={cuisine} style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  alignItems: 'center',
                  padding: '12px',
                  backgroundColor: isPreferred ? '#e8f5e8' : isDisliked ? '#ffebee' : '#f8f9fa',
                  borderRadius: '8px',
                  border: `2px solid ${isPreferred ? '#28a745' : isDisliked ? '#dc3545' : '#e9ecef'}`
                }}>
                  <span style={{ 
                    fontSize: '0.875rem', 
                    fontWeight: '600', 
                    marginBottom: '8px',
                    textAlign: 'center'
                  }}>
                    {cuisine}
                  </span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleCuisinePreference(cuisine, 'preferred')}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: isPreferred ? '#28a745' : '#e9ecef',
                        color: isPreferred ? 'white' : '#495057',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        minHeight: 'auto'
                      }}
                    >
                      👍
                    </button>
                    <button
                      onClick={() => handleCuisinePreference(cuisine, 'disliked')}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: isDisliked ? '#dc3545' : '#e9ecef',
                        color: isDisliked ? 'white' : '#495057',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        minHeight: 'auto'
                      }}
                    >
                      👎
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Cooking Constraints Section */}
        <div className="recipe-card mb-4">
          <h3 className="mb-3">⏱️ Cooking Constraints</h3>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
            gap: '16px', 
            marginBottom: '20px' 
          }}>
            <div className="form-group">
              <label>Max Cooking Time (minutes)</label>
              <input
                type="number"
                value={cookingConstraints.maxCookTime}
                onChange={(e) => setCookingConstraints(prev => ({ ...prev, maxCookTime: e.target.value }))}
                placeholder="e.g. 45"
              />
            </div>
            
            <div className="form-group">
              <label>Max Prep Time (minutes)</label>
              <input
                type="number"
                value={cookingConstraints.maxPrepTime}
                onChange={(e) => setCookingConstraints(prev => ({ ...prev, maxPrepTime: e.target.value }))}
                placeholder="e.g. 15"
              />
            </div>
            
            <div className="form-group">
              <label>Max Ingredients</label>
              <input
                type="number"
                value={cookingConstraints.maxIngredients}
                onChange={(e) => setCookingConstraints(prev => ({ ...prev, maxIngredients: e.target.value }))}
                placeholder="e.g. 10"
              />
            </div>
            
            <div className="form-group">
              <label>Difficulty Level</label>
              <select
                value={cookingConstraints.difficultyLevel}
                onChange={(e) => setCookingConstraints(prev => ({ ...prev, difficultyLevel: e.target.value }))}
              >
                <option value="">Any difficulty</option>
                {difficultyLevels.map(level => (
                  <option key={level.value} value={level.value}>{level.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Available Kitchen Equipment</label>
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
              gap: '8px',
              marginTop: '8px'
            }}>
              {kitchenEquipmentOptions.map(equipment => (
                <label key={equipment} style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  padding: '8px', 
                  backgroundColor: cookingConstraints.kitchenEquipment.includes(equipment) ? '#e3f2fd' : '#f8f9fa',
                  borderRadius: '6px',
                  border: `2px solid ${cookingConstraints.kitchenEquipment.includes(equipment) ? '#007bff' : '#e9ecef'}`,
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}>
                  <input
                    type="checkbox"
                    checked={cookingConstraints.kitchenEquipment.includes(equipment)}
                    onChange={() => handleEquipmentChange(equipment)}
                    style={{ marginRight: '8px' }}
                  />
                  {equipment}
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2 justify-center">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary"
            style={{ width: 'auto', minWidth: '200px' }}
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
          
          <button
            onClick={() => navigate('/home')}
            className="btn-secondary"
            style={{ width: 'auto', minWidth: '120px' }}
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}