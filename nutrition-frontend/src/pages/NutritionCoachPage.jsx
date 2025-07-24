// src/pages/NutritionCoachPage.jsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import {
    Target, TrendingUp, Award, BarChart3, Calendar, Settings,
    Activity, Zap, Brain, Users, AlertCircle, CheckCircle,
    ArrowUp, ArrowDown, Minus, Home, RefreshCw
} from 'lucide-react';

const NutritionCoachPage = () => {
    const navigate = useNavigate();
    const [userId, setUserId] = useState(null);
    const [activeTab, setActiveTab] = useState('dashboard');
    const [loading, setLoading] = useState(false);

    // Coach data state
    const [coachingData, setCoachingData] = useState(null);
    const [userProfile, setUserProfile] = useState(null);
    const [progressHistory, setProgressHistory] = useState([]);
    const [weeklyInsights, setWeeklyInsights] = useState(null);
    const [goalProgress, setGoalProgress] = useState(null);

    // UI state
    const [showProgressModal, setShowProgressModal] = useState(false);
    const [showGoalUpdate, setShowGoalUpdate] = useState(false);

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
            loadCoachingDashboard();
        }
    }, [userId]);

    const loadCoachingDashboard = async () => {
        setLoading(true);
        try {
            const response = await fetch(`http://localhost:8000/coaching-dashboard/${userId}`);
            if (response.ok) {
                const data = await response.json();
                setCoachingData(data.data);
                setUserProfile(data.data.user_profile);
                setWeeklyInsights(data.data.weekly_insights);
            }
        } catch (error) {
            console.error('Error loading coaching dashboard:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadGoalProgress = async () => {
        try {
            const response = await fetch(`http://localhost:8000/goal-progress/${userId}?weeks=12`);
            if (response.ok) {
                const data = await response.json();
                setGoalProgress(data.data);
                setProgressHistory(data.data.current_progress?.history || []);
            }
        } catch (error) {
            console.error('Error loading goal progress:', error);
        }
    };

    const runWeeklyAnalysis = async () => {
        try {
            setLoading(true);
            const response = await fetch(`http://localhost:8000/weekly-analysis?user_id=${userId}`, {
                method: 'POST'
            });
            if (response.ok) {
                const data = await response.json();
                setWeeklyInsights(data.data);
                await loadCoachingDashboard(); // Refresh dashboard
            }
        } catch (error) {
            console.error('Error running weekly analysis:', error);
        } finally {
            setLoading(false);
        }
    };

    // Dashboard Overview Component
    const CoachingDashboard = () => (
        <div className="space-y-6">
            {/* Header with Goal Status */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-xl p-6 text-white">
                <div className="flex items-center justify-between">
                    <div>
                        <h2 className="text-2xl font-bold mb-2">🎯 Your Fitness Journey</h2>
                        <p className="text-blue-100">
                            Goal: {userProfile?.goal?.replace('_', ' ').toUpperCase()} •
                            Phase: {userProfile?.phase?.replace('_', ' ')} •
                            Week {userProfile?.week_in_phase}
                        </p>
                    </div>
                    <div className="text-right">
                        <div className="text-sm text-blue-200">Timeline</div>
                        <div className="text-xl font-bold">{userProfile?.timeline_weeks} weeks</div>
                    </div>
                </div>
            </div>

            {/* Current Macro Targets */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {coachingData?.current_macros && Object.entries(coachingData.current_macros).map(([key, value]) => {
                    if (key === 'meal_distribution') return null;

                    const getIcon = (macroKey) => {
                        switch(macroKey) {
                            case 'calories': return '🔥';
                            case 'protein': return '💪';
                            case 'carbs': return '🌾';
                            case 'fat': return '🥑';
                            case 'fiber': return '🥬';
                            default: return '📊';
                        }
                    };

                    return (
                        <div key={key} className="bg-white rounded-lg p-4 shadow-sm border">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-2xl">{getIcon(key)}</span>
                                <span className="text-xs text-gray-500 uppercase tracking-wide">{key}</span>
                            </div>
                            <div className="text-2xl font-bold text-gray-900">
                                {typeof value === 'number' ? value.toFixed(key === 'calories' ? 0 : 1) : value}
                                {key === 'calories' ? '' : 'g'}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Progress Summary */}
            {coachingData?.progress_summary && (
                <div className="bg-white rounded-lg p-6 shadow-sm border">
                    <h3 className="text-lg font-semibold mb-4 flex items-center">
                        <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
                        Recent Progress
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <ProgressCard
                            title="Weight Change"
                            value={coachingData.progress_summary.weight_change}
                            unit="lbs"
                            trend={coachingData.progress_summary.weight_change > 0 ? 'up' : 'down'}
                        />
                        <ProgressCard
                            title="Adherence Rate"
                            value={`${(coachingData.progress_summary.adherence_rate * 100).toFixed(0)}`}
                            unit="%"
                            trend={coachingData.progress_summary.adherence_rate > 0.8 ? 'up' : 'neutral'}
                        />
                        <ProgressCard
                            title="Energy Level"
                            value={coachingData.progress_summary.energy_level}
                            unit="/10"
                            trend={coachingData.progress_summary.energy_level > 7 ? 'up' : 'neutral'}
                        />
                    </div>
                </div>
            )}

            {/* AI Insights */}
            {weeklyInsights && (
                <div className="bg-white rounded-lg p-6 shadow-sm border">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold flex items-center">
                            <Brain className="w-5 h-5 mr-2 text-purple-600" />
                            AI Coach Insights
                        </h3>
                        <button
                            onClick={runWeeklyAnalysis}
                            disabled={loading}
                            className="flex items-center px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg hover:bg-purple-200 transition-colors text-sm"
                        >
                            <RefreshCw className={`w-4 h-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                            Update
                        </button>
                    </div>

                    {weeklyInsights.key_insights && (
                        <div className="space-y-3">
                            {weeklyInsights.key_insights.map((insight, index) => (
                                <div key={index} className="flex items-start space-x-3 p-3 bg-purple-50 rounded-lg">
                                    <CheckCircle className="w-5 h-5 text-purple-600 mt-0.5 flex-shrink-0" />
                                    <p className="text-gray-700">{insight}</p>
                                </div>
                            ))}
                        </div>
                    )}

                    {weeklyInsights.areas_of_concern && weeklyInsights.areas_of_concern.length > 0 && (
                        <div className="mt-4 space-y-2">
                            <h4 className="font-medium text-orange-800">Areas to Focus On:</h4>
                            {weeklyInsights.areas_of_concern.map((concern, index) => (
                                <div key={index} className="flex items-start space-x-3 p-3 bg-orange-50 rounded-lg">
                                    <AlertCircle className="w-5 h-5 text-orange-600 mt-0.5 flex-shrink-0" />
                                    <p className="text-gray-700">{concern}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <ActionCard
                    icon={<Target className="w-6 h-6" />}
                    title="Log Progress"
                    description="Update your weight, energy, and adherence"
                    onClick={() => setShowProgressModal(true)}
                    color="blue"
                />
                <ActionCard
                    icon={<Activity className="w-6 h-6" />}
                    title="Generate Meal"
                    description="Get goal-optimized recipe suggestions"
                    onClick={() => setActiveTab('recipes')}
                    color="green"
                />
                <ActionCard
                    icon={<Settings className="w-6 h-6" />}
                    title="Adjust Goals"
                    description="Update your fitness goals and timeline"
                    onClick={() => setShowGoalUpdate(true)}
                    color="purple"
                />
            </div>
        </div>
    );

    // Goal-Oriented Recipe Generator
    const GoalRecipeGenerator = () => {
        const [mealType, setMealType] = useState('breakfast');
        const [trainingDay, setTrainingDay] = useState(false);
        const [generatedRecipe, setGeneratedRecipe] = useState(null);
        const [recipeLoading, setRecipeLoading] = useState(false);

        const generateGoalRecipe = async () => {
            setRecipeLoading(true);
            try {
                const response = await fetch('http://localhost:8000/generate-goal-recipe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        meal_type: mealType,
                        training_day: trainingDay
                    })
                });

                if (response.ok) {
                    const data = await response.json();
                    setGeneratedRecipe(data.data);
                }
            } catch (error) {
                console.error('Error generating goal recipe:', error);
            } finally {
                setRecipeLoading(false);
            }
        };

        return (
            <div className="space-y-6">
                <div className="bg-white rounded-lg p-6 shadow-sm border">
                    <h3 className="text-lg font-semibold mb-4 flex items-center">
                        <Zap className="w-5 h-5 mr-2 text-yellow-600" />
                        Goal-Optimized Recipe Generator
                    </h3>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Meal Type</label>
                            <select
                                value={mealType}
                                onChange={(e) => setMealType(e.target.value)}
                                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                                <option value="breakfast">Breakfast</option>
                                <option value="lunch">Lunch</option>
                                <option value="dinner">Dinner</option>
                                <option value="pre_workout">Pre-Workout</option>
                                <option value="post_workout">Post-Workout</option>
                                <option value="snack">Snack</option>
                            </select>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Training Day</label>
                            <div className="flex items-center space-x-4 h-12">
                                <label className="flex items-center">
                                    <input
                                        type="radio"
                                        name="trainingDay"
                                        checked={trainingDay === true}
                                        onChange={() => setTrainingDay(true)}
                                        className="mr-2"
                                    />
                                    Yes
                                </label>
                                <label className="flex items-center">
                                    <input
                                        type="radio"
                                        name="trainingDay"
                                        checked={trainingDay === false}
                                        onChange={() => setTrainingDay(false)}
                                        className="mr-2"
                                    />
                                    No
                                </label>
                            </div>
                        </div>

                        <div className="flex items-end">
                            <button
                                onClick={generateGoalRecipe}
                                disabled={recipeLoading}
                                className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center"
                            >
                                {recipeLoading ? (
                                    <>
                                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                                        Generating...
                                    </>
                                ) : (
                                    'Generate Recipe'
                                )}
                            </button>
                        </div>
                    </div>

                    {generatedRecipe && (
                        <div className="border-t pt-6">
                            <div className="mb-4">
                                <h4 className="text-xl font-bold text-gray-900 mb-2">{generatedRecipe.recipe.name}</h4>
                                <div className="flex items-center space-x-4 text-sm text-gray-600">
                                    <span>Goal Alignment: {(generatedRecipe.goal_alignment_score * 100).toFixed(0)}%</span>
                                    <span>•</span>
                                    <span>Training Day: {trainingDay ? 'Yes' : 'No'}</span>
                                </div>
                            </div>

                            {/* Macro breakdown */}
                            <div className="grid grid-cols-4 gap-4 mb-6">
                                {Object.entries(generatedRecipe.meal_macros).map(([key, value]) => (
                                    <div key={key} className="text-center p-3 bg-gray-50 rounded-lg">
                                        <div className="text-xs text-gray-500 uppercase tracking-wide">{key}</div>
                                        <div className="text-lg font-bold text-gray-900">
                                            {typeof value === 'number' ? value.toFixed(key === 'calories' ? 0 : 1) : value}
                                            {key === 'calories' ? '' : 'g'}
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Recipe details */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div>
                                    <h5 className="font-semibold text-gray-900 mb-3">Ingredients</h5>
                                    <ul className="space-y-1">
                                        {generatedRecipe.recipe.ingredients?.map((ingredient, index) => (
                                            <li key={index} className="text-gray-700">• {ingredient}</li>
                                        ))}
                                    </ul>
                                </div>

                                <div>
                                    <h5 className="font-semibold text-gray-900 mb-3">Directions</h5>
                                    <ol className="space-y-2">
                                        {generatedRecipe.recipe.directions?.map((step, index) => (
                                            <li key={index} className="text-gray-700">
                                                <span className="font-medium text-blue-600">{index + 1}.</span> {step}
                                            </li>
                                        ))}
                                    </ol>
                                </div>
                            </div>

                            {/* Coaching notes */}
                            {generatedRecipe.coaching_notes && generatedRecipe.coaching_notes.length > 0 && (
                                <div className="mt-6 p-4 bg-blue-50 rounded-lg">
                                    <h5 className="font-semibold text-blue-900 mb-2 flex items-center">
                                        <Brain className="w-4 h-4 mr-2" />
                                        Coach Notes
                                    </h5>
                                    <ul className="space-y-1">
                                        {generatedRecipe.coaching_notes.map((note, index) => (
                                            <li key={index} className="text-blue-800 text-sm">• {note}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        );
    };

    // Progress Tracking Component
    const ProgressTracking = () => {
        const [progressForm, setProgressForm] = useState({
            weight: '',
            body_fat_estimate: '',
            energy_level: 5,
            adherence_score: 0.8,
            mood_rating: 5,
            sleep_quality: 5,
            notes: ''
        });

        const handleProgressSubmit = async (e) => {
            e.preventDefault();
            try {
                const response = await fetch('http://localhost:8000/log-progress', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: userId,
                        ...progressForm,
                        weight: progressForm.weight ? parseFloat(progressForm.weight) : null,
                        body_fat_estimate: progressForm.body_fat_estimate ? parseFloat(progressForm.body_fat_estimate) : null
                    })
                });

                if (response.ok) {
                    setProgressForm({
                        weight: '',
                        body_fat_estimate: '',
                        energy_level: 5,
                        adherence_score: 0.8,
                        mood_rating: 5,
                        sleep_quality: 5,
                        notes: ''
                    });
                    loadCoachingDashboard(); // Refresh dashboard
                    alert('Progress logged successfully!');
                }
            } catch (error) {
                console.error('Error logging progress:', error);
            }
        };

        return (
            <div className="space-y-6">
                <div className="bg-white rounded-lg p-6 shadow-sm border">
                    <h3 className="text-lg font-semibold mb-6 flex items-center">
                        <BarChart3 className="w-5 h-5 mr-2 text-green-600" />
                        Log Your Progress
                    </h3>

                    <form onSubmit={handleProgressSubmit} className="space-y-6">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Weight (lbs)
                                </label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={progressForm.weight}
                                    onChange={(e) => setProgressForm({...progressForm, weight: e.target.value})}
                                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Enter current weight"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Body Fat % (optional)
                                </label>
                                <input
                                    type="number"
                                    step="0.1"
                                    value={progressForm.body_fat_estimate}
                                    onChange={(e) => setProgressForm({...progressForm, body_fat_estimate: e.target.value})}
                                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                    placeholder="Enter body fat %"
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Energy Level (1-10)
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="10"
                                    value={progressForm.energy_level}
                                    onChange={(e) => setProgressForm({...progressForm, energy_level: parseInt(e.target.value)})}
                                    className="w-full"
                                />
                                <div className="text-center text-sm text-gray-600 mt-1">
                                    {progressForm.energy_level}/10
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Diet Adherence (0-100%)
                                </label>
                                <input
                                    type="range"
                                    min="0"
                                    max="1"
                                    step="0.1"
                                    value={progressForm.adherence_score}
                                    onChange={(e) => setProgressForm({...progressForm, adherence_score: parseFloat(e.target.value)})}
                                    className="w-full"
                                />
                                <div className="text-center text-sm text-gray-600 mt-1">
                                    {(progressForm.adherence_score * 100).toFixed(0)}%
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-2">
                                    Sleep Quality (1-10)
                                </label>
                                <input
                                    type="range"
                                    min="1"
                                    max="10"
                                    value={progressForm.sleep_quality}
                                    onChange={(e) => setProgressForm({...progressForm, sleep_quality: parseInt(e.target.value)})}
                                    className="w-full"
                                />
                                <div className="text-center text-sm text-gray-600 mt-1">
                                    {progressForm.sleep_quality}/10
                                </div>
                            </div>
                        </div>

                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Notes (optional)
                            </label>
                            <textarea
                                value={progressForm.notes}
                                onChange={(e) => setProgressForm({...progressForm, notes: e.target.value})}
                                rows={3}
                                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                placeholder="How are you feeling? Any challenges or wins to note?"
                            />
                        </div>

                        <button
                            type="submit"
                            className="w-full px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors font-medium"
                        >
                            Log Progress
                        </button>
                    </form>
                </div>

                {/* Progress History */}
                {progressHistory.length > 0 && (
                    <div className="bg-white rounded-lg p-6 shadow-sm border">
                        <h3 className="text-lg font-semibold mb-4">Progress History</h3>
                        <div className="space-y-3">
                            {progressHistory.slice(-5).map((entry, index) => (
                                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div>
                                        <div className="font-medium">{new Date(entry.recorded_at).toLocaleDateString()}</div>
                                        <div className="text-sm text-gray-600">
                                            Weight: {entry.weight}lbs • Energy: {entry.energy_level}/10
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <div className="text-sm text-gray-600">Adherence</div>
                                        <div className="font-medium">{(entry.adherence_score * 100).toFixed(0)}%</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        );
    };

    // Helper Components
    const ProgressCard = ({ title, value, unit, trend }) => (
        <div className="text-center">
            <div className="flex items-center justify-center mb-2">
                {trend === 'up' && <ArrowUp className="w-4 h-4 text-green-600 mr-1" />}
                {trend === 'down' && <ArrowDown className="w-4 h-4 text-red-600 mr-1" />}
                {trend === 'neutral' && <Minus className="w-4 h-4 text-gray-600 mr-1" />}
                <span className="text-sm text-gray-600">{title}</span>
            </div>
            <div className="text-2xl font-bold text-gray-900">
                {value}{unit}
            </div>
        </div>
    );

    const ActionCard = ({ icon, title, description, onClick, color }) => {
        const colorClasses = {
            blue: 'bg-blue-50 hover:bg-blue-100 text-blue-700',
            green: 'bg-green-50 hover:bg-green-100 text-green-700',
            purple: 'bg-purple-50 hover:bg-purple-100 text-purple-700'
        };

        return (
            <button
                onClick={onClick}
                className={`p-6 rounded-lg text-left transition-colors ${colorClasses[color]}`}
            >
                <div className="flex items-center mb-3">
                    {icon}
                    <h3 className="font-semibold ml-2">{title}</h3>
                </div>
                <p className="text-sm opacity-80">{description}</p>
            </button>
        );
    };

    // Progress Modal Component
    const ProgressModal = () => {
        if (!showProgressModal) return null;

        return (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-semibold">Quick Progress Log</h3>
                        <button
                            onClick={() => setShowProgressModal(false)}
                            className="text-gray-400 hover:text-gray-600"
                        >
                            ✕
                        </button>
                    </div>
                    <ProgressTracking />
                </div>
            </div>
        );
    };

    if (loading && !coachingData) {
        return (
            <div className="max-w-6xl mx-auto p-6">
                <div className="flex items-center justify-center h-64">
                    <div className="text-center">
                        <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                        <p className="text-gray-600">Loading your AI nutrition coach...</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl mx-auto p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center">
                        <Brain className="w-8 h-8 mr-3 text-purple-600" />
                        AI Nutrition Coach
                    </h1>
                    <p className="text-gray-600 mt-2">Your personal AI-powered fitness and nutrition guide</p>
                </div>

                <div className="flex gap-3">
                    <button
                        onClick={() => navigate('/home')}
                        className="flex items-center px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                        <Home className="w-4 h-4 mr-2" />
                        Home
                    </button>
                    <button
                        onClick={runWeeklyAnalysis}
                        disabled={loading}
                        className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
                    >
                        <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Update Analysis
                    </button>
                </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-gray-200 mb-8">
                {[
                    { id: 'dashboard', label: '🎯 Dashboard', icon: Target },
                    { id: 'recipes', label: '🍳 Goal Recipes', icon: Zap },
                    { id: 'progress', label: '📊 Progress', icon: BarChart3 },
                    { id: 'insights', label: '🧠 AI Insights', icon: Brain }
                ].map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                            activeTab === tab.id
                                ? 'border-purple-500 text-purple-600'
                                : 'border-transparent text-gray-500 hover:text-gray-700'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            {activeTab === 'dashboard' && <CoachingDashboard />}
            {activeTab === 'recipes' && <GoalRecipeGenerator />}
            {activeTab === 'progress' && <ProgressTracking />}
            {activeTab === 'insights' && (
                <div className="text-center py-12">
                    <Brain className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                    <p className="text-gray-600">Advanced AI insights coming soon...</p>
                </div>
            )}

            {/* Modals */}
            <ProgressModal />
        </div>
    );
};

export default NutritionCoachPage;