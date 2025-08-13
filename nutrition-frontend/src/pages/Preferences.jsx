// src/pages/Preferences.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';

export default function Preferences() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userId, setUserId] = useState(null);

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

  useEffect(() => {
    const loadUserAndPreferences = async () => {
      try {
        // Get current user
        const { data: { user }, error: userError } = await supabase.auth.getUser();
        if (userError || !user) {
          console.error('Auth error:', userError);
          navigate('/signin');
          return;
        }

        // FIXED: Set userId here where user is defined
        setUserId(user.id);

        // Load user preferences
        const response = await fetch(`http://localhost:8000/get-preferences/${user.id}`);
        if (response.ok) {
          const data = await response.json();
          const prefs = data.preferences;

          // Update state with loaded preferences
          if (prefs.budget) setBudget(prefs.budget.toString());
          if (prefs.allergies) setAllergies(prefs.allergies);
          if (prefs.diet) setDiet(prefs.diet);

          if (prefs.dietary_restrictions) {
            setDietaryRestrictions(prev => ({
              ...prev,
              ...prefs.dietary_restrictions
            }));
          }

          if (prefs.macro_targets) {
            setMacroTargets(prev => ({
              ...prev,
              ...prefs.macro_targets,
              // Convert numbers to strings for input fields
              calories: prefs.macro_targets.calories?.toString() || '2000',
              protein: prefs.macro_targets.protein?.toString() || '150',
              carbs: prefs.macro_targets.carbs?.toString() || '200',
              fat: prefs.macro_targets.fat?.toString() || '70',
              fiber: prefs.macro_targets.fiber?.toString() || '25'
            }));
          }

          if (prefs.cuisine_preferences) {
            setCuisinePreferences(prefs.cuisine_preferences);
          }

          if (prefs.cooking_constraints) {
            setCookingConstraints(prev => ({
              ...prev,
              ...prefs.cooking_constraints,
              // Convert numbers to strings for input fields
              maxCookTime: prefs.cooking_constraints.maxCookTime?.toString() || '45',
              maxPrepTime: prefs.cooking_constraints.maxPrepTime?.toString() || '15',
              maxIngredients: prefs.cooking_constraints.maxIngredients?.toString() || '10'
            }));
          }

          console.log('Loaded preferences from database:', prefs);
        }
      } catch (error) {
        console.error('Error loading preferences:', error);
      } finally {
        setLoading(false);
      }
    };

    loadUserAndPreferences();
  }, [navigate]);

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
    if (!userId) {
      alert('Please sign in to save preferences');
      return;
    }

    setSaving(true);

    try {
      // Prepare preference data for backend
      const preferenceData = {
        user_id: userId,
        budget: budget.trim(),
        allergies: allergies.trim(),
        diet: diet,
        dietary_restrictions: dietaryRestrictions,
        macro_targets: {
          ...macroTargets,
          // Convert string values to numbers
          calories: parseInt(macroTargets.calories) || 2000,
          protein: parseInt(macroTargets.protein) || 150,
          carbs: parseInt(macroTargets.carbs) || 200,
          fat: parseInt(macroTargets.fat) || 70,
          fiber: parseInt(macroTargets.fiber) || 25
        },
        cuisine_preferences: cuisinePreferences,
        cooking_constraints: {
          ...cookingConstraints,
          // Convert string values to numbers
          maxCookTime: parseInt(cookingConstraints.maxCookTime) || 45,
          maxPrepTime: parseInt(cookingConstraints.maxPrepTime) || 15,
          maxIngredients: parseInt(cookingConstraints.maxIngredients) || 10
        }
      };

      console.log('Saving preferences to database:', preferenceData);

      // Save to backend
      const response = await fetch('http://localhost:8000/save-preferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(preferenceData)
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Preferences saved successfully:', result);
        alert('Preferences saved successfully!');

        // Navigate to home after saving
        navigate('/home');
      } else {
        const error = await response.json();
        console.error('Failed to save preferences:', error);
        alert('Failed to save preferences. Please try again.');
      }
    } catch (error) {
      console.error('Error saving preferences:', error);
      alert('An error occurred while saving preferences.');
    } finally {
      setSaving(false);
    }
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
                  <option value="keto">Keto</option>
                  <option value="paleo">Paleo</option>
                  <option value="vegetarian">Vegetarian</option>
                  <option value="vegan">Vegan</option>
                </select>
              </div>
            </div>
          </div>

          {/* Dietary Restrictions Section */}
          <div className="recipe-card mb-4">
            <h3 className="mb-3">🚫 Dietary Restrictions</h3>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '12px'
            }}>
              {Object.entries(dietaryRestrictions).map(([key, value]) => (
                  <label key={key} style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '12px',
                    backgroundColor: value ? '#e3f2fd' : '#f8f9fa',
                    borderRadius: '8px',
                    border: `2px solid ${value ? '#007bff' : '#e9ecef'}`,
                    cursor: 'pointer',
                    fontWeight: value ? '600' : '400'
                  }}>
                    <input
                        type="checkbox"
                        checked={value}
                        onChange={() => handleDietaryRestrictionChange(key)}
                        style={{ marginRight: '8px' }}
                    />
                    {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                  </label>
              ))}
            </div>
          </div>

          {/* Macro Targets Section */}
          <div className="recipe-card mb-4">
            <h3 className="mb-3">🎯 Macro Targets</h3>

            <div className="form-group" style={{ marginBottom: '16px' }}>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                fontSize: '1rem',
                fontWeight: '500'
              }}>
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
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                  gap: '16px'
                }}>
                  <div className="form-group">
                    <label>Calories</label>
                    <input
                        type="number"
                        value={macroTargets.calories}
                        onChange={(e) => setMacroTargets(prev => ({ ...prev, calories: e.target.value }))}
                        placeholder="2000"
                    />
                  </div>

                  <div className="form-group">
                    <label>Protein (g)</label>
                    <input
                        type="number"
                        value={macroTargets.protein}
                        onChange={(e) => setMacroTargets(prev => ({ ...prev, protein: e.target.value }))}
                        placeholder="150"
                    />
                  </div>

                  <div className="form-group">
                    <label>Carbs (g)</label>
                    <input
                        type="number"
                        value={macroTargets.carbs}
                        onChange={(e) => setMacroTargets(prev => ({ ...prev, carbs: e.target.value }))}
                        placeholder="200"
                    />
                  </div>

                  <div className="form-group">
                    <label>Fat (g)</label>
                    <input
                        type="number"
                        value={macroTargets.fat}
                        onChange={(e) => setMacroTargets(prev => ({ ...prev, fat: e.target.value }))}
                        placeholder="70"
                    />
                  </div>

                  <div className="form-group">
                    <label>Fiber (g)</label>
                    <input
                        type="number"
                        value={macroTargets.fiber}
                        onChange={(e) => setMacroTargets(prev => ({ ...prev, fiber: e.target.value }))}
                        placeholder="25"
                    />
                  </div>
                </div>
            )}
          </div>

          {/* Cuisine Preferences Section */}
          <div className="recipe-card mb-4">
            <h3 className="mb-3">🍽️ Cuisine Preferences</h3>

            <div style={{ marginBottom: '20px' }}>
              <h4 style={{ fontSize: '1rem', marginBottom: '12px', color: '#28a745' }}>
                ✅ Preferred Cuisines
              </h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '8px'
              }}>
                {availableCuisines.map(cuisine => (
                    <button
                        key={cuisine}
                        onClick={() => handleCuisinePreference(cuisine, 'preferred')}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: `2px solid ${cuisinePreferences.preferred.includes(cuisine) ? '#28a745' : '#e9ecef'}`,
                          backgroundColor: cuisinePreferences.preferred.includes(cuisine) ? '#d4edda' : '#f8f9fa',
                          color: cuisinePreferences.preferred.includes(cuisine) ? '#155724' : '#6c757d',
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: cuisinePreferences.preferred.includes(cuisine) ? '600' : '400'
                        }}
                    >
                      {cuisine}
                    </button>
                ))}
              </div>
            </div>

            <div>
              <h4 style={{ fontSize: '1rem', marginBottom: '12px', color: '#dc3545' }}>
                ❌ Disliked Cuisines
              </h4>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                gap: '8px'
              }}>
                {availableCuisines.map(cuisine => (
                    <button
                        key={cuisine}
                        onClick={() => handleCuisinePreference(cuisine, 'disliked')}
                        style={{
                          padding: '8px 12px',
                          borderRadius: '6px',
                          border: `2px solid ${cuisinePreferences.disliked.includes(cuisine) ? '#dc3545' : '#e9ecef'}`,
                          backgroundColor: cuisinePreferences.disliked.includes(cuisine) ? '#f8d7da' : '#f8f9fa',
                          color: cuisinePreferences.disliked.includes(cuisine) ? '#721c24' : '#6c757d',
                          cursor: 'pointer',
                          fontSize: '0.875rem',
                          fontWeight: cuisinePreferences.disliked.includes(cuisine) ? '600' : '400'
                        }}
                    >
                      {cuisine}
                    </button>
                ))}
              </div>
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
                <label>Max Cook Time (minutes)</label>
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