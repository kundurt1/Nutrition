// NutritionPage.jsx - Complete version with AI Custom Meal Analyzer
import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import NutritionTracker from '../components/NutritionTracker';
import CustomMealAnalyzer from '../components/CustomMealAnalyzer';
import {
  Calendar,
  TrendingUp,
  Target,
  Award,
  BarChart3,
  Home,
  Settings,
  Brain,
  Calculator,
  Sparkles
} from 'lucide-react';

const NutritionPage = () => {
  const navigate = useNavigate();
  const [userId, setUserId] = useState(null);
  const [activeTab, setActiveTab] = useState('tracker');
  const [weeklyData, setWeeklyData] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [customEntryMethod, setCustomEntryMethod] = useState('manual');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [goals, setGoals] = useState({
    daily_calories: 2000,
    daily_protein: 150,
    daily_carbs: 200,
    daily_fat: 70,
    daily_fiber: 25,
    daily_budget: 30.00
  });
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

  const loadNutritionData = async () => {
    setLoading(true);
    try {
      // Load weekly summary
      try {
        const weeklyResponse = await fetch(`http://localhost:8000/weekly-nutrition-summary/${userId}`);
        if (weeklyResponse.ok) {
          const weeklyData = await weeklyResponse.json();
          setWeeklyData(weeklyData.weekly_summary);
        }
      } catch (error) {
        console.log('Weekly summary not available yet');
      }

      // Load dashboard data
      try {
        const dashboardResponse = await fetch(`http://localhost:8000/nutrition-dashboard/${userId}?days=7`);
        if (dashboardResponse.ok) {
          const dashboardData = await dashboardResponse.json();
          setDashboardData(dashboardData.dashboard);
        }
      } catch (error) {
        console.log('Dashboard data not available yet');
      }
    } catch (error) {
      console.error('Error loading nutrition data:', error);
    } finally {
      setLoading(false);
    }
  };

  // after userId is set
  useEffect(() => {
    if (userId) {
      loadGoals();
      loadNutritionData();
    }
  }, [userId, refreshTrigger]);

  const loadGoals = async () => {
    setLoading(true);
    try {
      // Load goals
      const res = await fetch(`http://localhost:8000/users/${userId}/goals`);
      if (res.ok) {
        const json = await res.json();
        if (json?.goals) setGoals(json.goals);
      } else {
        console.error('Failed to load goals', await res.text());
      }

      // Load dashboard data (gracefully if endpoint not ready)
      const dashboardResponse = await fetch(
          `http://localhost:8000/nutrition-dashboard/${userId}?days=7`
      );
      if (dashboardResponse.ok) {
        const dashboardJson = await dashboardResponse.json();
        setDashboardData(dashboardJson.dashboard);
      } else {
        console.log('Dashboard data not available yet');
      }
    } catch (error) {
      console.error('Error loading goals/dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveGoals = async () => {
    try {
      const res = await fetch(`http://localhost:8000/users/${userId}/goals`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          daily_calories: goals.daily_calories,
          daily_protein: goals.daily_protein,
          daily_carbs: goals.daily_carbs,
          daily_fat: goals.daily_fat,
          daily_fiber: goals.daily_fiber,
          daily_budget: goals.daily_budget,
        })
      });
      if (!res.ok) throw new Error('Failed to save');
      alert('Goals saved successfully!');
    } catch (e) {
      console.error(e);
      alert('Failed to save goals');
    }
  };

  const handleMealAdded = useCallback(() => {
    // Refresh data when a meal is added via AI
    setRefreshTrigger(prev => prev + 1);
  }, []);

  const WeeklyOverview = () => (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Calorie Summary */}
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6 border border-blue-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-600 text-sm font-medium">Avg Daily Calories</p>
                <p className="text-2xl font-bold text-blue-900">
                  {weeklyData?.daily_averages?.calories || 0}
                </p>
                <p className="text-blue-600 text-xs">
                  Goal: {goals.daily_calories}
                </p>
              </div>
              <div className="text-blue-500">
                <Target className="w-8 h-8" />
              </div>
            </div>
            {weeklyData?.goal_compliance?.calories && (
                <div className="mt-4">
                  <div className="flex justify-between text-xs text-blue-600">
                    <span>Goal Progress</span>
                    <span>{weeklyData.goal_compliance.calories}%</span>
                  </div>
                  <div className="w-full bg-blue-200 rounded-full h-2 mt-1">
                    <div
                        className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${Math.min(weeklyData.goal_compliance.calories, 100)}%` }}
                    />
                  </div>
                </div>
            )}
          </div>

          {/* Protein Summary */}
          <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg p-6 border border-red-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-red-600 text-sm font-medium">Avg Daily Protein</p>
                <p className="text-2xl font-bold text-red-900">
                  {weeklyData?.daily_averages?.protein || 0}g
                </p>
                <p className="text-red-600 text-xs">
                  Goal: {goals.daily_protein}g
                </p>
              </div>
              <div className="text-red-500">
                <Award className="w-8 h-8" />
              </div>
            </div>
          </div>

          {/* Cost Summary */}
          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6 border border-green-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-600 text-sm font-medium">Avg Daily Cost</p>
                <p className="text-2xl font-bold text-green-900">
                  ${weeklyData?.daily_averages?.cost || 0}
                </p>
                <p className="text-green-600 text-xs">
                  Budget: ${goals.daily_budget}
                </p>
              </div>
              <div className="text-green-500">
                <BarChart3 className="w-8 h-8" />
              </div>
            </div>
          </div>

          {/* Entries Summary */}
          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6 border border-purple-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-600 text-sm font-medium">Entries Logged</p>
                <p className="text-2xl font-bold text-purple-900">
                  {weeklyData?.entries_logged || 0}
                </p>
                <p className="text-purple-600 text-xs">
                  This week
                </p>
              </div>
              <div className="text-purple-500">
                <Calendar className="w-8 h-8" />
              </div>
            </div>
          </div>
        </div>

        {/* Tips Section */}
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-6 border border-purple-200">
          <h3 className="text-lg font-semibold text-purple-900 mb-4">💡 Nutrition Tips</h3>

          <div className="space-y-3 text-sm">
            <div className="bg-white/70 rounded-lg p-3 border border-purple-200">
              <span className="font-medium text-purple-800">🥩 Protein Boost:</span>
              <span className="text-purple-700 ml-2">
              Try adding more lean meats, eggs, or protein powder to reach your daily protein goal.
            </span>
            </div>

            <div className="bg-white/70 rounded-lg p-3 border border-purple-200">
              <span className="font-medium text-purple-800">💰 Budget Tip:</span>
              <span className="text-purple-700 ml-2">
              Consider meal prepping and buying ingredients in bulk to reduce daily food costs.
            </span>
            </div>

            <div className="bg-white/70 rounded-lg p-3 border border-purple-200">
              <span className="font-medium text-purple-800">📱 Consistency:</span>
              <span className="text-purple-700 ml-2">
              Try to log at least 2-3 meals per day for better nutrition insights and progress tracking.
            </span>
            </div>

            <div className="bg-white/70 rounded-lg p-3 border border-purple-200">
              <span className="font-medium text-purple-800">🤖 AI Tip:</span>
              <span className="text-purple-700 ml-2">
              Use our AI meal analyzer to quickly log meals - just describe what you ate!
            </span>
            </div>

            <div className="bg-white/70 rounded-lg p-3 border border-purple-200">
              <span className="font-medium text-purple-800">⭐ Pro Tip:</span>
              <span className="text-purple-700 ml-2">
              Double-click any generated recipe to instantly add it to your nutrition log with all macro and cost data!
            </span>
            </div>
          </div>
        </div>
      </div>
  );

  const GoalsSettings = () => (
      <div className="space-y-6">
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
            <Target className="w-5 h-5 mr-2 text-blue-600" />
            Nutrition Goals
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Daily Calories
              </label>
              <input
                  type="number"
                  value={goals.daily_calories}
                  onChange={(e) => setGoals({...goals, daily_calories: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Daily Protein (g)
              </label>
              <input
                  type="number"
                  value={goals.daily_protein}
                  onChange={(e) => setGoals({...goals, daily_protein: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Daily Carbs (g)
              </label>
              <input
                  type="number"
                  value={goals.daily_carbs}
                  onChange={(e) => setGoals({...goals, daily_carbs: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Daily Fat (g)
              </label>
              <input
                  type="number"
                  value={goals.daily_fat}
                  onChange={(e) => setGoals({...goals, daily_fat: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Daily Fiber (g)
              </label>
              <input
                  type="number"
                  value={goals.daily_fiber}
                  onChange={(e) => setGoals({...goals, daily_fiber: parseInt(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Daily Budget ($)
              </label>
              <input
                  type="number"
                  step="0.01"
                  value={goals.daily_budget}
                  onChange={(e) => setGoals({...goals, daily_budget: parseFloat(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>

          <div className="mt-6">
            <button
                onClick={saveGoals}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Save Goals
            </button>
          </div>
        </div>

        {/* Goal Progress */}
        <div className="bg-white rounded-lg p-6 shadow-sm border">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 Goal Progress</h3>

          <div className="space-y-4">
            {[
              { name: 'Calories', current: weeklyData?.daily_averages?.calories || 0, target: goals.daily_calories },
              { name: 'Protein', current: weeklyData?.daily_averages?.protein || 0, target: goals.daily_protein },
              { name: 'Carbs', current: weeklyData?.daily_averages?.carbs || 0, target: goals.daily_carbs },
              { name: 'Fat', current: weeklyData?.daily_averages?.fat || 0, target: goals.daily_fat }
            ].map((macro) => {
              const percentage = Math.min((macro.current / macro.target) * 100, 100);
              return (
                  <div key={macro.name} className="flex items-center">
                    <div className="w-20 text-sm font-medium text-gray-700">
                      {macro.name}
                    </div>
                    <div className="flex-1 mx-4">
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div
                            className={`h-3 rounded-full transition-all duration-500 ${
                                percentage >= 90 ? 'bg-green-500' :
                                    percentage >= 70 ? 'bg-yellow-500' :
                                        percentage >= 50 ? 'bg-orange-500' : 'bg-red-500'
                            }`}
                            style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                    <div className="w-24 text-sm text-gray-600 text-right">
                      {macro.current}/{macro.target} ({percentage.toFixed(0)}%)
                    </div>
                  </div>
              );
            })}
          </div>
        </div>
      </div>
  );

  // Move DailyTracker content directly into the render to avoid re-creation
  const renderDailyTracker = () => {
    return (
        <div className="space-y-6">
          {/* Custom Entry Method Selector */}
          <div className="bg-white rounded-lg p-6 shadow-sm border">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Custom Entry</h3>

            {/* Method Toggle */}
            <div className="flex gap-4 mb-6">
              <button
                  onClick={() => setCustomEntryMethod('manual')}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
                      customEntryMethod === 'manual'
                          ? 'border-blue-500 bg-blue-50 text-blue-700'
                          : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                  }`}
              >
                <Calculator className="w-5 h-5" />
                <div>
                  <span className="font-medium">Manual Entry</span>
                  <span className="text-xs block opacity-75">Enter exact values</span>
                </div>
              </button>

              <button
                  onClick={() => setCustomEntryMethod('ai')}
                  className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all ${
                      customEntryMethod === 'ai'
                          ? 'border-purple-500 bg-purple-50 text-purple-700'
                          : 'border-gray-200 bg-white text-gray-600 hover:border-gray-300'
                  }`}
              >
                <Brain className="w-5 h-5" />
                <div>
                  <span className="font-medium">AI Analysis</span>
                  <span className="text-xs block opacity-75">Describe your meal</span>
                </div>
              </button>
            </div>

            {/* Description based on selected method */}
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              {customEntryMethod === 'manual' ? (
                  <div className="flex items-start gap-3">
                    <Calculator className="w-5 h-5 text-blue-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">Manual Entry Mode</p>
                      <p className="text-xs text-gray-600 mt-1">
                        Perfect when you know the exact nutritional values. Enter calories, protein, carbs, fat, and fiber manually.
                      </p>
                    </div>
                  </div>
              ) : (
                  <div className="flex items-start gap-3">
                    <Sparkles className="w-5 h-5 text-purple-600 mt-0.5" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">AI-Powered Analysis</p>
                      <p className="text-xs text-gray-600 mt-1">
                        Simply describe your meal in natural language. Our AI will analyze it and calculate the nutrition facts.
                        The more detailed your description, the more accurate the results!
                      </p>
                    </div>
                  </div>
              )}
            </div>

            {/* Entry Component based on selection */}
            {customEntryMethod === 'ai' ? (
                <div key="ai-entry">
                  <CustomMealAnalyzer
                      userId={userId}
                      onMealAdded={handleMealAdded}
                      mode="inline"
                  />
                </div>
            ) : (
                <div className="text-center py-4 text-gray-600" key="manual-entry">
                  <p className="text-sm">Manual entry is available in the Daily Tracker below</p>
                  <p className="text-xs mt-1">Click "Add Custom Entry" in the tracker to enter values manually</p>
                </div>
            )}
          </div>

          {/* Existing Nutrition Tracker Component */}
          {userId && (
              <NutritionTracker
                  userId={userId}
                  macroTargets={goals}
                  key={refreshTrigger}
              />
          )}
        </div>
    );
  };

  if (loading) {
    return (
        <div className="max-w-6xl mx-auto p-6">
          <div className="flex items-center justify-center h-64">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p className="text-gray-600">Loading your nutrition data...</p>
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
            <h1 className="text-3xl font-bold text-gray-900">🍎 Nutrition Dashboard</h1>
            <p className="text-gray-600 mt-2">Track your daily nutrition, costs, and reach your health goals</p>
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
                onClick={() => navigate('/generate')}
                className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Generate Recipes
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-gray-200 mb-8">
          <button
              onClick={() => setActiveTab('tracker')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'tracker'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            📱 Daily Tracker
          </button>
          <button
              onClick={() => setActiveTab('overview')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'overview'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            📊 Weekly Overview
          </button>
          <button
              onClick={() => setActiveTab('goals')}
              className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'goals'
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
          >
            🎯 Goals & Settings
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'tracker' && renderDailyTracker()}
        {activeTab === 'overview' && <WeeklyOverview />}
        {activeTab === 'goals' && <GoalsSettings />}

        {/* Quick Actions Footer */}
        <div className="mt-12 bg-gradient-to-r from-blue-50 to-green-50 rounded-lg p-6 border border-blue-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🚀 Quick Actions</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
                onClick={() => navigate('/generate')}
                className="flex flex-col items-center p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all"
            >
              <div className="text-2xl mb-2">🍳</div>
              <span className="font-medium text-gray-900">Generate Recipes</span>
              <span className="text-sm text-gray-600 text-center mt-1">
              Create new recipes with nutrition data
            </span>
            </button>

            <button
                onClick={() => navigate('/grocery')}
                className="flex flex-col items-center p-4 bg-white rounded-lg border border-gray-200 hover:border-green-300 hover:shadow-sm transition-all"
            >
              <div className="text-2xl mb-2">🛒</div>
              <span className="font-medium text-gray-900">Grocery List</span>
              <span className="text-sm text-gray-600 text-center mt-1">
              View and manage your shopping list
            </span>
            </button>

            <button
                onClick={() => navigate('/favorites')}
                className="flex flex-col items-center p-4 bg-white rounded-lg border border-gray-200 hover:border-red-300 hover:shadow-sm transition-all"
            >
              <div className="text-2xl mb-2">❤️</div>
              <span className="font-medium text-gray-900">Favorites</span>
              <span className="text-sm text-gray-600 text-center mt-1">
              Access your saved favorite recipes
            </span>
            </button>
          </div>
        </div>

        {/* AI Feature Banner */}
        <div className="mt-8 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg p-6 border border-purple-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">🤖 AI-Powered Nutrition Tracking</h3>
          <p className="text-gray-700 text-sm mb-3">
            Experience the future of nutrition tracking with our intelligent features:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div className="flex items-start gap-2">
              <span className="text-purple-600">✨</span>
              <div>
                <span className="font-medium">Natural Language Input:</span> Just describe what you ate
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-purple-600">🎯</span>
              <div>
                <span className="font-medium">Smart Analysis:</span> AI calculates accurate nutrition facts
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-purple-600">📊</span>
              <div>
                <span className="font-medium">Confidence Scoring:</span> Know how accurate the analysis is
              </div>
            </div>
            <div className="flex items-start gap-2">
              <span className="text-purple-600">✏️</span>
              <div>
                <span className="font-medium">Editable Results:</span> Fine-tune values before saving
              </div>
            </div>
          </div>
        </div>

        {/* Motivational Footer */}
        <div className="mt-8 text-center text-gray-500">
          <p className="text-sm">
            💪 Keep tracking your nutrition to reach your health goals!
            <br />
            <span className="text-xs">
            Pro tip: The more detailed your meal descriptions, the more accurate the AI analysis!
          </span>
          </p>
        </div>
      </div>
  );
};

export default NutritionPage;