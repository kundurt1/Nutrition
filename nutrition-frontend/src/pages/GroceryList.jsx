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

      // Fetch grocery items
      const { data: groceryItems, error: itemsError } = await supabase
        .from('grocery_items')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: false })

      if (itemsError) {
        console.error('Error fetching grocery items:', itemsError)
      } else {
        setItems(groceryItems || [])
      }

      setLoading(false)
    }

    checkUserAndFetchItems()
  }, [navigate])

  const addItem = async () => {
    if (!input.trim() || !user) return
    
    setLoading(true)
    
    const category = categorizeItem(input.trim())
    const newItem = {
      user_id: user.id,
      name: input.trim(),
      quantity: quantity.trim() || '1',
      unit: unit || '',
      category: category
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

  // Group items by category
  const groupedItems = items.reduce((acc, item) => {
    const category = item.category
    if (!acc[category]) {
      acc[category] = []
    }
    acc[category].push(item)
    return acc
  }, {})

  const categories = [
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

  return (
    <div className="card">
      <div className="header">
        <button className="back-button" onClick={() => navigate('/preferences')}>
          ←
        </button>
        <h2>Grocery List</h2>
      </div>

      {/* Show categories with items */}
      <div className="categories-with-items">
        {categories.map((category) => {
          const categoryItems = groupedItems[category] || []
          const hasItems = categoryItems.length > 0
          
          return (
            <div key={category} className={`category-section ${hasItems ? 'has-items' : ''}`}>
              <div className="category-header">
                <h3 className="category-title">{category}</h3>
                {hasItems && <span className="item-count">({categoryItems.length})</span>}
              </div>
              
              {hasItems && (
                <div className="category-items">
                  {categoryItems.map((item) => (
                    <div key={item.id} className="item">
                      <div className="item-info">
                        <span className="item-name">{item.name}</span>
                        <span className="item-details">
                          {item.quantity} {item.unit}
                        </span>
                      </div>
                      <button 
                        onClick={() => removeItem(item.id)} 
                        className="remove-btn"
                        title="Remove item"
                        disabled={loading}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )
        })}
        
        {/* Show uncategorized items if any */}
        {groupedItems['Uncategorized'] && groupedItems['Uncategorized'].length > 0 && (
          <div className="category-section has-items">
            <div className="category-header">
              <h3 className="category-title">Other Items</h3>
              <span className="item-count">({groupedItems['Uncategorized'].length})</span>
            </div>
            <div className="category-items">
              {groupedItems['Uncategorized'].map((item) => (
                <div key={item.id} className="item">
                  <div className="item-info">
                    <span className="item-name">{item.name}</span>
                    <span className="item-details">
                      {item.quantity} {item.unit}
                    </span>
                  </div>
                  <button 
                    onClick={() => removeItem(item.id)} 
                    className="remove-btn"
                    title="Remove item"
                    disabled={loading}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="add-item-section">
        <div className="input-row">
          <input
            type="text"
            placeholder="Item name (e.g., chicken, apples)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addItem()}
            className="item-input"
            disabled={loading}
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
          />
          <select
            value={unit}
            onChange={(e) => setUnit(e.target.value)}
            className="unit-select"
            disabled={loading}
          >
            {units.map((unitOption) => (
              <option key={unitOption} value={unitOption}>
                {unitOption || 'unit'}
              </option>
            ))}
          </select>
          <button className="add-btn" onClick={addItem} disabled={loading || !input.trim()}>
            {loading ? '...' : 'Add'}
          </button>
        </div>
        {input.trim() && (
          <div className="category-preview">
            Will be added to: <strong>{categorizeItem(input)}</strong>
            {quantity && (
              <span className="quantity-preview">
                • Quantity: {quantity} {unit || 'unit(s)'}
              </span>
            )}
          </div>
        )}
      </div>

      <div className="action-buttons">
        <button className="secondary" disabled={items.length === 0}>
          Place DoorDash Order ({items.length} items)
        </button>
        <button className="secondary" disabled={items.length === 0}>
          Place Instacart Order ({items.length} items)
        </button>
      </div>
    </div>
  )
}