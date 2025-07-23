// src/pages/CommunityPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import CommunityFeed from '../components/CommunityFeed';
import {
    Users,
    Share2,
    Trophy,
    TrendingUp,
    UserPlus,
    Search,
    Star,
    ChefHat,
    Heart,
    MessageCircle,
    Bookmark
} from 'lucide-react';

const CommunityPage = () => {
    const navigate = useNavigate();
    const [userId, setUserId] = useState(null);
    const [activeTab, setActiveTab] = useState('feed');
    const [stats, setStats] = useState({
        totalUsers: 0,
        totalSharedRecipes: 0,
        totalLikes: 0,
        totalComments: 0
    });
    const [topContributors, setTopContributors] = useState([]);
    const [trendingRecipes, setTrendingRecipes] = useState([]);
    const [myProfile, setMyProfile] = useState(null);
    const [loading, setLoading] = useState(false);

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
            loadCommunityStats();
            loadMyProfile();
        }
    }, [userId]);

    const loadCommunityStats = async () => {
        try {
            // In a real implementation, you'd fetch these from your backend
            setStats({
                totalUsers: 1247,
                totalSharedRecipes: 3892,
                totalLikes: 18734,
                totalComments: 5621
            });

            setTopContributors([
                {
                    id: '1',
                    username: 'chef_maria',
                    display_name: 'Chef Maria Rodriguez',
                    recipes_shared: 45,
                    total_likes: 892,
                    avatar_color: 'from-pink-500 to-rose-600'
                },
                {
                    id: '2',
                    username: 'healthy_eats',
                    display_name: 'Sarah Johnson',
                    recipes_shared: 38,
                    total_likes: 756,
                    avatar_color: 'from-green-500 to-emerald-600'
                },
                {
                    id: '3',
                    username: 'budget_chef',
                    display_name: 'Mike Chen',
                    recipes_shared: 32,
                    total_likes: 643,
                    avatar_color: 'from-blue-500 to-indigo-600'
                }
            ]);

            setTrendingRecipes([
                {
                    id: '1',
                    recipe_name: '15-Minute Garlic Shrimp Pasta',
                    shared_by: { display_name: 'Chef Maria', username: 'chef_maria' },
                    likes_count: 234,
                    comments_count: 45,
                    rating_average: 4.8,
                    tags: ['quick', 'seafood', 'pasta'],
                    created_at: '2024-01-15'
                },
                {
                    id: '2',
                    recipe_name: 'Buddha Bowl with Tahini Dressing',
                    shared_by: { display_name: 'Sarah Johnson', username: 'healthy_eats' },
                    likes_count: 189,
                    comments_count: 32,
                    rating_average: 4.6,
                    tags: ['healthy', 'vegan', 'bowl'],
                    created_at: '2024-01-14'
                }
            ]);
        } catch (error) {
            console.error('Error loading community stats:', error);
        }
    };

    const loadMyProfile = async () => {
        try {
            const response = await fetch(`http://localhost:8000/user-profile/${userId}?current_user_id=${userId}`);
            if (response.ok) {
                const profileData = await response.json();
                setMyProfile(profileData);
            }
        } catch (error) {
            console.error('Error loading profile:', error);
        }
    };

    const StatsCard = ({ icon: Icon, title, value, color }) => (
        <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
            <div className="flex items-center">
                <div className={`p-3 rounded-lg ${color}`}>
                    <Icon className="w-6 h-6 text-white" />
                </div>
                <div className="ml-4">
                    <p className="text-sm font-medium text-gray-600">{title}</p>
                    <p className="text-2xl font-bold text-gray-900">{value.toLocaleString()}</p>
                </div>
            </div>
        </div>
    );

    const ContributorCard = ({ contributor }) => (
        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center space-x-3">
                <div className={`w-12 h-12 bg-gradient-to-br ${contributor.avatar_color} rounded-full flex items-center justify-center text-white font-bold text-lg`}>
                    {contributor.display_name.charAt(0)}
                </div>
                <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{contributor.display_name}</h3>
                    <p className="text-sm text-gray-600">@{contributor.username}</p>
                    <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
            <span className="flex items-center">
              <ChefHat className="w-3 h-3 mr-1" />
                {contributor.recipes_shared} recipes
            </span>
                        <span className="flex items-center">
              <Heart className="w-3 h-3 mr-1" />
                            {contributor.total_likes} likes
            </span>
                    </div>
                </div>
                <button className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    <UserPlus className="w-4 h-4" />
                </button>
            </div>
        </div>
    );

    const TrendingRecipeCard = ({ recipe }) => (
        <div className="bg-white rounded-lg p-4 shadow-sm border border-gray-200 hover:shadow-md transition-shadow cursor-pointer">
            <div className="flex items-start justify-between mb-3">
                <h3 className="font-semibold text-gray-900 text-sm leading-tight">{recipe.recipe_name}</h3>
                <div className="flex items-center text-yellow-500 ml-2">
                    <Star className="w-4 h-4 fill-current" />
                    <span className="text-xs font-medium ml-1">{recipe.rating_average}</span>
                </div>
            </div>

            <p className="text-xs text-gray-600 mb-3">by {recipe.shared_by.display_name}</p>

            <div className="flex items-center justify-between text-xs text-gray-500">
                <div className="flex items-center space-x-3">
          <span className="flex items-center">
            <Heart className="w-3 h-3 mr-1" />
              {recipe.likes_count}
          </span>
                    <span className="flex items-center">
            <MessageCircle className="w-3 h-3 mr-1" />
                        {recipe.comments_count}
          </span>
                </div>
                <span>{new Date(recipe.created_at).toLocaleDateString()}</span>
            </div>

            <div className="flex flex-wrap gap-1 mt-2">
                {recipe.tags.slice(0, 2).map((tag, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
            #{tag}
          </span>
                ))}
            </div>
        </div>
    );

    const MyProfileSummary = () => (
        <div className="bg-gradient-to-br from-blue-50 to-indigo-100 rounded-lg p-6 border border-blue-200">
            <div className="flex items-center space-x-4 mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-xl">
                    {myProfile?.display_name?.charAt(0) || 'U'}
                </div>
                <div>
                    <h2 className="text-xl font-bold text-gray-900">{myProfile?.display_name || 'Your Profile'}</h2>
                    <p className="text-gray-600">@{myProfile?.username || 'username'}</p>
                </div>
            </div>

            <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{myProfile?.recipes_shared || 0}</div>
                    <div className="text-xs text-gray-600">Recipes Shared</div>
                </div>
                <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{myProfile?.followers_count || 0}</div>
                    <div className="text-xs text-gray-600">Followers</div>
                </div>
                <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">{myProfile?.following_count || 0}</div>
                    <div className="text-xs text-gray-600">Following</div>
                </div>
            </div>

            <button
                onClick={() => navigate('/profile')}
                className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
                View Full Profile
            </button>
        </div>
    );

    const QuickActions = () => (
        <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-3">
                <button
                    onClick={() => navigate('/generate')}
                    className="w-full flex items-center justify-center space-x-2 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                    <ChefHat className="w-5 h-5" />
                    <span>Generate & Share Recipe</span>
                </button>

                <button
                    onClick={() => setActiveTab('feed')}
                    className="w-full flex items-center justify-center space-x-2 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                    <Users className="w-5 h-5" />
                    <span>Browse Community</span>
                </button>

                <button
                    onClick={() => navigate('/favorites')}
                    className="w-full flex items-center justify-center space-x-2 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                >
                    <Bookmark className="w-5 h-5" />
                    <span>View Saved Recipes</span>
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-50">
            <div className="max-w-7xl mx-auto p-6">
                {/* Header */}
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                            <Users className="w-8 h-8 mr-3 text-blue-600" />
                            Recipe Community
                        </h1>
                        <p className="text-gray-600 mt-2">Connect, share, and discover amazing recipes from fellow food enthusiasts</p>
                    </div>

                    <div className="flex gap-3">
                        <button
                            onClick={() => navigate('/home')}
                            className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                            🏠 Home
                        </button>
                        <button
                            onClick={() => navigate('/generate')}
                            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            <Share2 className="w-4 h-4 mr-2" />
                            Share Recipe
                        </button>
                    </div>
                </div>

                {/* Tab Navigation */}
                <div className="flex border-b border-gray-200 mb-8">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                            activeTab === 'overview'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        📊 Community Overview
                    </button>
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
                        onClick={() => setActiveTab('discover')}
                        className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                            activeTab === 'discover'
                                ? 'border-blue-500 text-blue-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        🔍 Discover Users
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
                </div>

                {/* Overview Tab */}
                {activeTab === 'overview' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Main Content */}
                        <div className="lg:col-span-2 space-y-6">
                            {/* Community Stats */}
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 mb-4">Community Stats</h2>
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <StatsCard
                                        icon={Users}
                                        title="Total Members"
                                        value={stats.totalUsers}
                                        color="bg-blue-500"
                                    />
                                    <StatsCard
                                        icon={ChefHat}
                                        title="Recipes Shared"
                                        value={stats.totalSharedRecipes}
                                        color="bg-green-500"
                                    />
                                    <StatsCard
                                        icon={Heart}
                                        title="Total Likes"
                                        value={stats.totalLikes}
                                        color="bg-red-500"
                                    />
                                    <StatsCard
                                        icon={MessageCircle}
                                        title="Comments"
                                        value={stats.totalComments}
                                        color="bg-purple-500"
                                    />
                                </div>
                            </div>

                            {/* Top Contributors */}
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                                    <Trophy className="w-5 h-5 mr-2 text-yellow-500" />
                                    Top Contributors This Month
                                </h2>
                                <div className="grid gap-4">
                                    {topContributors.map((contributor, index) => (
                                        <div key={contributor.id} className="relative">
                                            {index === 0 && (
                                                <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-500 text-white rounded-full flex items-center justify-center text-xs font-bold z-10">
                                                    👑
                                                </div>
                                            )}
                                            <ContributorCard contributor={contributor} />
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Recent Activity */}
                            <div>
                                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
                                    <TrendingUp className="w-5 h-5 mr-2 text-green-500" />
                                    Recent Community Activity
                                </h2>
                                <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                    <div className="space-y-4">
                                        <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
                                            <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-sm">
                                                👨‍🍳
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-sm"><strong>Chef Maria</strong> shared a new recipe: "Spicy Thai Basil Chicken"</p>
                                                <p className="text-xs text-gray-500">2 hours ago</p>
                                            </div>
                                            <Heart className="w-4 h-4 text-red-500" />
                                            <span className="text-sm font-medium">23</span>
                                        </div>

                                        <div className="flex items-center space-x-3 p-3 bg-blue-50 rounded-lg">
                                            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white text-sm">
                                                👩‍🍳
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-sm"><strong>Sarah Johnson</strong> commented on "Buddha Bowl Recipe"</p>
                                                <p className="text-xs text-gray-500">4 hours ago</p>
                                            </div>
                                            <MessageCircle className="w-4 h-4 text-blue-500" />
                                        </div>

                                        <div className="flex items-center space-x-3 p-3 bg-purple-50 rounded-lg">
                                            <div className="w-8 h-8 bg-purple-500 rounded-full flex items-center justify-center text-white text-sm">
                                                👨‍🍳
                                            </div>
                                            <div className="flex-1">
                                                <p className="text-sm"><strong>Mike Chen</strong> followed <strong>Healthy Eats</strong></p>
                                                <p className="text-xs text-gray-500">6 hours ago</p>
                                            </div>
                                            <UserPlus className="w-4 h-4 text-purple-500" />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Sidebar */}
                        <div className="space-y-6">
                            {/* My Profile Summary */}
                            <MyProfileSummary />

                            {/* Quick Actions */}
                            <QuickActions />

                            {/* Trending Recipes */}
                            <div>
                                <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                                    🔥 Trending This Week
                                </h3>
                                <div className="space-y-3">
                                    {trendingRecipes.map(recipe => (
                                        <TrendingRecipeCard key={recipe.id} recipe={recipe} />
                                    ))}
                                </div>
                            </div>

                            {/* Community Tips */}
                            <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-lg p-6 border border-yellow-200">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 Community Tips</h3>
                                <div className="space-y-3 text-sm">
                                    <div className="flex items-start space-x-2">
                                        <span className="text-yellow-600">•</span>
                                        <span>Share your favorite recipes to build your following</span>
                                    </div>
                                    <div className="flex items-start space-x-2">
                                        <span className="text-yellow-600">•</span>
                                        <span>Comment on recipes to engage with the community</span>
                                    </div>
                                    <div className="flex items-start space-x-2">
                                        <span className="text-yellow-600">•</span>
                                        <span>Follow users whose cooking style you admire</span>
                                    </div>
                                    <div className="flex items-start space-x-2">
                                        <span className="text-yellow-600">•</span>
                                        <span>Use tags to make your recipes discoverable</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Community Feed Tab */}
                {activeTab === 'feed' && (
                    <CommunityFeed />
                )}

                {/* Discover Tab */}
                {activeTab === 'discover' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
                                <div className="flex items-center space-x-4 mb-6">
                                    <Search className="w-5 h-5 text-gray-400" />
                                    <input
                                        type="text"
                                        placeholder="Search for users, cuisines, or cooking styles..."
                                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    />
                                    <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                                        Search
                                    </button>
                                </div>
                            </div>

                            <div className="grid gap-6">
                                <h2 className="text-xl font-bold text-gray-900">Suggested Users to Follow</h2>
                                <div className="grid gap-4">
                                    {topContributors.map(contributor => (
                                        <div key={contributor.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center space-x-4">
                                                    <div className={`w-16 h-16 bg-gradient-to-br ${contributor.avatar_color} rounded-full flex items-center justify-center text-white font-bold text-xl`}>
                                                        {contributor.display_name.charAt(0)}
                                                    </div>
                                                    <div>
                                                        <h3 className="text-lg font-semibold text-gray-900">{contributor.display_name}</h3>
                                                        <p className="text-gray-600">@{contributor.username}</p>
                                                        <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                                                            <span>{contributor.recipes_shared} recipes</span>
                                                            <span>{contributor.total_likes} likes</span>
                                                            <span>245 followers</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <button className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2">
                                                    <UserPlus className="w-4 h-4" />
                                                    <span>Follow</span>
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">Browse by Interest</h3>
                                <div className="space-y-2">
                                    {['Healthy Cooking', 'Budget Meals', 'Quick & Easy', 'Vegetarian', 'Baking', 'International Cuisine'].map(interest => (
                                        <button key={interest} className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-lg transition-colors">
                                            #{interest}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}

                {/* Trending Tab */}
                {activeTab === 'trending' && (
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        <div className="lg:col-span-2">
                            <h2 className="text-xl font-bold text-gray-900 mb-6">🔥 Trending Recipes This Week</h2>
                            <div className="grid gap-6">
                                {trendingRecipes.map(recipe => (
                                    <div key={recipe.id} className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
                                        <div className="flex items-start justify-between mb-4">
                                            <div>
                                                <h3 className="text-lg font-semibold text-gray-900">{recipe.recipe_name}</h3>
                                                <p className="text-gray-600">by {recipe.shared_by.display_name}</p>
                                            </div>
                                            <div className="flex items-center text-yellow-500">
                                                <Star className="w-5 h-5 fill-current" />
                                                <span className="font-medium ml-1">{recipe.rating_average}</span>
                                            </div>
                                        </div>

                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center space-x-6 text-sm text-gray-500">
                        <span className="flex items-center">
                          <Heart className="w-4 h-4 mr-1" />
                            {recipe.likes_count} likes
                        </span>
                                                <span className="flex items-center">
                          <MessageCircle className="w-4 h-4 mr-1" />
                                                    {recipe.comments_count} comments
                        </span>
                                            </div>
                                            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
                                                View Recipe
                                            </button>
                                        </div>

                                        <div className="flex flex-wrap gap-2 mt-4">
                                            {recipe.tags.map((tag, index) => (
                                                <span key={index} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                          #{tag}
                        </span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-6">
                            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                                <h3 className="text-lg font-semibold text-gray-900 mb-4">🏆 Weekly Leaderboard</h3>
                                <div className="space-y-3">
                                    {topContributors.slice(0, 5).map((contributor, index) => (
                                        <div key={contributor.id} className="flex items-center space-x-3">
                                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold text-sm ${
                                                index === 0 ? 'bg-yellow-500' :
                                                    index === 1 ? 'bg-gray-400' :
                                                        index === 2 ? 'bg-amber-600' : 'bg-gray-300'
                                            }`}>
                                                {index + 1}
                                            </div>
                                            <div className="flex-1">
                                                <p className="font-medium text-gray-900">{contributor.display_name}</p>
                                                <p className="text-xs text-gray-500">{contributor.total_likes} likes this week</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default CommunityPage;