// src/pages/Preferences.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../services/supabase'

export default function Preferences() {
  const [budget, setBudget] = useState('')
  const [allergies, setAllergies] = useState('')
  const [diet, setDiet] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [user, setUser] = useState(null)
  const navigate = useNavigate()

  // Check authentication and load preferences
  useEffect(() => {
    const checkUserAndLoadPreferences = async () => {
      setLoading(true)
      
      const { data: { user }, error: userError } = await supabase.auth.getUser()
      
      if (userError || !user) {
        console.log('No authenticated user, redirecting to sign in')
        navigate('/')
        return
      }

      setUser(user)

      // Load existing preferences
      const { data: preferences, error: prefsError } = await supabase
        .from('user_preferences')
        .select('*')
        .eq('user_id', user.id)
        .single()

      if (prefsError && prefsError.code !== 'PGRST116') {
        console.error('Error loading preferences:', prefsError)
      } else if (preferences) {
        setBudget(preferences.budget || '')
        setAllergies(preferences.allergies || '')
        setDiet(preferences.diet || '')
      }

      setLoading(false)
    }

    checkUserAndLoadPreferences()
  }, [navigate])

  const handleSave = async () => {
    if (!user) return

    setSaving(true)
    
    const preferenceData = {
      user_id: user.id,
      budget: budget.trim(),
      allergies: allergies.trim(),
      diet: diet
    }

    const { error } = await supabase
      .from('user_preferences')
      .upsert(preferenceData)

    if (error) {
      console.error('Error saving preferences:', error)
      alert('Failed to save preferences: ' + error.message)
    } else {
      alert('Preferences saved successfully!')
      // Navigate to grocery list after saving
      navigate('/grocery')
    }
    
    setSaving(false)
  }

  const handleSignOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) {
      console.error('Error signing out:', error)
    } else {
      navigate('/')
    }
  }

  if (loading) {
    return (
      <div className="card">
        <p>Loading preferences...</p>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="header">
        <button className="back-button" onClick={() => navigate('/')}>
          ←
        </button>
        <h2>Set your preferences</h2>
        <button className="sign-out-btn" onClick={handleSignOut}>
          Sign Out
        </button>
      </div>

      <div className="form-group">
        <label htmlFor="budget">What is your budget range?</label>
        <input
          id="budget"
          type="text"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
          placeholder="e.g. $50-$100"
          disabled={saving}
        />
      </div>

      <div className="form-group">
        <label htmlFor="allergies">
          Enter any allergies or foods you want to avoid
        </label>
        <input
          id="allergies"
          type="text"
          value={allergies}
          onChange={(e) => setAllergies(e.target.value)}
          placeholder="Shellfish, Eggs, Soy"
          disabled={saving}
        />
      </div>

      <div className="form-group">
        <label htmlFor="diet">
          Is there a particular diet you want to follow?
        </label>
        <select
          id="diet"
          value={diet}
          onChange={(e) => setDiet(e.target.value)}
          disabled={saving}
        >
          <option value="">Select...</option>
          <option value="vegan">Vegan</option>
          <option value="keto">Keto</option>
          <option value="paleo">Paleo</option>
          <option value="mediterranean">Mediterranean</option>
          <option value="vegetarian">Vegetarian</option>
        </select>


      </div>

      <button 
        className="primary" 
        onClick={handleSave} 
        disabled={saving}
      >
        {saving ? 'Saving...' : 'Save Preferences'}
      </button>

      <button 
        className="secondary" 
        onClick={() => navigate('/grocery')}
        style={{ marginTop: '8px' }}
      >
        Skip to Grocery List
      </button>
    </div>
  )
}