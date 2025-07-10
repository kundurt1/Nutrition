import React, { useState, useEffect } from 'react';
import { Plus, Minus, Calendar, TrendingUp, Target, Utensils, X, Trash2 } from 'lucide-react';

const NutritionTracker = ({ userId }) => {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [dailyLogs, setDailyLogs] = useState([]);
  const [customEntryForm, setCustomEntryForm] = useState({
    show: false,
    food_name: '',
    calories: '',
    protein: '',
    carbs: '',
    fat: '',
    fiber: ''
  });
  const [loading, setLoading] = useState(false);
  const [macroTargets, setMacroTargets] = useState({
    calories: 2000,
    protein: 150,
    carbs: 200,
    fat: 70,
    fiber: 25
  });

  useEffect(() => {
    if (userId) {
      loadDailyNutrition();
    }
  }, [userId, selectedDate]);

  const loadDailyNutrition = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/daily-nutrition?user_id=${userId}&date=${selectedDate}`);
      if (response.ok) {
        const data = await response.json();
        setDailyLogs(data.logs || []);
      } else {
        console.error('Failed to load daily nutrition');
      }
    } catch (error) {
      console.error('Error loading daily nutrition:', error);
    } finally {
      setLoading(false);
    }
  };

  const addCustomEntry = async () => {
    try {
      const response = await fetch('http://localhost:8000/custom-entry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          food_name: customEntryForm.food_name,
          calories: parseFloat(customEntryForm.calories) || 0,
          protein: parseFloat(customEntryForm.protein) || 0,
          carbs: parseFloat(customEntryForm.carbs) || 0,
          fat: parseFloat(customEntryForm.fat) || 0,
          fiber: parseFloat(customEntryForm.fiber) || 0,
          date: selectedDate
        })
      });

      if (response.ok) {
        setCustomEntryForm({
          show: false,
          food_name: '',
          calories: '',
          protein: '',
          carbs: '',
          fat: '',
          fiber: ''
        });
        await loadDailyNutrition();

        // Show success message
        showSuccessMessage('Custom food entry added!');
      } else {
        alert('Failed to add custom entry');
      }
    } catch (error) {
      console.error('Error adding custom entry:', error);
      alert('Error adding custom entry');
    }
  };

  const removeEntry = async (entryId, entryType) => {
    if (!window.confirm('Are you sure you want to remove this entry?')) {
      return;
    }

    try {
      let endpoint = '';
      if (entryType === 'meal') {
        endpoint = `http://localhost:8000/nutrition-entry/${entryId}?user_id=${userId}&entry_type=meal`;
      } else {
        endpoint = `http://localhost:8000/custom-entry/${entryId}?user_id=${userId}&entry_type=custom`;
      }

      const response = await fetch(endpoint, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadDailyNutrition();
        showSuccessMessage('Entry removed successfully!');
      } else {
        alert('Failed to remove entry');
      }
    } catch (error) {
      console.error('Error removing entry:', error);
      alert('Error removing entry');
    }
  };

  const showSuccessMessage = (message) => {
    // Create and show success notification
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

  const calculateTotals = () => {
    const totals = {
      calories: 0,
      protein: 0,
      carbs: 0,
      fat: 0,
      fiber: 0,
      cost: 0
    };

    dailyLogs.forEach(log => {
      if (log.type === 'meal' && log.recipe_data) {
        const macros = log.recipe_data.macros || {};
        totals.calories += parseFloat(macros.calories) || 0;
        totals.protein += parseFloat(String(macros.protein).replace('g', '')) || 0;
        totals.carbs += parseFloat(String(macros.carbs).replace('g', '')) || 0;
        totals.fat += parseFloat(String(macros.fat).replace('g', '')) || 0;
        totals.fiber += parseFloat(String(macros.fiber).replace('g', '')) || 0;
        totals.cost += parseFloat(log.recipe_data.cost_estimate) || 0;
      } else if (log.type === 'custom') {
        totals.calories += log.calories || 0;
        totals.protein += log.protein || 0;
        totals.carbs += log.carbs || 0;
        totals.fat += log.fat || 0;
        totals.fiber += log.fiber || 0;
      }
    });

    return totals;
  };

  const totals = calculateTotals();

  const MacroBar = ({ label, current, target, unit = 'g', color = 'blue' }) => {
    const percentage = Math.min((current / target) * 100, 100);
    const isOver = current > target;

    const colorClasses = {
      blue: isOver ? 'bg-red-500' : 'bg-blue-500',
      red: isOver ? 'bg-red-500' : 'bg-red-500',
      yellow: isOver ? 'bg-red-500' : 'bg-yellow-500',
      purple: isOver ? 'bg-red-500' : 'bg-purple-500',
      green: isOver ? 'bg-red-500' : 'bg-green-500'
    };

    return (
        <div className="mb-3">
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium text-gray-700">{label}</span>
            <span className={`text-sm ${isOver ? 'text-red-600' : 'text-gray-600'}`}>
            {Math.round(current)}{unit} / {target}{unit}
          </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
                className={`h-2 rounded-full transition-all duration-300 ${colorClasses[color]}`}
                style={{ width: `${Math.min(percentage, 100)}%` }}
            />
          </div>
          {isOver && (
              <div className="text-xs text-red-600 mt-1">
                {Math.round(current - target)}{unit} over target
              </div>
          )}
        </div>
    );
  };

  const navigateDate = (direction) => {
    const currentDate = new Date(selectedDate);
    currentDate.setDate(currentDate.getDate() + direction);
    setSelectedDate(currentDate.toISOString().split('T')[0]);
  };

  const formatDisplayDate = (dateString) => {
    const date = new Date(dateString);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (dateString === today.toISOString().split('T')[0]) {
      return 'Today';
    } else if (dateString === yesterday.toISOString().split('T')[0]) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', {
        weekday: 'long',
        month: 'short',
        day: 'numeric'
      });
    }
  };

  return (
      <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-sm">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <Utensils className="w-6 h-6 mr-3 text-green-600" />
              Nutrition Tracker
            </h2>
            <p className="text-gray-600">Track your daily nutrition and reach your goals</p>
          </div>

          <div className="flex items-center space-x-4">
            {/* Date Navigation */}
            <div className="flex items-center space-x-2">
              <button
                  onClick={() => navigateDate(-1)}
                  className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>

              <div className="text-center min-w-[120px]">
                <div className="font-semibold text-gray-900">{formatDisplayDate(selectedDate)}</div>
                <div className="text-sm text-gray-500">{selectedDate}</div>
              </div>

              <button
                  onClick={() => navigateDate(1)}
                  className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />

            <button
                onClick={() => setCustomEntryForm({ ...customEntryForm, show: true })}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Food
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Daily Summary */}
          <div className="lg:col-span-2">
            <div className="bg-gray-50 rounded-lg p-6 mb-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <Target className="w-5 h-5 mr-2 text-blue-600" />
                Daily Progress for {formatDisplayDate(selectedDate)}
              </h3>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center">
                  <div className="text-3xl font-bold text-blue-600">{Math.round(totals.calories)}</div>
                  <div className="text-sm text-gray-600">Calories</div>
                  <div className="text-xs text-gray-500">
                    {Math.round(macroTargets.calories - totals.calories)} remaining
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-3xl font-bold text-green-600">${totals.cost.toFixed(2)}</div>
                  <div className="text-sm text-gray-600">Daily Cost</div>
                  <div className="text-xs text-gray-500">
                    {dailyLogs.length} entries logged
                  </div>
                </div>
              </div>

              <MacroBar label="Protein" current={totals.protein} target={macroTargets.protein} color="red" />
              <MacroBar label="Carbs" current={totals.carbs} target={macroTargets.carbs} color="yellow" />
              <MacroBar label="Fat" current={totals.fat} target={macroTargets.fat} color="purple" />
              <MacroBar label="Fiber" current={totals.fiber} target={macroTargets.fiber} color="green" />
            </div>

            {/* Food Log */}
            <div className="bg-white border border-gray-200 rounded-lg">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Food Log</h3>
              </div>

              <div className="divide-y divide-gray-200">
                {loading ? (
                    <div className="p-6 text-center text-gray-500">
                      <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                      Loading...
                    </div>
                ) : dailyLogs.length === 0 ? (
                    <div className="p-6 text-center text-gray-500">
                      <Utensils className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p className="font-medium">No food logged for this day</p>
                      <p className="text-sm">Double-click recipes to add them or use the "Add Food" button!</p>
                    </div>
                ) : (
                    dailyLogs.map((log, index) => (
                        <div key={`${log.type}-${log.id}-${index}`} className="p-4 hover:bg-gray-50 transition-colors">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <h4 className="font-medium text-gray-900">
                                  {log.type === 'meal'
                                      ? (log.recipe_data?.recipe_name || 'Recipe')
                                      : log.food_name}
                                </h4>
                                <span className={`px-2 py-1 text-xs rounded-full ${
                                    log.type === 'meal'
                                        ? 'bg-blue-100 text-blue-800'
                                        : 'bg-green-100 text-green-800'
                                }`}>
                            {log.type === 'meal' ? 'Recipe' : 'Custom'}
                          </span>
                              </div>

                              <div className="flex flex-wrap gap-4 mt-2 text-sm text-gray-600">
                          <span className="font-medium">
                            {log.type === 'meal'
                                ? Math.round(log.recipe_data?.macros?.calories || 0)
                                : Math.round(log.calories || 0)
                            } cal
                          </span>

                                {log.type === 'meal' && log.recipe_data?.macros && (
                                    <>
                                      <span>P: {String(log.recipe_data.macros.protein).replace('g', '')}g</span>
                                      <span>C: {String(log.recipe_data.macros.carbs).replace('g', '')}g</span>
                                      <span>F: {String(log.recipe_data.macros.fat).replace('g', '')}g</span>
                                    </>
                                )}

                                {log.type === 'custom' && (
                                    <>
                                      <span>P: {Math.round(log.protein)}g</span>
                                      <span>C: {Math.round(log.carbs)}g</span>
                                      <span>F: {Math.round(log.fat)}g</span>
                                      {log.fiber > 0 && <span>Fiber: {Math.round(log.fiber)}g</span>}
                                    </>
                                )}

                                {log.type === 'meal' && log.recipe_data?.cost_estimate && (
                                    <span className="text-green-600 font-medium">
                              ${parseFloat(log.recipe_data.cost_estimate).toFixed(2)}
                            </span>
                                )}
                              </div>

                              {log.type === 'meal' && log.recipe_data?.cuisine && (
                                  <div className="mt-2">
                            <span className="inline-block bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded">
                              {log.recipe_data.cuisine}
                            </span>
                                  </div>
                              )}

                              {log.logged_at && (
                                  <div className="mt-1 text-xs text-gray-400">
                                    Logged: {new Date(log.logged_at).toLocaleTimeString()}
                                  </div>
                              )}
                            </div>

                            <button
                                onClick={() => removeEntry(log.id, log.type)}
                                className="ml-4 p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                                title="Remove entry"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                    ))
                )}
              </div>
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Quick Stats */}
            <div className="bg-gradient-to-br from-blue-50 to-green-50 rounded-lg p-6 border border-blue-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-blue-600" />
                Quick Stats
              </h3>

              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Remaining Calories</span>
                  <span className={`text-sm font-medium ${
                      macroTargets.calories - totals.calories >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                  {Math.round(macroTargets.calories - totals.calories)}
                </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Protein Goal</span>
                  <span className={`text-sm font-medium ${
                      totals.protein >= macroTargets.protein ? 'text-green-600' : 'text-orange-600'
                  }`}>
                  {Math.round((totals.protein / macroTargets.protein) * 100)}%
                </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Entries Logged</span>
                  <span className="text-sm font-medium text-blue-600">
                  {dailyLogs.length}
                </span>
                </div>

                <div className="flex justify-between">
                  <span className="text-sm text-gray-600">Daily Budget</span>
                  <span className={`text-sm font-medium ${
                      totals.cost <= 30 ? 'text-green-600' : 'text-red-600'
                  }`}>
                  ${totals.cost.toFixed(2)} / $30.00
                </span>
                </div>
              </div>
            </div>

            {/* Macro Targets Card */}
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">🎯 Daily Targets</h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span>Calories:</span>
                  <span className="font-medium">{macroTargets.calories}</span>
                </div>
                <div className="flex justify-between">
                  <span>Protein:</span>
                  <span className="font-medium">{macroTargets.protein}g</span>
                </div>
                <div className="flex justify-between">
                  <span>Carbs:</span>
                  <span className="font-medium">{macroTargets.carbs}g</span>
                </div>
                <div className="flex justify-between">
                  <span>Fat:</span>
                  <span className="font-medium">{macroTargets.fat}g</span>
                </div>
                <div className="flex justify-between">
                  <span>Fiber:</span>
                  <span className="font-medium">{macroTargets.fiber}g</span>
                </div>
              </div>
            </div>

            {/* Tips */}
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 Tips</h3>
              <ul className="space-y-2 text-sm text-gray-700">
                <li className="flex items-start">
                  <span className="text-yellow-600 mr-2">•</span>
                  Double-click generated recipes to add them automatically
                </li>
                <li className="flex items-start">
                  <span className="text-yellow-600 mr-2">•</span>
                  Aim for balanced macros throughout the day
                </li>
                <li className="flex items-start">
                  <span className="text-yellow-600 mr-2">•</span>
                  Track everything for better insights
                </li>
                <li className="flex items-start">
                  <span className="text-yellow-600 mr-2">•</span>
                  Use custom entries for quick additions
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* Custom Entry Modal */}
        {customEntryForm.show && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Add Custom Food Entry</h3>
                  <button
                      onClick={() => setCustomEntryForm({...customEntryForm, show: false})}
                      className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Food Name *</label>
                    <input
                        type="text"
                        value={customEntryForm.food_name}
                        onChange={(e) => setCustomEntryForm({...customEntryForm, food_name: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="e.g. Apple, Chicken Breast, Protein Bar"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Calories *</label>
                      <input
                          type="number"
                          value={customEntryForm.calories}
                          onChange={(e) => setCustomEntryForm({...customEntryForm, calories: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="0"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Protein (g)</label>
                      <input
                          type="number"
                          step="0.1"
                          value={customEntryForm.protein}
                          onChange={(e) => setCustomEntryForm({...customEntryForm, protein: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="0"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Carbs (g)</label>
                      <input
                          type="number"
                          step="0.1"
                          value={customEntryForm.carbs}
                          onChange={(e) => setCustomEntryForm({...customEntryForm, carbs: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="0"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Fat (g)</label>
                      <input
                          type="number"
                          step="0.1"
                          value={customEntryForm.fat}
                          onChange={(e) => setCustomEntryForm({...customEntryForm, fat: e.target.value})}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          placeholder="0"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fiber (g)</label>
                    <input
                        type="number"
                        step="0.1"
                        value={customEntryForm.fiber}
                        onChange={(e) => setCustomEntryForm({...customEntryForm, fiber: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        placeholder="0"
                    />
                  </div>
                </div>

                <div className="flex justify-end space-x-3 mt-6">
                  <button
                      onClick={() => setCustomEntryForm({...customEntryForm, show: false})}
                      className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                      onClick={addCustomEntry}
                      disabled={!customEntryForm.food_name || !customEntryForm.calories}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Add Entry
                  </button>
                </div>
              </div>
            </div>
        )}
      </div>
  );
};

export default NutritionTracker;