// SocialMediaImport.jsx - Complete Social Media Recipe Import Feature

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from './services/supabase';
import {
    Upload, Link, Camera, ChefHat, DollarSign, Clock,
    Zap, Heart, TrendingUp, Loader2, Check, X,
    Instagram, Video, Image, Sparkles, ArrowRight,
    Repeat, AlertCircle, Share2
} from 'lucide-react';

// Main Component
const SocialMediaImport = () => {
    const navigate = useNavigate();
    const [userId, setUserId] = useState(null);
    const [activeTab, setActiveTab] = useState('url');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    // URL Import State
    const [socialUrl, setSocialUrl] = useState('');
    const [urlPlatform, setUrlPlatform] = useState(null);

    // Image Upload State
    const [selectedImage, setSelectedImage] = useState(null);
    const [imagePreview, setImagePreview] = useState(null);

    // Recipe Results State
    const [importedRecipe, setImportedRecipe] = useState(null);
    const [alternatives, setAlternatives] = useState([]);
    const [selectedAlternative, setSelectedAlternative] = useState(null);
    const [showComparison, setShowComparison] = useState(false);

    // Trending Imports
    const [trendingImports, setTrendingImports] = useState([]);

    useEffect(() => {
        const fetchUser = async () => {
            try {
                const { data: { user }, error: userError } = await supabase.auth.getUser();
                if (userError || !user) {
                    navigate('/');
                    return;
                }
                setUserId(user.id);
                loadTrendingImports();
            } catch (error) {
                console.error('Error fetching user:', error);
                navigate('/');
            }
        };
        fetchUser();
    }, [navigate]);

    // Platform Detection
    const detectPlatform = (url) => {
        if (url.includes('tiktok.com')) return 'tiktok';
        if (url.includes('instagram.com')) return 'instagram';
        if (url.includes('youtube.com')) return 'youtube';
        if (url.includes('pinterest.com')) return 'pinterest';
        return null;
    };

    // URL Import Handler
    const handleUrlImport = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        const platform = detectPlatform(socialUrl);
        if (!platform) {
            setError('Please enter a valid TikTok, Instagram, YouTube, or Pinterest URL');
            return;
        }

        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/import-from-url', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    url: socialUrl,
                    create_alternatives: true,
                    alternative_types: ['healthier', 'budget', 'quick']
                })
            });

            const data = await response.json();
            if (response.ok) {
                setImportedRecipe(data.original_recipe);
                setAlternatives(data.alternatives || []);
                setSuccess('Recipe imported successfully!');
                setSocialUrl('');
            } else {
                setError(data.detail || 'Failed to import recipe');
            }
        } catch (err) {
            setError('Error importing recipe. Please try again.');
            console.error('Import error:', err);
        } finally {
            setLoading(false);
        }
    };

    // Image Upload Handler
    const handleImageUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            setError('Please upload an image file');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            setError('Image size must be less than 10MB');
            return;
        }

        setSelectedImage(file);
        setImagePreview(URL.createObjectURL(file));
    };

    const handleImageSubmit = async () => {
        if (!selectedImage) {
            setError('Please select an image first');
            return;
        }

        setLoading(true);
        setError('');
        setSuccess('');

        try {
            const formData = new FormData();
            formData.append('user_id', userId);
            formData.append('image', selectedImage);
            formData.append('create_alternatives', 'true');
            formData.append('alternative_types', JSON.stringify(['healthier', 'budget', 'quick']));

            const response = await fetch('http://localhost:8000/extract-from-image', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (response.ok) {
                setImportedRecipe(data.original_recipe);
                setAlternatives(data.alternatives || []);
                setSuccess(`Recipe extracted with ${Math.round(data.confidence * 100)}% confidence!`);
                setSelectedImage(null);
                setImagePreview(null);
            } else {
                setError(data.detail || 'Failed to extract recipe from image');
            }
        } catch (err) {
            setError('Error processing image. Please try again.');
            console.error('Image extraction error:', err);
        } finally {
            setLoading(false);
        }
    };

    // Create Alternative Handler
    const handleCreateAlternative = async (alternativeType) => {
        if (!importedRecipe) return;

        setLoading(true);
        try {
            const response = await fetch('http://localhost:8000/recreate-recipe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    original_recipe: importedRecipe,
                    alternative_type: alternativeType,
                    preserve_flavors: true
                })
            });

            const data = await response.json();
            if (response.ok) {
                setAlternatives([...alternatives, data.recipe]);
                setSuccess(`${alternativeType} alternative created!`);
            }
        } catch (err) {
            console.error('Alternative creation error:', err);
        } finally {
            setLoading(false);
        }
    };

    // Save Recipe Handler
    const handleSaveRecipe = async (recipe) => {
        try {
            // Add to favorites
            const response = await fetch('http://localhost:8000/add-favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    recipe_name: recipe.recipe_name,
                    recipe_id: recipe.id || `import_${Date.now()}`,
                    recipe_data: recipe,
                    source: 'social_import'
                })
            });

            if (response.ok) {
                setSuccess('Recipe saved to your favorites!');
            }
        } catch (err) {
            console.error('Save error:', err);
            setError('Failed to save recipe');
        }
    };

    // Load Trending Imports
    const loadTrendingImports = async () => {
        try {
            const response = await fetch('http://localhost:8000/trending-imports');
            if (response.ok) {
                const data = await response.json();
                setTrendingImports(data.trending || []);
            }
        } catch (err) {
            console.error('Error loading trending:', err);
        }
    };

    // Platform Icon Component
    const PlatformIcon = ({ platform }) => {
        const icons = {
            tiktok: <Video className="w-5 h-5" />,
            instagram: <Instagram className="w-5 h-5" />,
            youtube: <Video className="w-5 h-5" />,
            pinterest: <Image className="w-5 h-5" />
        };
        return icons[platform] || <Link className="w-5 h-5" />;
    };

    // Recipe Card Component
    const RecipeCard = ({ recipe, isAlternative = false, alternativeType = '' }) => (
        <div className={`bg-white rounded-xl shadow-lg p-6 ${isAlternative ? 'border-2 border-blue-200' : ''}`}>
            {isAlternative && (
                <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-blue-500" />
                    <span className="text-sm font-medium text-blue-700">
                        {alternativeType.charAt(0).toUpperCase() + alternativeType.slice(1)} Alternative
                    </span>
                </div>
            )}

            <h3 className="text-xl font-bold mb-3">{recipe.recipe_name}</h3>

            {recipe.description && (
                <p className="text-gray-600 mb-4">{recipe.description}</p>
            )}

            <div className="flex flex-wrap gap-4 mb-4 text-sm">
                <div className="flex items-center gap-1">
                    <Clock className="w-4 h-4 text-gray-500" />
                    <span>{parseInt(recipe.prep_time) + parseInt(recipe.cook_time)} min</span>
                </div>
                <div className="flex items-center gap-1">
                    <DollarSign className="w-4 h-4 text-gray-500" />
                    <span>{recipe.cost_estimate}</span>
                </div>
                <div className="flex items-center gap-1">
                    <Heart className="w-4 h-4 text-gray-500" />
                    <span>{recipe.macros?.calories} cal</span>
                </div>
            </div>

            <div className="flex gap-2 mb-4">
                {recipe.tags?.slice(0, 3).map((tag, idx) => (
                    <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded-full">
                        {tag}
                    </span>
                ))}
            </div>

            <div className="flex gap-2">
                <button
                    onClick={() => handleSaveRecipe(recipe)}
                    className="flex-1 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors"
                >
                    Save Recipe
                </button>
                <button
                    onClick={() => {
                        setSelectedAlternative(recipe);
                        setShowComparison(true);
                    }}
                    className="flex-1 bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition-colors"
                >
                    View Details
                </button>
            </div>
        </div>
    );

    // Comparison Modal Component
    const ComparisonModal = ({ original, alternative, onClose }) => {
        if (!original || !alternative) return null;

        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto p-6">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-bold">Recipe Comparison</h2>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        {/* Original Recipe */}
                        <div>
                            <h3 className="text-lg font-semibold mb-4 text-gray-700">Original</h3>
                            <div className="bg-gray-50 rounded-lg p-4">
                                <h4 className="font-medium mb-2">{original.recipe_name}</h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span>Cost:</span>
                                        <span className="font-medium">{original.cost_estimate}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Calories:</span>
                                        <span className="font-medium">{original.macros?.calories}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Time:</span>
                                        <span className="font-medium">
                                            {parseInt(original.prep_time) + parseInt(original.cook_time)} min
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Alternative Recipe */}
                        <div>
                            <h3 className="text-lg font-semibold mb-4 text-blue-700">
                                {alternative.alternative_type} Alternative
                            </h3>
                            <div className="bg-blue-50 rounded-lg p-4">
                                <h4 className="font-medium mb-2">{alternative.recipe_name}</h4>
                                <div className="space-y-2 text-sm">
                                    <div className="flex justify-between">
                                        <span>Cost:</span>
                                        <span className="font-medium">{alternative.cost_estimate}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Calories:</span>
                                        <span className="font-medium">{alternative.macros?.calories}</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Time:</span>
                                        <span className="font-medium">
                                            {parseInt(alternative.prep_time) + parseInt(alternative.cook_time)} min
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Key Changes */}
                    {alternative.modifications && (
                        <div className="mt-6 bg-yellow-50 rounded-lg p-4">
                            <h4 className="font-medium mb-2">Key Changes</h4>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-gray-600">Cost Difference:</span>
                                    <span className={`ml-2 font-medium ${
                                        alternative.modifications.cost_difference.startsWith('-')
                                            ? 'text-green-600'
                                            : 'text-red-600'
                                    }`}>
                                        {alternative.modifications.cost_difference}
                                    </span>
                                </div>
                                <div>
                                    <span className="text-gray-600">Calorie Difference:</span>
                                    <span className={`ml-2 font-medium ${
                                        alternative.modifications.calorie_difference.startsWith('-')
                                            ? 'text-green-600'
                                            : 'text-red-600'
                                    }`}>
                                        {alternative.modifications.calorie_difference}
                                    </span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold mb-2 flex items-center gap-3">
                    <Share2 className="w-8 h-8 text-blue-500" />
                    Import Recipe from Social Media
                </h1>
                <p className="text-gray-600">
                    Turn viral food videos into personalized recipes with healthier and budget-friendly alternatives
                </p>
            </div>

            {/* Tab Navigation */}
            <div className="flex gap-4 mb-6">
                <button
                    onClick={() => setActiveTab('url')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                        activeTab === 'url'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                >
                    <Link className="w-4 h-4" />
                    Import from URL
                </button>
                <button
                    onClick={() => setActiveTab('image')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                        activeTab === 'image'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                >
                    <Camera className="w-4 h-4" />
                    Upload Food Photo
                </button>
                <button
                    onClick={() => setActiveTab('trending')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                        activeTab === 'trending'
                            ? 'bg-blue-500 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                >
                    <TrendingUp className="w-4 h-4" />
                    Trending Imports
                </button>
            </div>

            {/* Alerts */}
            {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
                    <AlertCircle className="w-5 h-5" />
                    {error}
                </div>
            )}
            {success && (
                <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-green-700">
                    <Check className="w-5 h-5" />
                    {success}
                </div>
            )}

            {/* URL Import Tab */}
            {activeTab === 'url' && (
                <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Import from Social Media URL</h2>
                    <form onSubmit={handleUrlImport} className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Paste TikTok, Instagram, YouTube, or Pinterest URL
                            </label>
                            <div className="flex gap-2">
                                <input
                                    type="url"
                                    value={socialUrl}
                                    onChange={(e) => {
                                        setSocialUrl(e.target.value);
                                        setUrlPlatform(detectPlatform(e.target.value));
                                    }}
                                    placeholder="https://www.tiktok.com/@user/video/..."
                                    className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                    required
                                />
                                <button
                                    type="submit"
                                    disabled={loading || !socialUrl}
                                    className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
                                >
                                    {loading ? (
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                    ) : (
                                        <Upload className="w-4 h-4" />
                                    )}
                                    Import
                                </button>
                            </div>
                            {urlPlatform && (
                                <div className="mt-2 flex items-center gap-2 text-sm text-gray-600">
                                    <PlatformIcon platform={urlPlatform} />
                                    <span>Detected {urlPlatform} link</span>
                                </div>
                            )}
                        </div>
                    </form>

                    {/* Supported Platforms */}
                    <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                            <Video className="w-5 h-5 text-gray-600" />
                            <span className="text-sm font-medium">TikTok</span>
                        </div>
                        <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                            <Instagram className="w-5 h-5 text-gray-600" />
                            <span className="text-sm font-medium">Instagram</span>
                        </div>
                        <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                            <Video className="w-5 h-5 text-gray-600" />
                            <span className="text-sm font-medium">YouTube</span>
                        </div>
                        <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                            <Image className="w-5 h-5 text-gray-600" />
                            <span className="text-sm font-medium">Pinterest</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Image Upload Tab */}
            {activeTab === 'image' && (
                <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Extract Recipe from Food Photo</h2>

                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Upload a photo of the dish
                            </label>
                            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                                {imagePreview ? (
                                    <div className="space-y-4">
                                        <img
                                            src={imagePreview}
                                            alt="Preview"
                                            className="max-h-64 mx-auto rounded-lg"
                                        />
                                        <div className="flex gap-2 justify-center">
                                            <button
                                                onClick={() => {
                                                    setSelectedImage(null);
                                                    setImagePreview(null);
                                                }}
                                                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                                            >
                                                Remove
                                            </button>
                                            <button
                                                onClick={handleImageSubmit}
                                                disabled={loading}
                                                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 flex items-center gap-2"
                                            >
                                                {loading ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <Sparkles className="w-4 h-4" />
                                                )}
                                                Extract Recipe
                                            </button>
                                        </div>
                                    </div>
                                ) : (
                                    <div>
                                        <Camera className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                                        <input
                                            type="file"
                                            accept="image/*"
                                            onChange={handleImageUpload}
                                            className="hidden"
                                            id="image-upload"
                                        />
                                        <label
                                            htmlFor="image-upload"
                                            className="cursor-pointer px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 inline-block"
                                        >
                                            Choose Photo
                                        </label>
                                        <p className="mt-2 text-sm text-gray-500">
                                            Max file size: 10MB
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Trending Tab */}
            {activeTab === 'trending' && (
                <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
                    <h2 className="text-xl font-semibold mb-4">Trending Imported Recipes</h2>
                    <div className="grid gap-4">
                        {trendingImports.map((recipe, idx) => (
                            <div key={idx} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                                <div className="flex items-center gap-4">
                                    <PlatformIcon platform={recipe.source_platform} />
                                    <div>
                                        <h3 className="font-medium">{recipe.recipe_name}</h3>
                                        <div className="flex gap-2 text-sm text-gray-600">
                                            <span>{recipe.cuisine}</span>
                                            <span>•</span>
                                            <span>{recipe.import_count} imports</span>
                                        </div>
                                    </div>
                                </div>
                                <button
                                    onClick={() => window.open(recipe.original_url, '_blank')}
                                    className="px-3 py-1 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 text-sm"
                                >
                                    View Original
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Results Section */}
            {importedRecipe && (
                <div className="space-y-6">
                    <h2 className="text-2xl font-semibold">Imported Recipe</h2>

                    {/* Original Recipe */}
                    <RecipeCard recipe={importedRecipe} />

                    {/* Alternatives */}
                    {alternatives.length > 0 && (
                        <>
                            <h3 className="text-xl font-semibold mt-8 mb-4">Alternative Versions</h3>
                            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {alternatives.map((alt, idx) => (
                                    <RecipeCard
                                        key={idx}
                                        recipe={alt}
                                        isAlternative={true}
                                        alternativeType={alt.alternative_type}
                                    />
                                ))}
                            </div>
                        </>
                    )}

                    {/* Create More Alternatives */}
                    <div className="bg-gray-50 rounded-xl p-6">
                        <h3 className="text-lg font-semibold mb-4">Create More Alternatives</h3>
                        <div className="flex flex-wrap gap-2">
                            {['vegan', 'keto', 'gluten-free', 'dairy-free', 'paleo'].map(type => (
                                <button
                                    key={type}
                                    onClick={() => handleCreateAlternative(type)}
                                    disabled={loading || alternatives.some(a => a.alternative_type === type)}
                                    className="px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:text-gray-400"
                                >
                                    {type.charAt(0).toUpperCase() + type.slice(1)} Version
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {/* Comparison Modal */}
            {showComparison && (
                <ComparisonModal
                    original={importedRecipe}
                    alternative={selectedAlternative}
                    onClose={() => {
                        setShowComparison(false);
                        setSelectedAlternative(null);
                    }}
                />
            )}

            {/* Navigation */}
            <div className="mt-8 flex justify-center gap-4">
                <button
                    onClick={() => navigate('/home')}
                    className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
                >
                    Back to Home
                </button>
                <button
                    onClick={() => navigate('/generate')}
                    className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                    Generate More Recipes
                </button>
            </div>
        </div>
    );
};

export default SocialMediaImport;