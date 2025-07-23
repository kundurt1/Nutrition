// src/pages/GroceryList.jsx - Enhanced with Smart Grocery Management
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../services/supabase'

export default function GroceryList() {
  const [items, setItems] = useState([])
  const [input, setInput] = useState('')
  const [quantity, setQuantity] = useState('')
  const [unit, setUnit] = useState('')
  const [loading, setLoading] = useState(false)
  const [user, setUser] = useState(null)
  const navigate = useNavigate()

  // Smart grocery management state
  const [activeTab, setActiveTab] = useState('grocery-list') // grocery-list, pantry, smart-features
  const [pantryItems, setPantryItems] = useState([])
  const [pantryLoading, setPantryLoading] = useState(false)
  const [substitutionsLoading, setSubstitutionsLoading] = useState(false)
  const [optimizedView, setOptimizedView] = useState(false)
  const [organizedItems, setOrganizedItems] = useState({})
  const [analytics, setAnalytics] = useState({})
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategory, setFilterCategory] = useState('all')
  const [showPurchased, setShowPurchased] = useState(false)

  // Pantry management state
  const [showAddPantry, setShowAddPantry] = useState(false)
  const [pantryForm, setPantryForm] = useState({
    item_name: '',
    quantity: '',
    unit: '',
    category: 'Other',
    expiry_date: '',
    minimum_quantity: 1
  })

  // Smart substitutions state
  const [missingIngredients, setMissingIngredients] = useState([])
  const [substitutions, setSubstitutions] = useState({})
  const [showSubstitutions, setShowSubstitutions] = useState({})
  const [selectedRecipe, setSelectedRecipe] = useState(null)
  const [adaptedRecipe, setAdaptedRecipe] = useState(null)
  const [recipeIdeas, setRecipeIdeas] = useState([])
  const [showRecipeIdeas, setShowRecipeIdeas] = useState(false)

  // Common units for grocery items
  const units = [
    '', 'lbs', 'oz', 'kg', 'g', 'cups', 'tbsp', 'tsp', 'ml', 'l', 'qt', 'pt',
    'gal', 'pieces', 'slices', 'bunches', 'bags', 'boxes', 'cans', 'bottles',
    'jars', 'packages', 'loaves', 'dozen', 'head', 'bunch', 'cloves'
  ]

  // Food categorization database
  const foodCategories = {
    'Proteins': [
      'chicken', 'beef', 'pork', 'turkey', 'salmon', 'tuna', 'cod', 'shrimp', 'fish',
      'eggs', 'tofu', 'tempeh', 'beans', 'lentils', 'chickpeas', 'black beans',
      'kidney beans', 'pinto beans', 'navy beans', 'quinoa', 'nuts', 'almonds',
      'peanuts', 'walnuts', 'cashews', 'pistachios', 'protein powder', 'ham',
      'bacon', 'sausage', 'ground beef', 'ground turkey', 'chicken breast',
      'chicken thighs', 'steak', 'pork chops', 'lamb', 'duck', 'crab', 'lobster'
    ],
    'Produce': [
      'apples', 'bananas', 'oranges', 'grapes', 'strawberries', 'blueberries',
      'raspberries', 'blackberries', 'mango', 'pineapple', 'kiwi', 'peaches',
      'pears', 'plums', 'cherries', 'watermelon', 'cantaloupe', 'honeydew',
      'lettuce', 'spinach', 'kale', 'arugula', 'broccoli', 'cauliflower',
      'carrots', 'celery', 'onions', 'garlic', 'tomatoes', 'cucumbers',
      'bell peppers', 'jalapeños', 'mushrooms', 'zucchini', 'squash',
      'sweet potatoes', 'potatoes', 'avocados', 'lemons', 'limes',
      'ginger', 'cilantro', 'parsley', 'basil', 'mint', 'green beans',
      'asparagus', 'brussels sprouts', 'cabbage', 'corn', 'peas'
    ],
    'Grains and Carbs': [
      'bread', 'rice', 'pasta', 'noodles', 'quinoa', 'oats', 'oatmeal',
      'cereal', 'crackers', 'bagels', 'tortillas', 'wraps', 'pita',
      'couscous', 'barley', 'bulgur', 'brown rice', 'white rice',
      'whole wheat bread', 'sourdough', 'rye bread', 'rolls', 'buns',
      'spaghetti', 'penne', 'macaroni', 'lasagna sheets', 'ramen',
      'flour', 'cornmeal', 'pancake mix', 'muffin mix'
    ],
    'Dairy & Alternatives': [
      'milk', 'cheese', 'yogurt', 'butter', 'cream', 'sour cream',
      'cottage cheese', 'cream cheese', 'mozzarella', 'cheddar',
      'parmesan', 'swiss', 'feta', 'goat cheese', 'ricotta',
      'almond milk', 'soy milk', 'oat milk', 'coconut milk',
      'cashew milk', 'greek yogurt', 'heavy cream', 'half and half',
      'whipped cream', 'ice cream', 'frozen yogurt'
    ],
    'Pantry and Staples': [
      'olive oil', 'vegetable oil', 'coconut oil', 'vinegar', 'salt',
      'pepper', 'sugar', 'honey', 'maple syrup', 'vanilla', 'cinnamon',
      'paprika', 'cumin', 'oregano', 'thyme', 'rosemary', 'garlic powder',
      'onion powder', 'chili powder', 'cayenne', 'turmeric', 'ginger powder',
      'baking soda', 'baking powder', 'flour', 'cornstarch', 'yeast',
      'soy sauce', 'hot sauce', 'ketchup', 'mustard', 'mayonnaise',
      'ranch', 'bbq sauce', 'worcestershire', 'fish sauce', 'sesame oil',
      'peanut butter', 'jam', 'jelly', 'nutella', 'tea', 'coffee',
      'canned tomatoes', 'tomato paste', 'coconut milk', 'broth',
      'chicken broth', 'vegetable broth', 'beef broth'
    ],
    'Recipe Generated': [],
    'Frozen and Misc': [
      'frozen vegetables', 'frozen fruit', 'frozen pizza', 'ice cream',
      'frozen dinners', 'frozen chicken', 'frozen fish', 'frozen shrimp',
      'popsicles', 'ice', 'toilet paper', 'paper towels', 'dish soap',
      'laundry detergent', 'shampoo', 'conditioner', 'toothpaste',
      'deodorant', 'soap', 'cleaning supplies', 'trash bags',
      'aluminum foil', 'plastic wrap', 'parchment paper'
    ]
  }

  // Function to categorize an item
  const categorizeItem = (itemName) => {
    const lowerCaseItem = itemName.toLowerCase().trim()

    for (const [category, foods] of Object.entries(foodCategories)) {
      for (const food of foods) {
        if (lowerCaseItem.includes(food) || food.includes(lowerCaseItem)) {
          return category
        }
      }
    }

    return 'Uncategorized'
  }

  // Function to refresh items from database
  const fetchItems = async (userId) => {
    try {
      const response = await fetch(`http://localhost:8000/grocery-list/${userId}?include_purchased=${showPurchased}`)
      if (response.ok) {
        const data = await response.json()
        setAnalytics(data.analytics || {})
        return data.grocery_items || []
      }
    } catch (error) {
      console.error('Error fetching grocery items:', error)
    }
    return []
  }

  const fetchPantryItems = async (userId) => {
    try {
      setPantryLoading(true)
      const response = await fetch(`http://localhost:8000/pantry/${userId}`)
      if (response.ok) {
        const data = await response.json()
        setPantryItems(data.items || [])
        setAnalytics(prev => ({ ...prev, ...data.analytics }))
      }
    } catch (error) {
      console.error('Error fetching pantry items:', error)
    } finally {
      setPantryLoading(false)
    }
  }

  const loadOptimizedList = async () => {
    try {
      const response = await fetch(`http://localhost:8000/grocery-list/${user.id}/optimized`)
      if (response.ok) {
        const data = await response.json()
        setOrganizedItems(data.organized_items || {})
        setOptimizedView(true)
      }
    } catch (error) {
      console.error('Error loading optimized list:', error)
    }
  }

  // Check authentication and fetch items
  useEffect(() => {
    const checkUserAndFetchItems = async () => {
      setLoading(true)

      const { data: { user }, error: userError } = await supabase.auth.getUser()

      if (userError || !user) {
        console.log('No authenticated user, redirecting to sign in')
        navigate('/')
        return
      }

      setUser(user)
      const groceryItems = await fetchItems(user.id)
      setItems(groceryItems)
      await fetchPantryItems(user.id)
      setLoading(false)
    }

    checkUserAndFetchItems()
  }, [navigate, showPurchased])

  // Add effect to listen for real-time updates
  useEffect(() => {
    if (!user) return

    const channel = supabase
        .channel('grocery_items_changes')
        .on(
            'postgres_changes',
            {
              event: '*',
              schema: 'public',
              table: 'grocery_items',
              filter: `user_id=eq.${user.id}`
            },
            async (payload) => {
              console.log('Real-time update received:', payload)
              const updatedItems = await fetchItems(user.id)
              setItems(updatedItems)
            }
        )
        .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [user])

  const addItem = async () => {
    if (!input.trim() || !user) return

    setLoading(true)

    // Use the new smart grocery list endpoint
    try {
      const category = categorizeItem(input.trim())
      const payload = {
        user_id: user.id,
        grocery_items: [{
          item_name: input.trim(),
          quantity: parseFloat(quantity) || 1,
          category: category,
          estimated_cost: 0
        }]
      }

      const response = await fetch('http://localhost:8000/save-grocery-list', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()
        if (data.pantry_sufficient && data.pantry_sufficient.length > 0) {
          alert(`${input} is already available in your pantry!`)
        }

        const updatedItems = await fetchItems(user.id)
        setItems(updatedItems)
        setInput('')
        setQuantity('')
        setUnit('')
      }
    } catch (error) {
      console.error('Error adding item:', error)
      alert('Failed to add item')
    }

    setLoading(false)
  }

  const removeItem = async (id) => {
    setLoading(true)

    try {
      const response = await fetch(`http://localhost:8000/grocery-list/${id}?user_id=${user.id}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        const updatedItems = await fetchItems(user.id)
        setItems(updatedItems)
      }
    } catch (error) {
      console.error('Error removing item:', error)
      alert('Failed to remove item')
    }

    setLoading(false)
  }

  const togglePurchased = async (id, currentStatus) => {
    setLoading(true)

    try {
      const response = await fetch(`http://localhost:8000/grocery-list/${id}/purchase?user_id=${user.id}`, {
        method: 'PATCH'
      })

      if (response.ok) {
        const updatedItems = await fetchItems(user.id)
        setItems(updatedItems)
        await fetchPantryItems(user.id) // Refresh pantry as item might be added
      }
    } catch (error) {
      console.error('Error updating item:', error)
      alert('Failed to update item')
    }

    setLoading(false)
  }

  const clearPurchasedItems = async () => {
    if (!window.confirm('Clear all purchased items?')) return

    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/grocery-list/${user.id}/clear-purchased`, {
        method: 'DELETE'
      })

      if (response.ok) {
        const updatedItems = await fetchItems(user.id)
        setItems(updatedItems)
      }
    } catch (error) {
      console.error('Error clearing purchased items:', error)
    } finally {
      setLoading(false)
    }
  }

  // Smart grocery management functions
  const addPantryItem = async () => {
    if (!user || !pantryForm.item_name || !pantryForm.quantity) return

    try {
      setPantryLoading(true)
      const response = await fetch('http://localhost:8000/pantry/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          items: [{
            name: pantryForm.item_name,
            quantity: parseFloat(pantryForm.quantity),
            unit: pantryForm.unit,
            category: pantryForm.category,
            expiration_date: pantryForm.expiry_date || null,
            location: 'Pantry'
          }]
        })
      })

      if (response.ok) {
        await fetchPantryItems(user.id)
        setPantryForm({
          item_name: '',
          quantity: '',
          unit: '',
          category: 'Other',
          expiry_date: '',
          minimum_quantity: 1
        })
        setShowAddPantry(false)

        // Refresh grocery list to update pantry status
        const updatedItems = await fetchItems(user.id)
        setItems(updatedItems)
      }
    } catch (error) {
      console.error('Error adding pantry item:', error)
    } finally {
      setPantryLoading(false)
    }
  }

  const getSubstitutions = async (itemName) => {
    if (substitutions[itemName]) {
      setShowSubstitutions(prev => ({
        ...prev,
        [itemName]: !prev[itemName]
      }))
      return
    }

    setSubstitutionsLoading(true)
    try {
      const payload = {
        user_id: user.id,
        missing_ingredients: [itemName],
        dietary_restrictions: [],
        budget_preference: "medium"
      }

      const response = await fetch('http://localhost:8000/substitutions/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      if (response.ok) {
        const data = await response.json()
        setSubstitutions(prev => ({
          ...prev,
          [itemName]: data.substitutions || []
        }))
        setShowSubstitutions(prev => ({
          ...prev,
          [itemName]: true
        }))
      }
    } catch (error) {
      console.error('Error getting substitutions:', error)
    } finally {
      setSubstitutionsLoading(false)
    }
  }

  const getRecipeIdeas = async () => {
    if (!user || pantryItems.length === 0) return

    try {
      setSubstitutionsLoading(true)
      // This would be a new endpoint for "what can I make" feature
      const pantryIngredients = pantryItems.map(item => item.name)
      alert(`Based on your pantry items: ${pantryIngredients.slice(0, 5).join(', ')}... you could make many delicious recipes! This feature is coming soon.`)
    } catch (error) {
      console.error('Error getting recipe ideas:', error)
    } finally {
      setSubstitutionsLoading(false)
    }
  }

  // Helper function to check if ingredient is available in pantry
  const isInPantry = (ingredientName) => {
    return pantryItems.some(item =>
        item.name.toLowerCase().includes(ingredientName.toLowerCase()) ||
        ingredientName.toLowerCase().includes(item.name.toLowerCase())
    )
  }

  // Get pantry summary stats
  const pantryStats = {
    totalItems: pantryItems.length,
    lowStock: pantryItems.filter(item =>
        parseFloat(item.quantity || 0) <= 1
    ).length,
    expiringSoon: pantryItems.filter(item => {
      if (!item.expiration_date) return false
      const expiryDate = new Date(item.expiration_date)
      const today = new Date()
      const daysDiff = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24))
      return daysDiff <= 7 && daysDiff >= 0
    }).length
  }

  // Filter and search functionality
  const filteredItems = items.filter(item => {
    const matchesSearch = item.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.item_name?.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesCategory = filterCategory === 'all' || item.category === filterCategory
    return matchesSearch && matchesCategory
  })

  // Group items by category
  const groupedItems = filteredItems.reduce((acc, item) => {
    const category = item.category || 'Uncategorized'
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(item)
    return acc
  }, {})

  const categories = [
    'Recipe Generated',
    'Proteins',
    'Produce',
    'Grains and Carbs',
    'Dairy & Alternatives',
    'Pantry and Staples',
    'Frozen and Misc'
  ]

  if (loading && !user) {
    return (
        <div className="app-container">
          <div className="card">
            <p className="text-center">Loading...</p>
          </div>
        </div>
    )
  }

  const totalItems = items.length
  const purchasedItems = items.filter(item => item.is_purchased).length
  const unpurchasedItems = totalItems - purchasedItems
  const totalCost = items.reduce((sum, item) => sum + (parseFloat(item.estimated_cost) || 0), 0)
  const itemsInPantry = items.filter(item => item.in_pantry).length

  return (
      <div className="app-container">
        <div className="card-full">
          {/* Header */}
          <div className="nav-header">
            <div>
              <h1 style={{ textAlign: 'left' }}>Smart Grocery Management</h1>
              <p className="subtitle" style={{ textAlign: 'left', marginBottom: 0 }}>
                AI-powered shopping with pantry tracking and smart substitutions
              </p>
            </div>

            <div className="nav-buttons">
              <button
                  onClick={() => navigate('/home')}
                  className="btn-secondary btn-sm"
              >
                🏠 Home
              </button>
              <button
                  onClick={() => navigate('/generate')}
                  className="btn-secondary btn-sm"
              >
                ← Generate
              </button>
            </div>
          </div>

          {/* Enhanced Analytics Dashboard */}
          {totalItems > 0 && (
              <div className="recipe-card mb-4">
                <h3 style={{ marginBottom: '16px' }}>📊 Smart Analytics</h3>
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                  gap: '16px',
                  marginBottom: '16px'
                }}>
                  <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#e3f2fd', borderRadius: '8px' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#1976d2' }}>{unpurchasedItems}</div>
                    <div style={{ fontSize: '0.75rem', color: '#666' }}>To Buy</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#e8f5e8', borderRadius: '8px' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#388e3c' }}>{purchasedItems}</div>
                    <div style={{ fontSize: '0.75rem', color: '#666' }}>Purchased</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#f3e5f5', borderRadius: '8px' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#7b1fa2' }}>${totalCost.toFixed(2)}</div>
                    <div style={{ fontSize: '0.75rem', color: '#666' }}>Est. Cost</div>
                  </div>
                  <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff3e0', borderRadius: '8px' }}>
                    <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#f57c00' }}>{itemsInPantry}</div>
                    <div style={{ fontSize: '0.75rem', color: '#666' }}>In Pantry</div>
                  </div>
                  {analytics.expiring_analysis && (
                      <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#ffebee', borderRadius: '8px' }}>
                        <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#d32f2f' }}>
                          {analytics.expiring_analysis.expired_or_expiring_today?.length || 0}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#666' }}>Expiring</div>
                      </div>
                  )}
                </div>
              </div>
          )}

          {/* Tab Navigation */}
          <div style={{
            display: 'flex',
            gap: '8px',
            marginBottom: '24px',
            borderBottom: '2px solid #f8f9fa',
            paddingBottom: '16px'
          }}>
            <button
                onClick={() => setActiveTab('grocery-list')}
                className={activeTab === 'grocery-list' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              🛒 Shopping List ({unpurchasedItems})
            </button>
            <button
                onClick={() => setActiveTab('pantry')}
                className={activeTab === 'pantry' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              📦 Pantry ({pantryItems.length})
            </button>
            <button
                onClick={() => setActiveTab('smart-features')}
                className={activeTab === 'smart-features' ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              🧠 Smart Features
            </button>
          </div>

          {/* Grocery List Tab */}
          {activeTab === 'grocery-list' && (
              <>
                {/* Add New Item */}
                <div className="recipe-card mb-4">
                  <h3 style={{ marginBottom: '16px' }}>➕ Add New Item</h3>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '2fr 1fr 1fr 1fr',
                    gap: '12px',
                    alignItems: 'end'
                  }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Item Name
                      </label>
                      <input
                          type="text"
                          value={input}
                          onChange={(e) => setInput(e.target.value)}
                          onKeyPress={(e) => e.key === 'Enter' && addItem()}
                          placeholder="What do you need?"
                          className="form-input"
                          style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Quantity
                      </label>
                      <input
                          type="number"
                          value={quantity}
                          onChange={(e) => setQuantity(e.target.value)}
                          placeholder="1"
                          min="0"
                          step="0.1"
                          className="form-input"
                          style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Unit
                      </label>
                      <select
                          value={unit}
                          onChange={(e) => setUnit(e.target.value)}
                          className="form-input"
                          style={{ width: '100%' }}
                      >
                        {units.map(u => (
                            <option key={u} value={u}>{u || 'pieces'}</option>
                        ))}
                      </select>
                    </div>
                    <button
                        onClick={addItem}
                        disabled={loading || !input.trim()}
                        className="btn-primary"
                        style={{ alignSelf: 'end' }}
                    >
                      {loading ? 'Adding...' : 'Add Item'}
                    </button>
                  </div>
                </div>

                {/* Search and Filter */}
                {items.length > 0 && (
                    <div className="recipe-card mb-4">
                      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: '12px' }}>
                        <div style={{ position: 'relative' }}>
                          <input
                              type="text"
                              placeholder="🔍 Search items..."
                              value={searchTerm}
                              onChange={(e) => setSearchTerm(e.target.value)}
                              className="form-input"
                              style={{ width: '100%' }}
                          />
                        </div>
                        <select
                            value={filterCategory}
                            onChange={(e) => setFilterCategory(e.target.value)}
                            className="form-input"
                        >
                          <option value="all">All Categories</option>
                          {categories.map(cat => (
                              <option key={cat} value={cat}>{cat}</option>
                          ))}
                        </select>
                        <button
                            onClick={() => setShowPurchased(!showPurchased)}
                            className={showPurchased ? 'btn-primary btn-sm' : 'btn-secondary btn-sm'}
                        >
                          {showPurchased ? '👁️ Hide Purchased' : '👁️ Show Purchased'}
                        </button>
                        <button
                            onClick={loadOptimizedList}
                            className="btn-secondary btn-sm"
                        >
                          ⚡ Optimize Route
                        </button>
                      </div>
                    </div>
                )}

                {/* Smart Actions */}
                {totalItems > 0 && (
                    <div className="recipe-card mb-4">
                      <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
                        ✨ Smart Actions
                      </h3>
                      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                        {purchasedItems > 0 && (
                            <button
                                onClick={clearPurchasedItems}
                                className="btn-secondary btn-sm"
                                disabled={loading}
                            >
                              🗑️ Clear Purchased Items
                            </button>
                        )}
                        <button
                            onClick={getRecipeIdeas}
                            disabled={substitutionsLoading || pantryItems.length === 0}
                            className="btn-secondary btn-sm"
                        >
                          💡 {substitutionsLoading ? 'Loading...' : 'What Can I Make?'}
                        </button>
                      </div>
                    </div>
                )}

                {/* Optimized Shopping Route View */}
                {optimizedView ? (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'between', alignItems: 'center', marginBottom: '16px' }}>
                        <h3>🛒 Optimized Shopping Route</h3>
                        <button
                            onClick={() => setOptimizedView(false)}
                            className="btn-secondary btn-sm"
                        >
                          ← Back to Categories
                        </button>
                      </div>

                      {Object.entries(organizedItems).map(([category, categoryItems]) => (
                          <div key={category} className="recipe-card mb-3">
                            <div style={{
                              padding: '16px',
                              backgroundColor: '#f8f9fa',
                              borderBottom: '1px solid #e9ecef'
                            }}>
                              <h4 style={{ margin: 0, fontSize: '1.125rem' }}>
                                🏪 {category} ({categoryItems.length} items)
                              </h4>
                            </div>
                            <div style={{ padding: '16px' }}>
                              {categoryItems.map((item) => (
                                  <GroceryItemRow
                                      key={item.id}
                                      item={item}
                                      onTogglePurchased={togglePurchased}
                                      onRemove={removeItem}
                                      onGetSubstitutions={getSubstitutions}
                                      substitutions={substitutions[item.name] || []}
                                      showSubstitutions={showSubstitutions[item.name] || false}
                                      loading={loading}
                                      isInPantry={isInPantry}
                                  />
                              ))}
                            </div>
                          </div>
                      ))}
                    </div>
                ) : (
                    /* Regular Category View */
                    <div>
                      {categories.map((category) => {
                        const categoryItems = groupedItems[category] || []
                        if (categoryItems.length === 0) return null

                        return (
                            <div key={category} className="recipe-card mb-3">
                              <div className="flex justify-between align-center mb-3">
                                <h3 style={{
                                  margin: 0,
                                  color: category === 'Recipe Generated' ? '#28a745' : '#333',
                                  fontSize: '1.125rem'
                                }}>
                                  {category === 'Recipe Generated' ? '🍳 From Recipes' :
                                      category === 'Proteins' ? '🥩 Proteins' :
                                          category === 'Produce' ? '🥬 Produce' :
                                              category === 'Grains and Carbs' ? '🌾 Grains & Carbs' :
                                                  category === 'Dairy & Alternatives' ? '🥛 Dairy' :
                                                      category === 'Pantry and Staples' ? '🏺 Pantry' :
                                                          category === 'Frozen and Misc' ? '❄️ Frozen' : category}
                                </h3>
                                <span style={{
                                  fontSize: '0.875rem',
                                  color: '#6c757d',
                                  backgroundColor: '#f8f9fa',
                                  padding: '4px 8px',
                                  borderRadius: '12px',
                                  fontWeight: '500'
                                }}>
                          {categoryItems.length} items
                        </span>
                              </div>

                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {categoryItems.map((item) => (
                                    <GroceryItemRow
                                        key={item.id}
                                        item={item}
                                        onTogglePurchased={togglePurchased}
                                        onRemove={removeItem}
                                        onGetSubstitutions={getSubstitutions}
                                        substitutions={substitutions[item.name] || []}
                                        showSubstitutions={showSubstitutions[item.name] || false}
                                        loading={loading}
                                        isInPantry={isInPantry}
                                    />
                                ))}
                              </div>
                            </div>
                        )
                      })}

                      {/* Uncategorized items */}
                      {groupedItems['Uncategorized'] && groupedItems['Uncategorized'].length > 0 && (
                          <div className="recipe-card mb-3">
                            <div className="flex justify-between align-center mb-3">
                              <h3 style={{ margin: 0, fontSize: '1.125rem' }}>📦 Other Items</h3>
                              <span style={{
                                fontSize: '0.875rem',
                                color: '#6c757d',
                                backgroundColor: '#f8f9fa',
                                padding: '4px 8px',
                                borderRadius: '12px',
                                fontWeight: '500'
                              }}>
                        {groupedItems['Uncategorized'].length} items
                      </span>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              {groupedItems['Uncategorized'].map((item) => (
                                  <GroceryItemRow
                                      key={item.id}
                                      item={item}
                                      onTogglePurchased={togglePurchased}
                                      onRemove={removeItem}
                                      onGetSubstitutions={getSubstitutions}
                                      substitutions={substitutions[item.name] || []}
                                      showSubstitutions={showSubstitutions[item.name] || false}
                                      loading={loading}
                                      isInPantry={isInPantry}
                                  />
                              ))}
                            </div>
                          </div>
                      )}
                    </div>
                )}

                {/* Empty State */}
                {filteredItems.length === 0 && items.length > 0 && (
                    <div className="recipe-card" style={{ textAlign: 'center', padding: '48px' }}>
                      <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🔍</div>
                      <h3>No items found</h3>
                      <p style={{ color: '#6c757d' }}>Try adjusting your search or filter criteria.</p>
                    </div>
                )}

                {items.length === 0 && (
                    <div className="recipe-card" style={{ textAlign: 'center', padding: '48px' }}>
                      <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🛒</div>
                      <h3>Your grocery list is empty</h3>
                      <p style={{ color: '#6c757d' }}>Add items above or generate from recipes to get started!</p>
                    </div>
                )}
              </>
          )}

          {/* Pantry Tab */}
          {activeTab === 'pantry' && (
              <>
                {/* Pantry Analytics */}
                {pantryItems.length > 0 && (
                    <div className="recipe-card mb-4">
                      <h3 style={{ marginBottom: '16px' }}>📊 Pantry Overview</h3>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                        gap: '16px'
                      }}>
                        <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#e3f2fd', borderRadius: '8px' }}>
                          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#1976d2' }}>{pantryStats.totalItems}</div>
                          <div style={{ fontSize: '0.75rem', color: '#666' }}>Total Items</div>
                        </div>
                        <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#fff3e0', borderRadius: '8px' }}>
                          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#f57c00' }}>{pantryStats.lowStock}</div>
                          <div style={{ fontSize: '0.75rem', color: '#666' }}>Low Stock</div>
                        </div>
                        <div style={{ textAlign: 'center', padding: '12px', backgroundColor: '#ffebee', borderRadius: '8px' }}>
                          <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#d32f2f' }}>{pantryStats.expiringSoon}</div>
                          <div style={{ fontSize: '0.75rem', color: '#666' }}>Expiring Soon</div>
                        </div>
                      </div>
                    </div>
                )}

                {/* Add Pantry Item */}
                <div className="recipe-card mb-4">
                  <h3 style={{ marginBottom: '16px' }}>➕ Add Pantry Item</h3>
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: '2fr 1fr 1fr 1fr 1fr',
                    gap: '12px',
                    alignItems: 'end'
                  }}>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Item Name
                      </label>
                      <input
                          type="text"
                          value={pantryForm.item_name}
                          onChange={(e) => setPantryForm(prev => ({...prev, item_name: e.target.value}))}
                          placeholder="What's in your pantry?"
                          className="form-input"
                          style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Quantity
                      </label>
                      <input
                          type="number"
                          value={pantryForm.quantity}
                          onChange={(e) => setPantryForm(prev => ({...prev, quantity: e.target.value}))}
                          placeholder="1"
                          min="0"
                          step="0.1"
                          className="form-input"
                          style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Unit
                      </label>
                      <select
                          value={pantryForm.unit}
                          onChange={(e) => setPantryForm(prev => ({...prev, unit: e.target.value}))}
                          className="form-input"
                          style={{ width: '100%' }}
                      >
                        {units.map(u => (
                            <option key={u} value={u}>{u || 'pieces'}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label style={{ display: 'block', marginBottom: '4px', fontSize: '0.875rem', fontWeight: '500' }}>
                        Expiry Date
                      </label>
                      <input
                          type="date"
                          value={pantryForm.expiry_date}
                          onChange={(e) => setPantryForm(prev => ({...prev, expiry_date: e.target.value}))}
                          className="form-input"
                          style={{ width: '100%' }}
                      />
                    </div>
                    <button
                        onClick={addPantryItem}
                        disabled={pantryLoading || !pantryForm.item_name.trim()}
                        className="btn-primary"
                        style={{ alignSelf: 'end' }}
                    >
                      {pantryLoading ? 'Adding...' : 'Add to Pantry'}
                    </button>
                  </div>
                </div>

                {/* Expiring Items Alert */}
                {analytics.expiring_analysis && analytics.expiring_analysis.expired_or_expiring_today.length > 0 && (
                    <div className="recipe-card mb-4" style={{ backgroundColor: '#fff3cd', border: '1px solid #ffeaa7' }}>
                      <h3 style={{ color: '#856404', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        ⚠️ Items Expiring Soon
                      </h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {analytics.expiring_analysis.expired_or_expiring_today.slice(0, 3).map((item, idx) => (
                            <div key={idx} style={{
                              padding: '8px 12px',
                              backgroundColor: '#fff',
                              borderRadius: '6px',
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center'
                            }}>
                              <span style={{ fontWeight: '500' }}>{item.name}</span>
                              <span style={{
                                color: item.days_remaining <= 0 ? '#dc3545' : '#f57c00',
                                fontSize: '0.875rem',
                                fontWeight: '500'
                              }}>
                        {item.days_remaining <= 0 ? 'Expired!' : `${item.days_remaining} days left`}
                      </span>
                            </div>
                        ))}
                      </div>
                    </div>
                )}

                {/* Pantry Items List */}
                <div className="recipe-card">
                  <h3 style={{ marginBottom: '16px' }}>📦 Pantry Inventory</h3>

                  {pantryLoading ? (
                      <div style={{ textAlign: 'center', padding: '24px' }}>
                        <p>Loading pantry items...</p>
                      </div>
                  ) : pantryItems.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {pantryItems.map((item) => (
                            <div key={item.id} style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '12px',
                              backgroundColor: '#f8f9fa',
                              border: '1px solid #e9ecef',
                              borderRadius: '8px'
                            }}>
                              <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: '500', marginBottom: '4px' }}>{item.name}</div>
                                <div style={{ fontSize: '0.875rem', color: '#6c757d', display: 'flex', gap: '16px' }}>
                                  <span>{item.quantity} {item.unit}</span>
                                  <span>📍 {item.location}</span>
                                  {item.expiration_date && (
                                      <span>📅 {new Date(item.expiration_date).toLocaleDateString()}</span>
                                  )}
                                </div>
                              </div>
                            </div>
                        ))}
                      </div>
                  ) : (
                      <div style={{ textAlign: 'center', padding: '48px' }}>
                        <div style={{ fontSize: '4rem', marginBottom: '16px' }}>📦</div>
                        <h4>Your pantry is empty</h4>
                        <p style={{ color: '#6c757d' }}>Add items above to start tracking your pantry inventory!</p>
                      </div>
                  )}
                </div>
              </>
          )}

          {/* Smart Features Tab */}
          {activeTab === 'smart-features' && (
              <>
                <div className="recipe-card mb-4">
                  <h3 style={{ marginBottom: '16px' }}>🧠 AI-Powered Smart Features</h3>
                  <p style={{ color: '#6c757d', marginBottom: '24px' }}>
                    Leverage AI to optimize your shopping experience with intelligent substitutions and recipe suggestions.
                  </p>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                    {/* Smart Substitutions */}
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '12px',
                      border: '1px solid #e9ecef'
                    }}>
                      <h4 style={{ color: '#495057', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        💡 Smart Substitutions
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '16px' }}>
                        Get AI-powered ingredient substitutions based on your dietary preferences and pantry contents.
                      </p>
                      <button
                          onClick={() => alert('Smart substitutions are available when you click the lightbulb icon next to any grocery item!')}
                          className="btn-secondary btn-sm"
                      >
                        Learn More
                      </button>
                    </div>

                    {/* Recipe Ideas */}
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '12px',
                      border: '1px solid #e9ecef'
                    }}>
                      <h4 style={{ color: '#495057', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        👨‍🍳 Recipe Suggestions
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '16px' }}>
                        Discover what you can make with ingredients you already have in your pantry.
                      </p>
                      <button
                          onClick={getRecipeIdeas}
                          disabled={substitutionsLoading || pantryItems.length === 0}
                          className="btn-primary btn-sm"
                      >
                        {substitutionsLoading ? 'Loading...' : 'What Can I Make?'}
                      </button>
                    </div>

                    {/* Shopping Optimization */}
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '12px',
                      border: '1px solid #e9ecef'
                    }}>
                      <h4 style={{ color: '#495057', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        🛤️ Shopping Route Optimization
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '16px' }}>
                        Optimize your shopping route based on store layout and category organization.
                      </p>
                      <button
                          onClick={loadOptimizedList}
                          disabled={items.length === 0}
                          className="btn-primary btn-sm"
                      >
                        Optimize My Route
                      </button>
                    </div>

                    {/* Pantry Integration */}
                    <div style={{
                      padding: '20px',
                      backgroundColor: '#f8f9fa',
                      borderRadius: '12px',
                      border: '1px solid #e9ecef'
                    }}>
                      <h4 style={{ color: '#495057', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                        📦 Pantry Intelligence
                      </h4>
                      <p style={{ fontSize: '0.875rem', color: '#6c757d', marginBottom: '16px' }}>
                        Automatically check what you already have before adding items to your grocery list.
                      </p>
                      <div style={{ fontSize: '0.875rem', color: '#28a745' }}>
                        ✅ Active - {itemsInPantry} items detected in pantry
                      </div>
                    </div>
                  </div>
                </div>

                {/* Usage Tips */}
                <div className="recipe-card">
                  <h3 style={{ marginBottom: '16px' }}>💡 Smart Shopping Tips</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'start', gap: '12px' }}>
                      <span style={{ fontSize: '1.2rem' }}>🔍</span>
                      <div>
                        <strong>Check Pantry First:</strong> Items already in your pantry are automatically flagged when adding to grocery list.
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'start', gap: '12px' }}>
                      <span style={{ fontSize: '1.2rem' }}>💡</span>
                      <div>
                        <strong>Smart Substitutions:</strong> Click the lightbulb icon next to any item for AI-powered substitution suggestions.
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'start', gap: '12px' }}>
                      <span style={{ fontSize: '1.2rem' }}>⚡</span>
                      <div>
                        <strong>Optimize Route:</strong> Use the "Optimize Route" button to organize your list by store layout.
                      </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'start', gap: '12px' }}>
                      <span style={{ fontSize: '1.2rem' }}>📅</span>
                      <div>
                        <strong>Track Expiry:</strong> Add expiration dates to pantry items to get alerts for items expiring soon.
                      </div>
                    </div>
                  </div>
                </div>
              </>
          )}
        </div>
      </div>
  )
}

// Grocery Item Row Component
const GroceryItemRow = ({
                          item,
                          onTogglePurchased,
                          onRemove,
                          onGetSubstitutions,
                          substitutions,
                          showSubstitutions,
                          loading,
                          isInPantry
                        }) => {
  return (
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '12px',
        backgroundColor: item.is_purchased ? '#f8f9fa' : '#fff',
        border: '2px solid #e9ecef',
        borderRadius: '8px',
        opacity: item.is_purchased ? 0.7 : 1,
        transition: 'all 0.2s ease'
      }}>
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: '1rem',
            color: '#333',
            fontWeight: '500',
            textDecoration: item.is_purchased ? 'line-through' : 'none',
            marginBottom: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            {item.name}
            {item.in_pantry && (
                <span style={{
                  fontSize: '0.75rem',
                  backgroundColor: '#d4edda',
                  color: '#155724',
                  padding: '2px 6px',
                  borderRadius: '12px',
                  fontWeight: 'normal'
                }}>
              📦 In Pantry
            </span>
            )}
          </div>
          <div style={{
            fontSize: '0.875rem',
            color: '#6c757d',
            display: 'flex',
            gap: '16px'
          }}>
            <span>{item.quantity} {item.unit}</span>
            {item.estimated_cost > 0 && (
                <span style={{ color: '#28a745', fontWeight: '500' }}>
              ${parseFloat(item.estimated_cost).toFixed(2)}
            </span>
            )}
            {item.pantry_quantity > 0 && (
                <span style={{ color: '#28a745' }}>
              📦 {item.pantry_quantity} available
            </span>
            )}
            {isInPantry(item.item_name || item.name) && (
                <span style={{ color: '#28a745' }}>
              ✅ Available in pantry
            </span>
            )}
          </div>

          {/* Substitution Suggestions */}
          {showSubstitutions && substitutions.length > 0 && (
              <div style={{
                marginTop: '12px',
                padding: '12px',
                backgroundColor: '#e3f2fd',
                borderRadius: '6px',
                border: '1px solid #bbdefb'
              }}>
                <h5 style={{
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  color: '#1565c0',
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }}>
                  💡 Smart Substitutions
                </h5>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                  {substitutions.slice(0, 2).map((sub, idx) => (
                      <div key={idx} style={{ fontSize: '0.8rem' }}>
                        <div style={{ fontWeight: '500', color: '#1565c0' }}>{sub.substitute_ingredient}</div>
                        <div style={{ color: '#1976d2' }}>{sub.conversion_notes}</div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                            <span style={{ color: '#ffa000' }}>⭐</span>
                            <span>{(sub.confidence_score * 100).toFixed(0)}%</span>
                          </div>
                          {sub.cost_impact && (
                              <span style={{
                                fontSize: '0.7rem',
                                padding: '1px 4px',
                                borderRadius: '8px',
                                backgroundColor: sub.cost_impact === 'lower' ? '#c8e6c9' :
                                    sub.cost_impact === 'higher' ? '#ffcdd2' : '#f5f5f5',
                                color: sub.cost_impact === 'lower' ? '#2e7d32' :
                                    sub.cost_impact === 'higher' ? '#c62828' : '#666'
                              }}>
                        {sub.cost_impact} cost
                      </span>
                          )}
                        </div>
                      </div>
                  ))}
                </div>
              </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '8px', marginLeft: '16px' }}>
          <button
              onClick={() => onGetSubstitutions(item.name || item.item_name)}
              style={{
                padding: '6px',
                backgroundColor: 'transparent',
                border: '1px solid #007bff',
                borderRadius: '6px',
                color: '#007bff',
                cursor: 'pointer',
                fontSize: '0.875rem'
              }}
              title="Get substitutions"
          >
            💡
          </button>
          <button
              onClick={() => onTogglePurchased(item.id, item.is_purchased)}
              disabled={loading}
              style={{
                padding: '8px 12px',
                backgroundColor: item.is_purchased ? '#28a745' : '#007bff',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.875rem',
                cursor: 'pointer',
                minHeight: '36px',
                fontWeight: '500'
              }}
          >
            {item.is_purchased ? '✓ Bought' : 'Buy'}
          </button>
          <button
              onClick={() => onRemove(item.id)}
              disabled={loading}
              style={{
                padding: '8px 12px',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                fontSize: '0.875rem',
                cursor: 'pointer',
                minHeight: '36px',
                fontWeight: '500'
              }}
          >
            Remove
          </button>
        </div>
      </div>
  )
}