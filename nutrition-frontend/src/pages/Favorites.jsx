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
      <div key={favorite.id} style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        marginBottom: '16px',
        backgroundColor: '#fff'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
          <div>
            <h3 style={{ margin: '0 0 8px 0', color: '#333' }}>
              {favorite.recipe_name || 'Favorite Recipe'}
            </h3>
            <div style={{ fontSize: '12px', color: '#888' }}>
              Favorited {new Date(favorite.favorited_at).toLocaleDateString()}
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={() => removeFavorite(favorite.id)}
              style={{
                padding: '4px 8px',
                backgroundColor: '#f44336',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              Remove
            </button>
          </div>
        </div>

        {/* Recipe Details */}
        {ingredients.length > 0 && (
          <div style={{ marginBottom: '12px' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#555' }}>Ingredients:</h4>
            <div style={{ fontSize: '12px', color: '#666' }}>
              {ingredients.slice(0, 3).map(ing => ing.name).join(', ')}
              {ingredients.length > 3 && ` +${ingredients.length - 3} more`}
            </div>
          </div>
        )}

        {/* Macros */}
        {(macros.calories || macros.protein) && (
          <div style={{ marginBottom: '12px' }}>
            <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: '#555' }}>Nutrition:</h4>
            <div style={{ fontSize: '12px', color: '#666', display: 'flex', gap: '12px' }}>
              {macros.calories && <span>Calories: {macros.calories}</span>}
              {macros.protein && <span>Protein: {macros.protein}</span>}
              {macros.carbs && <span>Carbs: {macros.carbs}</span>}
            </div>
          </div>
        )}

        {/* Cuisine and Cost */}
        <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#666' }}>
          {recipeData.cuisine && <span><strong>Cuisine:</strong> {recipeData.cuisine}</span>}
          {recipeData.cost_estimate && <span><strong>Est. Cost:</strong> ${recipeData.cost_estimate}</span>}
        </div>

        {/* Notes */}
        {favorite.notes && (
          <div style={{ marginTop: '12px', padding: '8px', backgroundColor: '#f9f9f9', borderRadius: '4px' }}>
            <strong style={{ fontSize: '12px' }}>Notes:</strong>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#666' }}>{favorite.notes}</p>
          </div>
        )}
      </div>
    );
  };

  if (loading && !userId) {
    return (
      <div className="card">
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="card">
      {/* Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '24px',
        paddingBottom: '16px',
        borderBottom: '2px solid #f0f0f0'
      }}>
        <div>
          <h1 style={{ margin: '0 0 8px 0', color: '#333' }}>❤️ My Favorites</h1>
          <p style={{ margin: 0, color: '#666', fontSize: '16px' }}>
            Your saved favorite recipes
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => navigate('/home')}
            style={{
              padding: '8px 16px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            🏠 Home
          </button>
          <button
            onClick={() => navigate('/generate')}
            style={{
              padding: '8px 16px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Generate Recipes
          </button>
        </div>
      </div>

      {/* Error Message */}
      {errorMsg && (
        <div style={{ 
          color: 'red', 
          marginBottom: '16px', 
          padding: '8px', 
          backgroundColor: '#ffebee', 
          borderRadius: '4px',
          border: '1px solid #ffcdd2'
        }}>
          {errorMsg}
        </div>
      )}

      {/* Collections Filter */}
      {collections.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <h3 style={{ margin: '0 0 12px 0', fontSize: '18px' }}>Filter by Collection</h3>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <button
              onClick={() => setSelectedCollection(null)}
              style={{
                padding: '8px 16px',
                backgroundColor: selectedCollection === null ? '#e91e63' : '#f5f5f5',
                color: selectedCollection === null ? 'white' : '#333',
                border: '1px solid #ddd',
                borderRadius: '20px',
                cursor: 'pointer',
                fontSize: '14px'
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
                  backgroundColor: selectedCollection === collection.id ? '#e91e63' : '#f5f5f5',
                  color: selectedCollection === collection.id ? 'white' : '#333',
                  border: '1px solid #ddd',
                  borderRadius: '20px',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                {collection.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Create Collection Button */}
      <div style={{ marginBottom: '24px' }}>
        <button
          onClick={() => setShowCreateCollection(!showCreateCollection)}
          style={{
            padding: '8px 16px',
            backgroundColor: '#ff9800',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          {showCreateCollection ? 'Cancel' : 'Create New Collection'}
        </button>
      </div>

      {/* Create Collection Form */}
      {showCreateCollection && (
        <div style={{ 
          marginBottom: '24px', 
          padding: '16px', 
          backgroundColor: '#f9f9f9', 
          borderRadius: '8px',
          border: '1px solid #ddd'
        }}>
          <h3 style={{ margin: '0 0 12px 0' }}>Create New Collection</h3>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: 'bold' }}>
              Collection Name
            </label>
            <input
              type="text"
              value={newCollectionName}
              onChange={(e) => setNewCollectionName(e.target.value)}
              placeholder="e.g., Quick Dinners, Healthy Snacks"
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px'
              }}
            />
          </div>
          <div style={{ marginBottom: '12px' }}>
            <label style={{ display: 'block', marginBottom: '4px', fontSize: '14px', fontWeight: 'bold' }}>
              Description (Optional)
            </label>
            <textarea
              value={newCollectionDescription}
              onChange={(e) => setNewCollectionDescription(e.target.value)}
              placeholder="Describe this collection..."
              rows={3}
              style={{
                width: '100%',
                padding: '8px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px',
                resize: 'vertical'
              }}
            />
          </div>
          <button
            onClick={createCollection}
            style={{
              padding: '8px 16px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Create Collection
          </button>
        </div>
      )}

      {/* Favorites List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px', color: '#666' }}>
          Loading favorites...
        </div>
      ) : favorites.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '32px' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>💔</div>
          <h3 style={{ color: '#666', marginBottom: '16px' }}>No favorites yet</h3>
          <p style={{ color: '#888', marginBottom: '24px' }}>
            Start favoriting recipes to see them here!
          </p>
          <button
            onClick={() => navigate('/generate')}
            style={{
              padding: '12px 24px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 'bold'
            }}
          >
            Generate Some Recipes
          </button>
        </div>
      ) : (
        <div>
          <div style={{ marginBottom: '16px', color: '#666', fontSize: '14px' }}>
            Showing {favorites.length} favorite{favorites.length !== 1 ? 's' : ''}
            {selectedCollection && collections.find(c => c.id === selectedCollection) && 
              ` in "${collections.find(c => c.id === selectedCollection).name}"`
            }
          </div>
          
          {favorites.map(favorite => renderFavoriteCard(favorite))}
        </div>
      )}
    </div>
  );
}