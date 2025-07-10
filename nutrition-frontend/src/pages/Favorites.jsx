// src/pages/Favorites.jsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';

export default function Favorites() {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [favorites, setFavorites] = useState([]);
  const [collections, setCollections] = useState([]);
  const [selectedCollection, setSelectedCollection] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  const [showCreateCollection, setShowCreateCollection] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newCollectionDescription, setNewCollectionDescription] = useState('');

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const { data: { user }, error: userError } = await supabase.auth.getUser();
        if (userError || !user) {
          navigate('/');
          return;
        }
        setUserId(user.id);
      } catch (error) {
        console.error('Error fetching user:', error);
        navigate('/');
      }
    };
    fetchUser();
  }, [navigate]);

  useEffect(() => {
    if (userId) {
      fetchFavorites();
      fetchCollections();
    }
  }, [userId, selectedCollection]);
  const addFavoriteToNutritionLog = async (favorite) => {
    if (!userId) {
      alert('Please sign in to track nutrition');
      return;
    }

    try {
      const result = await fetch('http://localhost:8000/quick-log-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          recipe_data: favorite.recipe_data || {
            recipe_name: favorite.recipe_name,
            macros: favorite.recipe_data?.macros || {},
            cost_estimate: favorite.recipe_data?.cost_estimate || 0,
            cuisine: favorite.recipe_data?.cuisine || 'Unknown'
          }
        })
      });

      if (result.ok) {
        // Show success notification
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center';
        notification.innerHTML = `
        <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
        </svg>
        Added "${favorite.recipe_name}" to nutrition log!
      `;
        document.body.appendChild(notification);

        setTimeout(() => {
          if (document.body.contains(notification)) {
            document.body.removeChild(notification);
          }
        }, 3000);
      } else {
        alert('Failed to add to nutrition log');
      }
    } catch (error) {
      console.error('Error adding to nutrition log:', error);
      alert('Error adding to nutrition log');
    }
  };


  const fetchFavorites = async () => {
    try {
      setLoading(true);
      const params = selectedCollection ? `?collection_id=${selectedCollection}` : '';
      const response = await fetch(`http://localhost:8000/favorites/${userId}${params}`);
      
      if (response.ok) {
        const data = await response.json();
        setFavorites(data.favorites || []);
      } else {
        setErrorMsg('Failed to load favorites');
      }
    } catch (error) {
      console.error('Error fetching favorites:', error);
      setErrorMsg('Error loading favorites');
    } finally {
      setLoading(false);
    }
  };

  const fetchCollections = async () => {
    try {
      const response = await fetch(`http://localhost:8000/collections/${userId}`);
      
      if (response.ok) {
        const data = await response.json();
        setCollections(data.collections || []);
      }
    } catch (error) {
      console.error('Error fetching collections:', error);
    }
  };

  const removeFavorite = async (favoriteId) => {
    if (!window.confirm('Are you sure you want to remove this recipe from favorites?')) {
      return;
    }

    try {
      const response = await fetch(`http://localhost:8000/remove-favorite/${favoriteId}?user_id=${userId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        setFavorites(favorites.filter(fav => fav.id !== favoriteId));
      } else {
        alert('Failed to remove favorite');
      }
    } catch (error) {
      console.error('Error removing favorite:', error);
      alert('Error removing favorite');
    }
  };

  const createCollection = async () => {
    if (!newCollectionName.trim()) {
      alert('Please enter a collection name');
      return;
    }

    try {
      const response = await fetch('http://localhost:8000/create-collection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          name: newCollectionName.trim(),
          description: newCollectionDescription.trim() || null
        })
      });

      if (response.ok) {
        setNewCollectionName('');
        setNewCollectionDescription('');
        setShowCreateCollection(false);
        fetchCollections();
      } else {
        alert('Failed to create collection');
      }
    } catch (error) {
      console.error('Error creating collection:', error);
      alert('Error creating collection');
    }
  };

  const renderFavoriteCard = (favorite) => {
    const recipeData = favorite.recipe_data || {};
    const ingredients = recipeData.ingredients || [];
    const macros = recipeData.macros || {};
    
    return (
      <div key={favorite.id} className="recipe-card">
        <div className="recipe-header">
          <div>
            <h3 className="recipe-title">
              {favorite.recipe_name || 'Favorite Recipe'}
            </h3>
            <div style={{ 
              fontSize: '0.875rem', 
              color: '#6c757d',
              marginTop: '4px'
            }}>
              Favorited {new Date(favorite.favorited_at).toLocaleDateString()}
            </div>
          </div>
          
          <div className="recipe-actions">
            <button
              onClick={() => removeFavorite(favorite.id)}
              className="btn-danger btn-sm"
            >
              Remove
            </button>
          </div>
        </div>

        {/* Recipe Details */}
        {ingredients.length > 0 && (
          <div className="recipe-section">
            <h4>Key Ingredients</h4>
            <div style={{ fontSize: '0.875rem', color: '#495057' }}>
              {ingredients.slice(0, 5).map(ing => ing.name).join(', ')}
              {ingredients.length > 5 && ` +${ingredients.length - 5} more`}
            </div>
          </div>
        )}

        {/* Nutrition Info */}
        {(macros.calories || macros.protein) && (
          <div className="recipe-section">
            <h4>Nutrition</h4>
            <div className="nutrition-grid">
              {macros.calories && (
                <div className="nutrition-item">
                  <span className="nutrition-value">{macros.calories}</span>
                  <span className="nutrition-label">Calories</span>
                </div>
              )}
              {macros.protein && (
                <div className="nutrition-item">
                  <span className="nutrition-value">{macros.protein}</span>
                  <span className="nutrition-label">Protein</span>
                </div>
              )}
              {macros.carbs && (
                <div className="nutrition-item">
                  <span className="nutrition-value">{macros.carbs}</span>
                  <span className="nutrition-label">Carbs</span>
                </div>
              )}
              {macros.fat && (
                <div className="nutrition-item">
                  <span className="nutrition-value">{macros.fat}</span>
                  <span className="nutrition-label">Fat</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recipe Meta */}
        <div style={{ 
          display: 'flex', 
          gap: '16px', 
          fontSize: '0.875rem', 
          color: '#6c757d',
          marginTop: '16px',
          paddingTop: '16px',
          borderTop: '1px solid #e9ecef'
        }}>
          {recipeData.cuisine && (
            <span><strong>Cuisine:</strong> {recipeData.cuisine}</span>
          )}
          {recipeData.cost_estimate && (
            <span><strong>Cost:</strong> ${recipeData.cost_estimate}</span>
          )}
        </div>

        {/* Notes */}
        {favorite.notes && (
          <div style={{ 
            marginTop: '16px', 
            padding: '12px', 
            backgroundColor: '#f8f9fa', 
            borderRadius: '8px',
            border: '1px solid #e9ecef'
          }}>
            <strong style={{ fontSize: '0.875rem', color: '#495057' }}>Notes:</strong>
            <p style={{ 
              margin: '4px 0 0 0', 
              fontSize: '0.875rem', 
              color: '#6c757d',
              lineHeight: '1.4'
            }}>
              {favorite.notes}
            </p>
          </div>
        )}
      </div>
    );
  };

  if (loading && !userId) {
    return (
      <div className="app-container">
        <div className="card">
          <p className="text-center">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="card-full">
        {/* Header */}
        <div className="nav-header">
          <div>
            <h1 style={{ textAlign: 'left' }}>❤️ My Favorites</h1>
            <p className="subtitle" style={{ textAlign: 'left', marginBottom: 0 }}>
              Your saved favorite recipes and collections
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
              className="btn-primary btn-sm"
            >
              Generate Recipes
            </button>
          </div>
        </div>

        {/* Error Message */}
        {errorMsg && (
          <div className="error-message">
            {errorMsg}
          </div>
        )}

        {/* Collections Filter */}
        {collections.length > 0 && (
          <div className="recipe-card mb-4">
            <h3 className="mb-3">Filter by Collection</h3>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <button
                onClick={() => setSelectedCollection(null)}
                style={{
                  padding: '8px 16px',
                  backgroundColor: selectedCollection === null ? '#007bff' : '#f8f9fa',
                  color: selectedCollection === null ? 'white' : '#495057',
                  border: '2px solid #e9ecef',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  minHeight: 'auto'
                }}
              >
                All Favorites ({favorites.length})
              </button>
              {collections.map(collection => (
                <button
                  key={collection.id}
                  onClick={() => setSelectedCollection(collection.id)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: selectedCollection === collection.id ? '#007bff' : '#f8f9fa',
                    color: selectedCollection === collection.id ? 'white' : '#495057',
                    border: '2px solid #e9ecef',
                    borderRadius: '20px',
                    cursor: 'pointer',
                    fontSize: '0.875rem',
                    fontWeight: '500',
                    minHeight: 'auto'
                  }}
                >
                  {collection.name}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Create Collection Section */}
        <div className="recipe-card mb-4">
          <div className="flex justify-between align-center mb-3">
            <h3 style={{ margin: 0 }}>Collections</h3>
            <button
              onClick={() => setShowCreateCollection(!showCreateCollection)}
              className="btn-warning btn-sm"
            >
              {showCreateCollection ? 'Cancel' : 'Create New Collection'}
            </button>
          </div>

          {showCreateCollection && (
            <div style={{ 
              padding: '16px', 
              backgroundColor: '#f8f9fa', 
              borderRadius: '8px',
              border: '1px solid #e9ecef'
            }}>
              <div className="form-group">
                <label>Collection Name</label>
                <input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="e.g., Quick Dinners, Healthy Snacks"
                />
              </div>
              
              <div className="form-group">
                <label>Description (Optional)</label>
                <textarea
                  value={newCollectionDescription}
                  onChange={(e) => setNewCollectionDescription(e.target.value)}
                  placeholder="Describe this collection..."
                  rows={3}
                  style={{ resize: 'vertical' }}
                />
              </div>
              
              <button
                onClick={createCollection}
                className="btn-success"
                style={{ width: 'auto', minWidth: '150px' }}
              >
                Create Collection
              </button>
            </div>
          )}
        </div>

        {/* Favorites List */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#6c757d' }}>
            Loading favorites...
          </div>
        ) : favorites.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '60px 20px' }}>
            <div style={{ fontSize: '4rem', marginBottom: '16px' }}>💔</div>
            <h3 style={{ color: '#6c757d', marginBottom: '8px' }}>No favorites yet</h3>
            <p style={{ color: '#6c757d', marginBottom: '24px' }}>
              Start favoriting recipes to see them here!
            </p>
            <button
              onClick={() => navigate('/generate')}
              className="btn-primary"
              style={{ width: 'auto', minWidth: '200px' }}
            >
              Generate Some Recipes
            </button>
          </div>
        ) : (
          <div>
            <div style={{ 
              marginBottom: '24px', 
              color: '#6c757d', 
              fontSize: '0.875rem',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>
                Showing {favorites.length} favorite{favorites.length !== 1 ? 's' : ''}
                {selectedCollection && collections.find(c => c.id === selectedCollection) && 
                  ` in "${collections.find(c => c.id === selectedCollection).name}"`
                }
              </span>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {favorites.map(favorite => renderFavoriteCard(favorite))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}