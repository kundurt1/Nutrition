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
    'Recipe Generated': [
      // This will catch items added from recipes
    ],
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
      console.log('Fetched grocery items:', groceryItems) // Debug log
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

    // Set up real-time listener for grocery_items table
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
          // Refresh the items when changes occur
          const updatedItems = await fetchItems(user.id)
          setItems(updatedItems)
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [user])

  // Add a manual refresh function
  const refreshItems = async () => {
    if (!user) return
    setLoading(true)
    const groceryItems = await fetchItems(user.id)
    setItems(groceryItems)
    setLoading(false)
  }

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
      item_name: input.trim(), // Add this field too for consistency
      estimated_cost: 0.0, // Default cost
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

  // Toggle purchased status
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
    'Recipe Generated', // Show recipe items first
    'Proteins',
    'Produce', 
    'Grains and Carbs',
    'Dairy & Alternatives',
    'Pantry and Staples',
    'Frozen and Misc'
  ]

  if (loading && !user) {
    return (
      <div className="card">
        <p>Loading...</p>
      </div>
    )
  }

  // Count total items and purchased items
  const totalItems = items.length
  const purchasedItems = items.filter(item => item.is_purchased).length
  const unpurchasedItems = totalItems - purchasedItems
  const totalCost = items.reduce((sum, item) => sum + (parseFloat(item.estimated_cost) || 0), 0)

  return (
    <div className="card">
      <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="back-button" onClick={() => navigate('/generate')} style={{
            padding: '8px 12px',
            backgroundColor: '#9E9E9E',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}>
            ← Generate
          </button>
          <h2 style={{ margin: 0 }}>Grocery List</h2>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button 
            onClick={refreshItems}
            disabled={loading}
            style={{
              padding: '8px 12px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {loading ? '...' : 'Refresh'}
          </button>
          <div style={{ fontSize: '14px', color: '#666' }}>
            {unpurchasedItems} items • ${totalCost.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      {totalItems > 0 && (
        <div style={{ 
          marginBottom: '20px', 
          padding: '12px', 
          backgroundColor: '#f5f5f5', 
          borderRadius: '8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <strong>Total: {totalItems} items</strong>
            {purchasedItems > 0 && (
              <span style={{ marginLeft: '16px', color: '#4CAF50' }}>
                ✓ {purchasedItems} purchased
              </span>
            )}
          </div>
          <div style={{ fontSize: '16px', fontWeight: 'bold', color: '#4CAF50' }}>
            Estimated Cost: ${totalCost.toFixed(2)}
          </div>
        </div>
      )}

      {/* Show categories with items */}
      <div className="categories-with-items">
        {categories.map((category) => {
          const categoryItems = groupedItems[category] || []
          const hasItems = categoryItems.length > 0
          
          if (!hasItems) return null // Don't show empty categories
          
          return (
            <div key={category} className={`category-section ${hasItems ? 'has-items' : ''}`} style={{
              marginBottom: '24px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div className="category-header" style={{ marginBottom: '12px' }}>
                <h3 className="category-title" style={{ 
                  margin: 0, 
                  color: category === 'Recipe Generated' ? '#4CAF50' : '#333',
                  fontSize: '18px'
                }}>
                  {category === 'Recipe Generated' ? '🍳 From Recipes' : category}
                </h3>
                <span className="item-count" style={{ color: '#666', fontSize: '14px' }}>
                  ({categoryItems.length} items)
                </span>
              </div>
              
              <div className="category-items">
                {categoryItems.map((item) => (
                  <div key={item.id} className="item" style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: '1px solid #eee',
                    opacity: item.is_purchased ? 0.6 : 1
                  }}>
                    <div className="item-info" style={{ flex: 1 }}>
                      <span className="item-name" style={{
                        fontWeight: 'bold',
                        textDecoration: item.is_purchased ? 'line-through' : 'none'
                      }}>
                        {item.name}
                      </span>
                      <span className="item-details" style={{ 
                        marginLeft: '8px', 
                        color: '#666',
                        fontSize: '14px'
                      }}>
                        {item.quantity} {item.unit}
                        {item.estimated_cost > 0 && (
                          <span style={{ marginLeft: '8px', color: '#4CAF50' }}>
                            ${parseFloat(item.estimated_cost).toFixed(2)}
                          </span>
                        )}
                      </span>
                    </div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button 
                        onClick={() => togglePurchased(item.id, item.is_purchased)}
                        style={{
                          padding: '4px 8px',
                          backgroundColor: item.is_purchased ? '#4CAF50' : '#2196F3',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                        disabled={loading}
                      >
                        {item.is_purchased ? '✓' : 'Buy'}
                      </button>
                      <button 
                        onClick={() => removeItem(item.id)} 
                        className="remove-btn"
                        title="Remove item"
                        disabled={loading}
                        style={{
                          padding: '4px 8px',
                          backgroundColor: '#f44336',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          fontSize: '12px',
                          cursor: 'pointer'
                        }}
                      >
                        ×
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
          <div className="category-section has-items" style={{
            marginBottom: '24px',
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '16px'
          }}>
            <div className="category-header" style={{ marginBottom: '12px' }}>
              <h3 className="category-title" style={{ margin: 0, fontSize: '18px' }}>Other Items</h3>
              <span className="item-count" style={{ color: '#666', fontSize: '14px' }}>
                ({groupedItems['Uncategorized'].length} items)
              </span>
            </div>
            <div className="category-items">
              {groupedItems['Uncategorized'].map((item) => (
                <div key={item.id} className="item" style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '8px 0',
                  borderBottom: '1px solid #eee',
                  opacity: item.is_purchased ? 0.6 : 1
                }}>
                  <div className="item-info" style={{ flex: 1 }}>
                    <span className="item-name" style={{
                      fontWeight: 'bold',
                      textDecoration: item.is_purchased ? 'line-through' : 'none'
                    }}>
                      {item.name}
                    </span>
                    <span className="item-details" style={{ 
                      marginLeft: '8px', 
                      color: '#666',
                      fontSize: '14px'
                    }}>
                      {item.quantity} {item.unit}
                      {item.estimated_cost > 0 && (
                        <span style={{ marginLeft: '8px', color: '#4CAF50' }}>
                          ${parseFloat(item.estimated_cost).toFixed(2)}
                        </span>
                      )}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button 
                      onClick={() => togglePurchased(item.id, item.is_purchased)}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: item.is_purchased ? '#4CAF50' : '#2196F3',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                      disabled={loading}
                    >
                      {item.is_purchased ? '✓' : 'Buy'}
                    </button>
                    <button 
                      onClick={() => removeItem(item.id)} 
                      className="remove-btn"
                      title="Remove item"
                      disabled={loading}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: '#f44336',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        fontSize: '12px',
                        cursor: 'pointer'
                      }}
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="add-item-section" style={{ marginTop: '32px', padding: '16px', backgroundColor: '#f9f9f9', borderRadius: '8px' }}>
        <h3 style={{ marginTop: 0 }}>Add Manual Item</h3>
        <div className="input-row" style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          <input
            type="text"
            placeholder="Item name (e.g., chicken, apples)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addItem()}
            className="item-input"
            disabled={loading}
            style={{ flex: 2, padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
          />
          <input
            type="number"
            placeholder="Qty"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addItem()}
            className="quantity-input"
            min="0"
            step="0.1"
            disabled={loading}
            style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
          />
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="unit-select"
            disabled={loading}
            style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
          >
            {units.map((unitOption) => (
              <option key={unitOption} value={unitOption}>
                {unitOption || 'unit'}
              </option>
            ))}
          </select>
          <button 
            className="add-btn" 
            onClick={addItem} 
            disabled={loading || !input.trim()}
            style={{
              padding: '8px 16px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {loading ? '...' : 'Add'}
          </button>
        </div>
        {input.trim() && (
          <div className="category-preview" style={{ fontSize: '14px', color: '#666' }}>
            Will be added to: <strong>{categorizeItem(input)}</strong>
            {quantity && (
              <span className="quantity-preview">
                • Quantity: {quantity} {unit || 'unit(s)'}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="action-buttons" style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
        <button 
          className="secondary" 
          disabled={unpurchasedItems === 0}
          style={{
            flex: 1,
            padding: '12px',
            backgroundColor: unpurchasedItems > 0 ? '#FF9800' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: unpurchasedItems > 0 ? 'pointer' : 'not-allowed'
          }}
        >
          Place DoorDash Order ({unpurchasedItems} items)
        </button>
        <button 
          className="secondary" 
          disabled={unpurchasedItems === 0}
          style={{
            flex: 1,
            padding: '12px',
            backgroundColor: unpurchasedItems > 0 ? '#4CAF50' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: unpurchasedItems > 0 ? 'pointer' : 'not-allowed'
          }}
        >
          Place Instacart Order ({unpurchasedItems} items)
        </button>
      </div>
    </div>
  )
}