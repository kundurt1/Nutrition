// src/components/CommunityFeed.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import {
    Heart,
    MessageCircle,
    Share2,
    Bookmark,
    Users,
    Search,
    Filter,
    Eye,
    Star,
    UserPlus,
    ChefHat,
    Clock,
    DollarSign
} from 'lucide-react';

const CommunityFeed = () => {
    const navigate = useNavigate();
    const [userId, setUserId] = useState(null);
    const [activeTab, setActiveTab] = useState('feed');
    const [feedData, setFeedData] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedFilters, setSelectedFilters] = useState({
        cuisine: '',
        maxCost: '',
        maxTime: '',
        sortBy: 'recent'
    });

    // State for interactions
    const [likedRecipes, setLikedRecipes] = useState(new Set());
    const [savedRecipes, setSavedRecipes] = useState(new Set());
    const [showComments, setShowComments] = useState({});
    const [newComment, setNewComment] = useState({});

    // State for sharing modal
    const [showShareModal, setShowShareModal] = useState(false);
    const [recipeToShare, setRecipeToShare] = useState(null);
    const [shareMessage, setShareMessage] = useState('');
    const [shareLevel, setShareLevel] = useState('public');

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
        if (userId && activeTab === 'feed') {
            loadCommunityFeed();
        }
    }, [userId, activeTab, selectedFilters]);

    const loadCommunityFeed = async () => {
        try {
            setLoading(true);
            const response = await fetch(`http://localhost:8000/community-feed/${userId}?page=1&per_page=20`);

            if (response.ok) {
                const data = await response.json();
                setFeedData(data.feed || []);

                // Track which recipes are liked/saved by user
                const liked = new Set();
                const saved = new Set();

                data.feed.forEach(recipe => {
                    if (recipe.is_liked_by_user) liked.add(recipe.id);
                    if (recipe.is_saved_by_user) saved.add(recipe.id);
                });

                setLikedRecipes(liked);
                setSavedRecipes(saved);
            }
        } catch (error) {
            console.error('Error loading community feed:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleLikeRecipe = async (recipeId) => {
        try {
            const response = await fetch('http://localhost:8000/like-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shared_recipe_id: recipeId,
                    user_id: userId
                })
            });

            if (response.ok) {
                const result = await response.json();

                // Update local state
                setLikedRecipes(prev => {
                    const newLiked = new Set(prev);
                    if (result.action === 'liked') {
                        newLiked.add(recipeId);
                    } else {
                        newLiked.delete(recipeId);
                    }
                    return newLiked;
                });

                // Update feed data with new like count
                setFeedData(prev => prev.map(recipe =>
                    recipe.id === recipeId
                        ? {
                            ...recipe,
                            likes_count: recipe.likes_count + (result.action === 'liked' ? 1 : -1),
                            is_liked_by_user: result.action === 'liked'
                        }
                        : recipe
                ));
            }
        } catch (error) {
            console.error('Error liking recipe:', error);
        }
    };

    const handleSaveRecipe = async (recipeId) => {
        try {
            const response = await fetch('http://localhost:8000/save-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    shared_recipe_id: recipeId,
                    user_id: userId
                })
            });

            if (response.ok) {
                setSavedRecipes(prev => {
                    const newSaved = new Set(prev);
                    newSaved.add(recipeId);
                    return newSaved;
                });

                // Show success message
                showSuccessMessage('Recipe saved to your collection!');
            }
        } catch (error) {
            console.error('Error saving recipe:', error);
        }
    };

    const handleAddComment = async (recipeId) => {
        const commentText = newComment[recipeId];
        if (!commentText || !commentText.trim()) return;

        try {
            const response = await fetch('http://localhost:8000/comment-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    shared_recipe_id: recipeId,
                    comment_text: commentText.trim()
                })
            });

            if (response.ok) {
                // Clear comment input
                setNewComment(prev => ({ ...prev, [recipeId]: '' }));

                // Update comments count
                setFeedData(prev => prev.map(recipe =>
                    recipe.id === recipeId
                        ? { ...recipe, comments_count: recipe.comments_count + 1 }
                        : recipe
                ));

                showSuccessMessage('Comment added!');
            }
        } catch (error) {
            console.error('Error adding comment:', error);
        }
    };

    const handleShareRecipe = async (recipe) => {
        setRecipeToShare(recipe);
        setShowShareModal(true);
    };

    const submitShareRecipe = async () => {
        if (!recipeToShare) return;

        try {
            const response = await fetch('http://localhost:8000/share-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    recipe_data: recipeToShare.recipe_data,
                    sharing_level: shareLevel,
                    message: shareMessage,
                    tags: recipeToShare.tags || []
                })
            });

            if (response.ok) {
                setShowShareModal(false);
                setShareMessage('');
                setRecipeToShare(null);
                showSuccessMessage('Recipe shared with the community!');
            }
        } catch (error) {
            console.error('Error sharing recipe:', error);
        }
    };

    const showSuccessMessage = (message) => {
        const notification = document.createElement('div');
        notification.className = 'fixed top-4 right-4 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg z-50 flex items-center';
        notification.innerHTML = `
      <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
      </svg>
      ${message}
    `;
        document.body.appendChild(notification);

        setTimeout(() => {
            if (document.body.contains(notification)) {
                document.body.removeChild(notification);
            }
        }, 3000);
    };

    const RecipeCard = ({ recipe }) => (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden mb-6">
            {/* Header with user info */}
            <div className="p-4 border-b border-gray-100">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold">
                            {recipe.shared_by.display_name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <h3 className="font-semibold text-gray-900">{recipe.shared_by.display_name}</h3>
                            <p className="text-sm text-gray-500">@{recipe.shared_by.username}</p>
                        </div>
                    </div>
                    <div className="flex items-center space-x-2 text-sm text-gray-500">
                        <Clock className="w-4 h-4" />
                        <span>{new Date(recipe.created_at).toLocaleDateString()}</span>
                    </div>
                </div>

                {recipe.message && (
                    <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                        <p className="text-gray-700">{recipe.message}</p>
                    </div>
                )}
            </div>

            {/* Recipe content */}
            <div className="p-4">
                <div className="flex items-start justify-between mb-4">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900 mb-2">{recipe.recipe_name}</h2>
                        <div className="flex items-center space-x-4 text-sm text-gray-600">
                            <div className="flex items-center space-x-1">
                                <ChefHat className="w-4 h-4" />
                                <span>{recipe.recipe_data.cuisine || 'Various'}</span>
                            </div>
                            <div className="flex items-center space-x-1">
                                <Clock className="w-4 h-4" />
                                <span>{recipe.recipe_data.prep_time || '30 min'}</span>
                            </div>
                            <div className="flex items-center space-x-1">
                                <DollarSign className="w-4 h-4" />
                                <span>${recipe.recipe_data.cost_estimate || '0.00'}</span>
                            </div>
                            <div className="flex items-center space-x-1">
                                <Star className="w-4 h-4 text-yellow-500" />
                                <span>{recipe.rating_average.toFixed(1)}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Nutrition info */}
                {recipe.recipe_data.macros && (
                    <div className="grid grid-cols-4 gap-4 mb-4 p-3 bg-gray-50 rounded-lg">
                        <div className="text-center">
                            <div className="font-semibold text-blue-600">{recipe.recipe_data.macros.calories || 0}</div>
                            <div className="text-xs text-gray-600">Calories</div>
                        </div>
                        <div className="text-center">
                            <div className="font-semibold text-red-600">{String(recipe.recipe_data.macros.protein || '0').replace('g', '')}g</div>
                            <div className="text-xs text-gray-600">Protein</div>
                        </div>
                        <div className="text-center">
                            <div className="font-semibold text-yellow-600">{String(recipe.recipe_data.macros.carbs || '0').replace('g', '')}g</div>
                            <div className="text-xs text-gray-600">Carbs</div>
                        </div>
                        <div className="text-center">
                            <div className="font-semibold text-purple-600">{String(recipe.recipe_data.macros.fat || '0').replace('g', '')}g</div>
                            <div className="text-xs text-gray-600">Fat</div>
                        </div>
                    </div>
                )}

                {/* Tags */}
                {recipe.tags && recipe.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                        {recipe.tags.map((tag, index) => (
                            <span
                                key={index}
                                className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full"
                            >
                #{tag}
              </span>
                        ))}
                    </div>
                )}

                {/* Interaction buttons */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-100">
                    <div className="flex items-center space-x-6">
                        <button
                            onClick={() => handleLikeRecipe(recipe.id)}
                            className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                                likedRecipes.has(recipe.id)
                                    ? 'bg-red-50 text-red-600'
                                    : 'text-gray-600 hover:bg-gray-50'
                            }`}
                        >
                            <Heart className={`w-5 h-5 ${likedRecipes.has(recipe.id) ? 'fill-current' : ''}`} />
                            <span className="font-medium">{recipe.likes_count}</span>
                        </button>

                        <button
                            onClick={() => setShowComments(prev => ({ ...prev, [recipe.id]: !prev[recipe.id] }))}
                            className="flex items-center space-x-2 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                            <MessageCircle className="w-5 h-5" />
                            <span className="font-medium">{recipe.comments_count}</span>
                        </button>

                        <button
                            onClick={() => handleShareRecipe(recipe)}
                            className="flex items-center space-x-2 px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                            <Share2 className="w-5 h-5" />
                            <span className="font-medium">Share</span>
                        </button>
                    </div>

                    <button
                        onClick={() => handleSaveRecipe(recipe.id)}
                        className={`p-2 rounded-lg transition-colors ${
                            savedRecipes.has(recipe.id)
                                ? 'bg-blue-50 text-blue-600'
                                : 'text-gray-600 hover:bg-gray-50'
                        }`}
                    >
                        <Bookmark className={`w-5 h-5 ${savedRecipes.has(recipe.id) ? 'fill-current' : ''}`} />
                    </button>
                </div>

                {/* Comments section */}
                {showComments[recipe.id] && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                        <div className="flex space-x-3 mb-4">
                            <div className="w-8 h-8 bg-gradient-to-br from-green-500 to-blue-600 rounded-full flex items-center justify-center text-white text-sm font-semibold">
                                U
                            </div>
                            <div className="flex-1">
                                <input
                                    type="text"
                                    placeholder="Add a comment..."
                                    value={newComment[recipe.id] || ''}
                                    onChange={(e) => setNewComment(prev => ({ ...prev, [recipe.id]: e.target.value }))}
                                    onKeyPress={(e) => e.key === 'Enter' && handleAddComment(recipe.id)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                />
                            </div>
                            <button
                                onClick={() => handleAddComment(recipe.id)}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Post
                            </button>
                        </div>

                        {/* Comments would be loaded and displayed here */}
                        <div className="space-y-3">
                            <div className="text-sm text-gray-500 text-center py-4">
                                Comments will be loaded here...
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );

    const SearchAndFilters = () => (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
            <div className="flex flex-col space-y-4">
                {/* Search bar */}
                <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                    <input
                        type="text"
                        placeholder="Search recipes, users, or cuisines..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-4">
                    <select
                        value={selectedFilters.cuisine}
                        onChange={(e) => setSelectedFilters(prev => ({ ...prev, cuisine: e.target.value }))}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">All Cuisines</option>
                        <option value="italian">Italian</option>
                        <option value="mexican">Mexican</option>
                        <option value="asian">Asian</option>
                        <option value="mediterranean">Mediterranean</option>
                    </select>

                    <select
                        value={selectedFilters.sortBy}
                        onChange={(e) => setSelectedFilters(prev => ({ ...prev, sortBy: e.target.value }))}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="recent">Most Recent</option>
                        <option value="popular">Most Popular</option>
                        <option value="top_rated">Top Rated</option>
                    </select>

                    <input
                        type="number"
                        placeholder="Max cost ($)"
                        value={selectedFilters.maxCost}
                        onChange={(e) => setSelectedFilters(prev => ({ ...prev, maxCost: e.target.value }))}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 w-32"
                    />

                    <input
                        type="number"
                        placeholder="Max time (min)"
                        value={selectedFilters.maxTime}
                        onChange={(e) => setSelectedFilters(prev => ({ ...prev, maxTime: e.target.value }))}
                        className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 w-32"
                    />
                </div>
            </div>
        </div>
    );

    return (
        <div className="max-w-4xl mx-auto p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                        <Users className="w-8 h-8 mr-3 text-blue-600" />
                        Recipe Community
                    </h1>
                    <p className="text-gray-600 mt-2">Discover, share, and connect with fellow food enthusiasts</p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => navigate('/home')}
                        className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                        <ChefHat className="w-4 h-4 mr-2" />
                        Home
                    </button>
                    <button
                        onClick={() => navigate('/generate')}
                        className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Generate Recipe
                    </button>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-gray-200 mb-8">
                <button
                    onClick={() => setActiveTab('feed')}
                    className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                        activeTab === 'feed'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                >
                    🏠 Community Feed
                </button>
                <button
                    onClick={() => setActiveTab('following')}
                    className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                        activeTab === 'following'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                >
                    👥 Following
                </button>
                <button
                    onClick={() => setActiveTab('trending')}
                    className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                        activeTab === 'trending'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                >
                    🔥 Trending
                </button>
                <button
                    onClick={() => setActiveTab('myshares')}
                    className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                        activeTab === 'myshares'
                            ? 'border-blue-500 text-blue-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                >
                    📤 My Shares
                </button>
            </div>

            {/* Content */}
            {activeTab === 'feed' && (
                <div>
                    <SearchAndFilters />

                    {loading ? (
                        <div className="flex items-center justify-center h-64">
                            <div className="text-center">
                                <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                                <p className="text-gray-600">Loading community feed...</p>
                            </div>
                        </div>
                    ) : feedData.length > 0 ? (
                        <div>
                            {feedData.map(recipe => (
                                <RecipeCard key={recipe.id} recipe={recipe} />
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12">
                            <Users className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                            <h3 className="text-xl font-semibold text-gray-900 mb-2">No recipes in your feed yet</h3>
                            <p className="text-gray-600 mb-6">Start following other users or check out trending recipes!</p>
                            <button
                                onClick={() => setActiveTab('trending')}
                                className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Explore Trending Recipes
                            </button>
                        </div>
                    )}
                </div>
            )}

            {/* Share Recipe Modal */}
            {showShareModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold text-gray-900">Share Recipe</h3>
                            <button
                                onClick={() => setShowShareModal(false)}
                                className="text-gray-400 hover:text-gray-600"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                    Recipe: {recipeToShare?.recipe_name}
                                </label>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Share Level</label>
                                <select
                                    value={shareLevel}
                                    onChange={(e) => setShareLevel(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="public">Public - Anyone can see</option>
                                    <option value="friends">Friends Only</option>
                                    <option value="private">Private - Just for me</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Message (Optional)</label>
                                <textarea
                                    value={shareMessage}
                                    onChange={(e) => setShareMessage(e.target.value)}
                                    placeholder="Share your thoughts about this recipe..."
                                    rows={3}
                                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                        </div>

                        <div className="flex justify-end space-x-3 mt-6">
                            <button
                                onClick={() => setShowShareModal(false)}
                                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={submitShareRecipe}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Share Recipe
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CommunityFeed;