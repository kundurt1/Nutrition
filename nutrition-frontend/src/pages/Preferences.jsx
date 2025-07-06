import { useState, useEffect } from 'react';

export default function AdvancedPreferences() {
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
  };

  const getActiveRestrictions = () => {
    return Object.entries(dietaryRestrictions)
      .filter(([_, active]) => active)
      .map(([key, _]) => key);
  };

  const getPreferencesSummary = () => {
    const activeRestrictions = getActiveRestrictions();
    return {
      restrictions: activeRestrictions.length,
      preferred_cuisines: cuisinePreferences.preferred.length,
      macro_tracking: macroTargets.enableTargets,
      max_cook_time: cookingConstraints.maxCookTime || 'No limit'
    };
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <p>Loading preferences...</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'system-ui, sans-serif' }}>
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
          <h1 style={{ margin: '0 0 8px 0', color: '#333' }}>⚙️ Advanced Preferences</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '16px' }}>
            Customize your dietary restrictions, macro targets, and cooking preferences
          </p>
        </div>
        <div style={{ 
          padding: '12px 16px', 
          backgroundColor: '#e3f2fd', 
          borderRadius: '8px',
          fontSize: '14px',
          color: '#1976d2'
        }}>
          <div><strong>{getPreferencesSummary().restrictions}</strong> active restrictions</div>
          <div><strong>{getPreferencesSummary().preferred_cuisines}</strong> preferred cuisines</div>
        </div>
      </div>

      {/* Basic Preferences Section */}
      <div style={{ marginBottom: '32px', padding: '20px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '20px' }}>💰 Basic Preferences</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Budget Range (per recipe)
            </label>
            <input
              type="text"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="e.g. $15-25"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Primary Diet Type
            </label>
            <select
              value={diet}
              onChange={(e) => setDiet(e.target.value)}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
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
        
        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Allergies & Foods to Avoid
          </label>
          <input
            type="text"
            value={allergies}
            onChange={(e) => setAllergies(e.target.value)}
            placeholder="e.g. Shellfish, Eggs, Soy, Peanuts"
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
          />
        </div>
      </div>

      {/* Dietary Restrictions Section */}
      <div style={{ marginBottom: '32px', padding: '20px', backgroundColor: '#f0f8ff', borderRadius: '8px' }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '20px' }}>🥗 Dietary Restrictions</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
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
              padding: '8px', 
              backgroundColor: dietaryRestrictions[key] ? '#e3f2fd' : '#fff',
              borderRadius: '4px',
              border: '1px solid #ddd',
              cursor: 'pointer'
            }}>
              <input
                type="checkbox"
                checked={dietaryRestrictions[key]}
                onChange={() => handleDietaryRestrictionChange(key)}
                style={{ marginRight: '8px' }}
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {/* Macro Targets Section */}
      <div style={{ marginBottom: '32px', padding: '20px', backgroundColor: '#f0fff0', borderRadius: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '16px' }}>
          <h2 style={{ margin: '0 16px 0 0', color: '#333', fontSize: '20px' }}>🎯 Macro Targets</h2>
          <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={macroTargets.enableTargets}
              onChange={(e) => setMacroTargets(prev => ({ ...prev, enableTargets: e.target.checked }))}
              style={{ marginRight: '8px' }}
            />
            Enable macro tracking
          </label>
        </div>
        
        {macroTargets.enableTargets && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
            {[
              { key: 'calories', label: 'Calories', placeholder: 'e.g. 2000' },
              { key: 'protein', label: 'Protein (g)', placeholder: 'e.g. 150' },
              { key: 'carbs', label: 'Carbs (g)', placeholder: 'e.g. 200' },
              { key: 'fat', label: 'Fat (g)', placeholder: 'e.g. 70' },
              { key: 'fiber', label: 'Fiber (g)', placeholder: 'e.g. 25' }
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold', fontSize: '14px' }}>
                  {label}
                </label>
                <input
                  type="number"
                  value={macroTargets[key]}
                  onChange={(e) => setMacroTargets(prev => ({ ...prev, [key]: e.target.value }))}
                  placeholder={placeholder}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Cuisine Preferences Section */}
      <div style={{ marginBottom: '32px', padding: '20px', backgroundColor: '#fff8f0', borderRadius: '8px' }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '20px' }}>🌍 Cuisine Preferences</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '8px' }}>
          {availableCuisines.map(cuisine => {
            const isPreferred = cuisinePreferences.preferred.includes(cuisine);
            const isDisliked = cuisinePreferences.disliked.includes(cuisine);
            
            return (
              <div key={cuisine} style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                padding: '8px',
                backgroundColor: isPreferred ? '#e8f5e8' : isDisliked ? '#ffebee' : '#fff',
                borderRadius: '4px',
                border: '1px solid #ddd'
              }}>
                <span style={{ fontSize: '12px', fontWeight: 'bold', marginBottom: '4px' }}>{cuisine}</span>
                <div style={{ display: 'flex', gap: '4px' }}>
                  <button
                    onClick={() => handleCuisinePreference(cuisine, 'preferred')}
                    style={{
                      padding: '2px 6px',
                      backgroundColor: isPreferred ? '#4CAF50' : '#f0f0f0',
                      color: isPreferred ? 'white' : '#333',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '10px'
                    }}
                  >
                    👍
                  </button>
                  <button
                    onClick={() => handleCuisinePreference(cuisine, 'disliked')}
                    style={{
                      padding: '2px 6px',
                      backgroundColor: isDisliked ? '#f44336' : '#f0f0f0',
                      color: isDisliked ? 'white' : '#333',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer',
                      fontSize: '10px'
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
      <div style={{ marginBottom: '32px', padding: '20px', backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
        <h2 style={{ margin: '0 0 16px 0', color: '#333', fontSize: '20px' }}>⏱️ Cooking Constraints</h2>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
              Max Cooking Time (minutes)
            </label>
            <input
              type="number"
              value={cookingConstraints.maxCookTime}
              onChange={(e) => setCookingConstraints(prev => ({ ...prev, maxCookTime: e.target.value }))}
              placeholder="e.g. 45"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
              Max Prep Time (minutes)
            </label>
            <input
              type="number"
              value={cookingConstraints.maxPrepTime}
              onChange={(e) => setCookingConstraints(prev => ({ ...prev, maxPrepTime: e.target.value }))}
              placeholder="e.g. 15"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
              Max Ingredients
            </label>
            <input
              type="number"
              value={cookingConstraints.maxIngredients}
              onChange={(e) => setCookingConstraints(prev => ({ ...prev, maxIngredients: e.target.value }))}
              placeholder="e.g. 10"
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
              Difficulty Level
            </label>
            <select
              value={cookingConstraints.difficultyLevel}
              onChange={(e) => setCookingConstraints(prev => ({ ...prev, difficultyLevel: e.target.value }))}
              style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
            >
              <option value="">Any difficulty</option>
              {difficultyLevels.map(level => (
                <option key={level.value} value={level.value}>{level.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
            Available Kitchen Equipment
          </label>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px' }}>
            {kitchenEquipmentOptions.map(equipment => (
              <label key={equipment} style={{ 
                display: 'flex', 
                alignItems: 'center', 
                padding: '6px', 
                backgroundColor: cookingConstraints.kitchenEquipment.includes(equipment) ? '#e3f2fd' : '#fff',
                borderRadius: '4px',
                border: '1px solid #ddd',
                cursor: 'pointer'
              }}>
                <input
                  type="checkbox"
                  checked={cookingConstraints.kitchenEquipment.includes(equipment)}
                  onChange={() => handleEquipmentChange(equipment)}
                  style={{ marginRight: '6px' }}
                />
                {equipment}
              </label>
            ))}
          </div>
        </div>
      </div>

      {/* Preferences Summary */}
      <div style={{ marginBottom: '32px', padding: '20px', backgroundColor: '#f0f4ff', borderRadius: '8px', border: '2px solid #2196F3' }}>
        <h3 style={{ margin: '0 0 12px 0', color: '#1976d2' }}>📋 Your Preferences Summary</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '14px' }}>
          <div>
            <strong>Budget:</strong> ${budget} per recipe
          </div>
          <div>
            <strong>Active Restrictions:</strong> {getActiveRestrictions().length > 0 ? getActiveRestrictions().join(', ') : 'None'}
          </div>
          <div>
            <strong>Preferred Cuisines:</strong> {cuisinePreferences.preferred.length > 0 ? cuisinePreferences.preferred.join(', ') : 'None'}
          </div>
          <div>
            <strong>Max Cook Time:</strong> {cookingConstraints.maxCookTime || 'No limit'} minutes
          </div>
          {macroTargets.enableTargets && (
            <div>
              <strong>Daily Calories:</strong> {macroTargets.calories} kcal
            </div>
          )}
          <div>
            <strong>Kitchen Equipment:</strong> {cookingConstraints.kitchenEquipment.length} items selected
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
        <button
          onClick={handleSave}
          disabled={saving}
          style={{
            padding: '12px 24px',
            backgroundColor: saving ? '#ccc' : '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: saving ? 'not-allowed' : 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          {saving ? 'Saving...' : 'Save Advanced Preferences'}
        </button>
        
        <button
          onClick={() => {
            // Reset to defaults
            setDietaryRestrictions({
              glutenFree: false, dairyFree: false, nutFree: false, lowSodium: false,
              lowSugar: false, lowFat: false, highProtein: false, vegetarian: false,
              vegan: false, keto: false, paleo: false, wholeFoods: false
            });
            setMacroTargets({
              calories: '', protein: '', carbs: '', fat: '', fiber: '', enableTargets: false
            });
            setCuisinePreferences({ preferred: [], disliked: [] });
            setCookingConstraints({
              maxCookTime: '', maxPrepTime: '', maxIngredients: '',
              difficultyLevel: '', kitchenEquipment: []
            });
          }}
          style={{
            padding: '12px 24px',
            backgroundColor: '#FF9800',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Reset to Defaults
        </button>
        
        <button
          onClick={() => alert('Navigating back to home...')}
          style={{
            padding: '12px 24px',
            backgroundColor: '#9E9E9E',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}