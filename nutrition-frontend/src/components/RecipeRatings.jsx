import { useState, useEffect } from 'react';

const RecipeRating = ({ recipeData, userId, onRatingSubmit }) => {
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackReason, setFeedbackReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Favorites state
  const [isFavorited, setIsFavorited] = useState(false);
  const [favoriteId, setFavoriteId] = useState(null);
  const [favoritingInProgress, setFavoritingInProgress] = useState(false);

  const feedbackOptions = [
    'Too many ingredients I don\'t like',
    'Too complicated to make',
    'Not enough protein',
    'Too expensive',
    'Cooking time too long',
    'Don\'t like this cuisine',
    'Other'
  ];

  // Check if recipe is already favorited when component mounts
  useEffect(() => {
    const checkFavoriteStatus = async () => {
      if (!userId || !recipeData) return;
      
      try {
        const params = new URLSearchParams({
          user_id: userId,
        });
        
        if (recipeData.recipe_id) {
          params.append('recipe_id', recipeData.recipe_id);
        } else {
          params.append('recipe_name', recipeData.recipe_name || 'Generated Recipe');
        }
        
        const response = await fetch(`http://localhost:8000/check-favorite/${userId}?${params}`);
        
        if (response.ok) {
          const data = await response.json();
          setIsFavorited(data.is_favorited);
          setFavoriteId(data.favorite_id);
        }
      } catch (error) {
        console.error('Error checking favorite status:', error);
      }
    };
    
    checkFavoriteStatus();
  }, [userId, recipeData]);

  const submitRating = async () => {
    if (rating === 0) return;
    
    setSubmitting(true);
    try {
      const response = await fetch('http://localhost:8000/rate-recipe', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          recipe_id: recipeData?.recipe_id || null,
          recipe_data: recipeData,
          rating: rating,
          feedback_reason: rating <= 2 ? feedbackReason : null
        })
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Rating submitted successfully:', result);
        onRatingSubmit && onRatingSubmit(rating, feedbackReason);
        
        // Show success message
        if (rating <= 2 && feedbackReason) {
          alert('Thanks for your feedback! We\'ll use this to improve future recipes.');
        } else if (rating >= 4) {
          alert('Great! We\'ll remember what you liked about this recipe.');
        }
        
        setShowFeedback(false);
      } else {
        console.error('Failed to submit rating');
        alert('Failed to submit rating. Please try again.');
      }
    } catch (error) {
      console.error('Error submitting rating:', error);
      alert('Error submitting rating. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleFavoriteToggle = async () => {
    if (!userId || !recipeData || favoritingInProgress) return;
    
    setFavoritingInProgress(true);
    
    try {
      if (isFavorited && favoriteId) {
        // Remove from favorites
        const response = await fetch(`http://localhost:8000/remove-favorite/${favoriteId}?user_id=${userId}`, {
          method: 'DELETE'
        });
        
        if (response.ok) {
          setIsFavorited(false);
          setFavoriteId(null);
          console.log('Recipe removed from favorites');
        } else {
          alert('Failed to remove from favorites');
        }
      } else {
        // Add to favorites
        const favoriteData = {
          user_id: userId,
          recipe_name: recipeData.recipe_name || `Generated Recipe ${Date.now()}`,
          notes: null
        };
        
        if (recipeData.recipe_id) {
          favoriteData.recipe_id = recipeData.recipe_id;
        } else {
          favoriteData.recipe_data = recipeData;
        }
        
        const response = await fetch('http://localhost:8000/add-favorite', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(favoriteData)
        });
        
        if (response.ok) {
          const result = await response.json();
          if (result.success) {
            setIsFavorited(true);
            setFavoriteId(result.favorite_id);
            console.log('Recipe added to favorites');
          } else {
            alert(result.message);
          }
        } else {
          alert('Failed to add to favorites');
        }
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
      alert('Error updating favorites. Please try again.');
    } finally {
      setFavoritingInProgress(false);
    }
  };

  const handleStarClick = (starRating) => {
    setRating(starRating);
    if (starRating <= 2) {
      setShowFeedback(true);
    } else {
      submitRating();
    }
  };

  return (
    <div style={{ 
      padding: '12px', 
      backgroundColor: '#f8f9fa', 
      borderRadius: '6px', 
      marginTop: '12px',
      border: '1px solid #e9ecef'
    }}>
      {/* Rating and Favorites Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '8px'
      }}>
        <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#495057' }}>
          Rate this recipe:
        </div>
        
        {/* Favorites Button */}
        <button
          onClick={handleFavoriteToggle}
          disabled={favoritingInProgress}
          style={{
            background: 'none',
            border: 'none',
            cursor: favoritingInProgress ? 'not-allowed' : 'pointer',
            fontSize: '20px',
            color: isFavorited ? '#e74c3c' : '#dee2e6',
            transition: 'color 0.2s ease',
            padding: '4px'
          }}
          title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
        >
          {favoritingInProgress ? '⏳' : (isFavorited ? '❤️' : '🤍')}
        </button>
      </div>
      
      {/* Star Rating */}
      <div style={{ display: 'flex', gap: '4px', marginBottom: '8px' }}>
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            onClick={() => handleStarClick(star)}
            onMouseEnter={() => setHoverRating(star)}
            onMouseLeave={() => setHoverRating(0)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: '20px',
              color: star <= (hoverRating || rating) ? '#ffc107' : '#dee2e6',
              transition: 'color 0.2s ease'
            }}
            disabled={submitting}
          >
            ★
          </button>
        ))}
      </div>

      {/* Feedback Form */}
      {showFeedback && (
        <div style={{ marginTop: '12px' }}>
          <div style={{ marginBottom: '8px', fontSize: '13px', color: '#6c757d' }}>
            What didn't you like about this recipe?
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {feedbackOptions.map((option) => (
              <label key={option} style={{ display: 'flex', alignItems: 'center', fontSize: '12px' }}>
                <input
                  type="radio"
                  name="feedback"
                  value={option}
                  checked={feedbackReason === option}
                  onChange={(e) => setFeedbackReason(e.target.value)}
                  style={{ marginRight: '8px' }}
                />
                {option}
              </label>
            ))}
          </div>
          
          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
            <button
              onClick={submitRating}
              disabled={!feedbackReason || submitting}
              style={{
                padding: '6px 12px',
                backgroundColor: feedbackReason ? '#28a745' : '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                cursor: feedbackReason ? 'pointer' : 'not-allowed'
              }}
            >
              {submitting ? 'Submitting...' : 'Submit Rating'}
            </button>
            <button
              onClick={() => setShowFeedback(false)}
              style={{
                padding: '6px 12px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                fontSize: '12px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Favorite Status Indicator */}
      {isFavorited && (
        <div style={{ 
          marginTop: '8px', 
          fontSize: '12px', 
          color: '#e74c3c',
          fontStyle: 'italic'
        }}>
          ❤️ Added to favorites
        </div>
      )}
    </div>
  );
};

export default RecipeRating;