// src/pages/GroceryList.jsx
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
    const { data: groceryItems, error: itemsError } = await supabase
      .from('grocery_items')
      .select('*')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })

    if (itemsError) {
      console.error('Error fetching grocery items:', itemsError)
      return []
    } else {
      console.log('Fetched grocery items:', groceryItems)
      return groceryItems || []
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
      setLoading(false)
    }

    checkUserAndFetchItems()
  }, [navigate])

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
    
    const category = categorizeItem(input.trim())
    const newItem = {
      user_id: user.id,
      name: input.trim(),
      quantity: quantity.trim() || '1',
      unit: unit || '',
      category: category,
      item_name: input.trim(),
      estimated_cost: 0.0,
      is_purchased: false
    }
    
    const { data, error } = await supabase
      .from('grocery_items')
      .insert([newItem])
      .select()
      .single()

    if (error) {
      console.error('Error adding item:', error)
      alert('Failed to add item')
    } else {
      setItems([data, ...items])
      setInput('')
      setQuantity('')
      setUnit('')
    }
    
    setLoading(false)
  }

  const removeItem = async (id) => {
    setLoading(true)
    
    const { error } = await supabase
      .from('grocery_items')
      .delete()
      .eq('id', id)

    if (error) {
      console.error('Error removing item:', error)
      alert('Failed to remove item')
    } else {
      setItems(items.filter(item => item.id !== id))
    }
    
    setLoading(false)
  }

  const togglePurchased = async (id, currentStatus) => {
    setLoading(true)
    
    const { error } = await supabase
      .from('grocery_items')
      .update({ 
        is_purchased: !currentStatus,
        purchased_at: !currentStatus ? new Date().toISOString() : null
      })
      .eq('id', id)

    if (error) {
      console.error('Error updating item:', error)
      alert('Failed to update item')
    } else {
      const updatedItems = await fetchItems(user.id)
      setItems(updatedItems)
    }
    
    setLoading(false)
  }

  // Group items by category
  const groupedItems = items.reduce((acc, item) => {
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

  return (
    <div className="app-container">
      <div className="card-full">
        {/* Header */}
        <div className="nav-header">
          <div>
            <h1 style={{ textAlign: 'left' }}>Grocery List</h1>
            <p className="subtitle" style={{ textAlign: 'left', marginBottom: 0 }}>
              Manage your shopping list and track your purchases
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

        {/* Summary Stats */}
        {totalItems > 0 && (
          <div className="recipe-card mb-4">
            <div className="flex justify-between align-center">
              <div>
                <h3 style={{ marginBottom: '8px' }}>Shopping Summary</h3>
                <div style={{ display: 'flex', gap: '24px', fontSize: '0.875rem', color: '#6c757d' }}>
                  <span><strong>{totalItems}</strong> total items</span>
                  {purchasedItems > 0 && (
                    <span style={{ color: '#28a745' }}>
                      <strong>{purchasedItems}</strong> purchased
                    </span>
                  )}
                  <span><strong>{unpurchasedItems}</strong> remaining</span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#28a745' }}>
                  ${totalCost.toFixed(2)}
                </div>
                <div style={{ fontSize: '0.875rem', color: '#6c757d' }}>
                  Estimated Cost
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Category Sections */}
        <div className="mb-4">
          {categories.map((category) => {
            const categoryItems = groupedItems[category] || []
            const hasItems = categoryItems.length > 0
            
            if (!hasItems) return null
            
            return (
              <div key={category} className="recipe-card mb-3">
                <div className="flex justify-between align-center mb-3">
                  <h3 style={{ 
                    margin: 0, 
                    color: category === 'Recipe Generated' ? '#28a745' : '#333',
                    fontSize: '1.125rem'
                  }}>
                    {category === 'Recipe Generated' ? '🍳 From Recipes' : category}
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
                    <div key={item.id} style={{
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
                          marginBottom: '4px'
                        }}>
                          {item.name}
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
                        </div>
                      </div>
                      
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button 
                          onClick={() => togglePurchased(item.id, item.is_purchased)}
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
                          onClick={() => removeItem(item.id)} 
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
                  ))}
                </div>
              </div>
            )
          })}
          
          {/* Show uncategorized items if any */}
          {groupedItems['Uncategorized'] && groupedItems['Uncategorized'].length > 0 && (
            <div className="recipe-card mb-3">
              <div className="flex justify-between align-center mb-3">
                <h3 style={{ margin: 0, fontSize: '1.125rem' }}>Other Items</h3>
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
                  <div key={item.id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px',
                    backgroundColor: item.is_purchased ? '#f8f9fa' : '#fff',
                    border: '2px solid #e9ecef',
                    borderRadius: '8px',
                    opacity: item.is_purchased ? 0.7 : 1
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{
                        fontSize: '1rem',
                        color: '#333',
                        fontWeight: '500',
                        textDecoration: item.is_purchased ? 'line-through' : 'none',
                        marginBottom: '4px'
                      }}>
                        {item.name}
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
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        onClick={() => togglePurchased(item.id, item.is_purchased)}
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
                        onClick={() => removeItem(item.id)} 
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
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Add Manual Item Section */}
        <div className="recipe-card mb-4">
          <h3 className="mb-3">Add Manual Item</h3>
          
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
            <input
              type="text"
              placeholder="Item name (e.g., chicken, apples)"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addItem()}
              disabled={loading}
              style={{ flex: '2 1 200px', minWidth: '200px' }}
            />
            <input
              type="number"
              placeholder="Qty"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addItem()}
              min="0"
              step="0.1"
              disabled={loading}
              style={{ flex: '0 1 80px', minWidth: '80px' }}
            />
            <select
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              disabled={loading}
              style={{ flex: '0 1 100px', minWidth: '100px' }}
            >
              {units.map((unitOption) => (
                <option key={unitOption} value={unitOption}>
                  {unitOption || 'unit'}
                </option>
              ))}
            </select>
            <button 
              onClick={addItem} 
              disabled={loading || !input.trim()}
              className="btn-primary"
              style={{ flex: '0 1 120px', minWidth: '120px', margin: 0 }}
            >
              {loading ? 'Adding...' : 'Add Item'}
            </button>
          </div>
          
          {input.trim() && (
            <div style={{ 
              fontSize: '0.875rem', 
              color: '#6c757d',
              padding: '8px 12px',
              backgroundColor: '#f8f9fa',
              borderRadius: '6px',
              border: '1px solid #e9ecef'
            }}>
              Will be added to: <strong style={{ color: '#007bff' }}>{categorizeItem(input)}</strong>
              {quantity && (
                <span style={{ marginLeft: '12px', color: '#28a745' }}>
                  • Quantity: {quantity} {unit || 'unit(s)'}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {unpurchasedItems > 0 && (
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <button 
              disabled={unpurchasedItems === 0}
              className="btn-warning"
              style={{ flex: 1, minWidth: '200px' }}
            >
              🚗 Place DoorDash Order ({unpurchasedItems} items)
            </button>
            <button 
              disabled={unpurchasedItems === 0}
              className="btn-success"
              style={{ flex: 1, minWidth: '200px' }}
            >
              🛒 Place Instacart Order ({unpurchasedItems} items)
            </button>
          </div>
        )}

        {/* Empty State */}
        {totalItems === 0 && !loading && (
          <div style={{ 
            textAlign: 'center', 
            padding: '60px 20px',
            color: '#6c757d'
          }}>
            <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🛒</div>
            <h3 style={{ marginBottom: '8px' }}>Your grocery list is empty</h3>
            <p style={{ marginBottom: '24px' }}>
              Generate some recipes or add items manually to get started!
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => navigate('/generate')}
                className="btn-primary"
                style={{ width: 'auto', minWidth: '180px' }}
              >
                Generate Recipes
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}