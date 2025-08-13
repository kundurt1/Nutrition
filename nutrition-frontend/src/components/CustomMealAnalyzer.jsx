// components/CustomMealAnalyzer.jsx
import React, { useState } from 'react';
import {
    AlertCircle,
    Loader2,
    CheckCircle,
    Edit2,
    Save,
    X,
    Info,
    Sparkles
} from 'lucide-react';

const CustomMealAnalyzer = ({ userId, onMealAdded, mode = 'button' }) => {
    // mode can be 'button' (shows button that opens modal) or 'inline' (shows form directly)
    const [isOpen, setIsOpen] = useState(mode === 'inline');
    const [mealDescription, setMealDescription] = useState('');
    const [servings, setServings] = useState(1);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analyzedNutrition, setAnalyzedNutrition] = useState(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editedNutrition, setEditedNutrition] = useState(null);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');

    const resetForm = () => {
        setMealDescription('');
        setServings(1);
        setAnalyzedNutrition(null);
        setEditedNutrition(null);
        setIsEditing(false);
        setError('');
    };

    const handleAnalyzeMeal = async () => {
        if (!mealDescription.trim()) {
            setError('Please describe your meal');
            return;
        }

        setIsAnalyzing(true);
        setError('');

        try {
            const response = await fetch('http://localhost:8000/analyze-custom-meal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    description: mealDescription,
                    user_id: userId,
                    servings: servings
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Failed to analyze meal');
            }

            const data = await response.json();
            setAnalyzedNutrition(data.nutrition);
            setEditedNutrition({ ...data.nutrition });
            setSuccessMessage('Meal analyzed successfully! Review and edit if needed.');
        } catch (error) {
            console.error('Error analyzing meal:', error);
            setError(error.message || 'Failed to analyze meal. Please try again.');
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleSaveMeal = async () => {
        const nutritionToSave = isEditing ? editedNutrition : analyzedNutrition;

        try {
            const response = await fetch('http://localhost:8000/save-analyzed-meal', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    nutrition: nutritionToSave,
                    date: new Date().toISOString().split('T')[0]
                })
            });

            if (!response.ok) {
                throw new Error('Failed to save meal');
            }

            const data = await response.json();

            if (onMealAdded) {
                onMealAdded(data.entry);
            }

            // Reset form
            if (mode === 'button') {
                setIsOpen(false);
            }
            resetForm();
            setSuccessMessage('Meal added to your nutrition tracker!');

            setTimeout(() => setSuccessMessage(''), 3000);
        } catch (error) {
            console.error('Error saving meal:', error);
            setError('Failed to save meal. Please try again.');
        }
    };

    const handleEditToggle = () => {
        if (isEditing) {
            setAnalyzedNutrition({ ...editedNutrition });
        }
        setIsEditing(!isEditing);
    };

    const updateNutritionValue = (field, value) => {
        setEditedNutrition({
            ...editedNutrition,
            [field]: field === 'food_name' ? value : (parseFloat(value) || 0)
        });
    };

    // Form content (shared between inline and modal modes)
    const FormContent = () => (
        <div className="space-y-6">
            {!analyzedNutrition && (
                <>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Describe Your Meal {mode === 'inline' && '*'}
                        </label>
                        <textarea
                            value={mealDescription}
                            onChange={(e) => {
                                const value = e.target.value;
                                setMealDescription(value);
                            }}
                            placeholder="Example: Grilled chicken breast with steamed broccoli and brown rice, about 6oz chicken, 1 cup rice, 2 cups broccoli with olive oil drizzle"
                            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent min-h-[120px] resize-none"
                            disabled={isAnalyzing}
                            autoFocus={mode === 'inline'}  // Auto-focus when in inline mode
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Number of Servings
                        </label>
                        <input
                            type="number"
                            value={servings}
                            onChange={(e) => setServings(Math.max(1, parseInt(e.target.value) || 1))}
                            min="1"
                            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                            disabled={isAnalyzing}
                        />
                    </div>

                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-start gap-2">
                            <Info className="w-5 h-5 text-blue-600 mt-0.5" />
                            <div className="text-sm text-blue-900">
                                <p className="font-semibold mb-1">Tips for Better Accuracy:</p>
                                <ul className="space-y-1 ml-4">
                                    <li>• Include specific quantities (oz, cups, grams)</li>
                                    <li>• Mention cooking methods (grilled, fried, steamed)</li>
                                    <li>• List all ingredients including oils and seasonings</li>
                                    <li>• Specify brand names when applicable</li>
                                </ul>
                            </div>
                        </div>
                    </div>

                    {error && (
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-2">
                            <AlertCircle className="w-5 h-5 text-red-600 mt-0.5" />
                            <p className="text-sm text-red-900">{error}</p>
                        </div>
                    )}

                    <button
                        onClick={handleAnalyzeMeal}
                        disabled={isAnalyzing || !mealDescription.trim()}
                        className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg px-6 py-3 font-medium hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2"
                    >
                        {isAnalyzing ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Analyzing Your Meal...
                            </>
                        ) : (
                            <>
                                <Sparkles className="w-5 h-5" />
                                Analyze Meal with AI
                            </>
                        )}
                    </button>
                </>
            )}

            {analyzedNutrition && (
                <>
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                        <div className="flex items-center gap-2 mb-2">
                            <CheckCircle className="w-5 h-5 text-green-600" />
                            <p className="font-semibold text-green-900">Meal Analyzed Successfully!</p>
                        </div>
                        <p className="text-sm text-green-800">
                            Confidence Score: {Math.round(analyzedNutrition.confidence_score * 100)}%
                        </p>
                        {analyzedNutrition.analysis_notes && (
                            <p className="text-sm text-green-700 mt-1 italic">
                                Note: {analyzedNutrition.analysis_notes}
                            </p>
                        )}
                    </div>

                    <div className="bg-gray-50 rounded-lg p-6">
                        <div className="flex justify-between items-center mb-4">
                            <h3 className="text-lg font-semibold text-gray-900">
                                Nutrition Facts (per serving)
                            </h3>
                            <button
                                onClick={handleEditToggle}
                                className="text-purple-600 hover:text-purple-700 flex items-center gap-1 text-sm font-medium"
                            >
                                {isEditing ? (
                                    <>
                                        <Save className="w-4 h-4" />
                                        Save Edits
                                    </>
                                ) : (
                                    <>
                                        <Edit2 className="w-4 h-4" />
                                        Edit Values
                                    </>
                                )}
                            </button>
                        </div>

                        <div className="space-y-3">
                            <div className="flex justify-between items-center">
                                <span className="font-medium text-gray-700">Food Name:</span>
                                {isEditing ? (
                                    <input
                                        type="text"
                                        value={editedNutrition.food_name}
                                        onChange={(e) => updateNutritionValue('food_name', e.target.value)}
                                        className="px-2 py-1 border rounded text-right w-32"
                                    />
                                ) : (
                                    <span className="font-semibold">{analyzedNutrition.food_name}</span>
                                )}
                            </div>

                            {[
                                { label: 'Calories', field: 'calories', unit: '' },
                                { label: 'Protein', field: 'protein', unit: 'g' },
                                { label: 'Carbs', field: 'carbs', unit: 'g' },
                                { label: 'Fat', field: 'fat', unit: 'g' },
                                { label: 'Fiber', field: 'fiber', unit: 'g' }
                            ].map(({ label, field, unit }) => (
                                <div key={field} className="flex justify-between items-center">
                                    <span className="text-gray-700">{label}:</span>
                                    {isEditing ? (
                                        <div className="flex items-center gap-1">
                                            <input
                                                type="number"
                                                value={editedNutrition[field]}
                                                onChange={(e) => updateNutritionValue(field, e.target.value)}
                                                className="px-2 py-1 border rounded text-right w-20"
                                                step="0.1"
                                                min="0"
                                            />
                                            <span className="text-gray-600">{unit}</span>
                                        </div>
                                    ) : (
                                        <span className="font-medium">
                      {analyzedNutrition[field]}{unit}
                    </span>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="flex gap-3">
                        <button
                            onClick={() => {
                                resetForm();
                            }}
                            className="flex-1 bg-gray-200 text-gray-800 rounded-lg px-4 py-2 font-medium hover:bg-gray-300 transition-colors"
                        >
                            Analyze Different Meal
                        </button>
                        <button
                            onClick={handleSaveMeal}
                            className="flex-1 bg-gradient-to-r from-green-600 to-green-700 text-white rounded-lg px-4 py-2 font-medium hover:from-green-700 hover:to-green-800 transition-all duration-200"
                        >
                            Add to Nutrition Tracker
                        </button>
                    </div>
                </>
            )}
        </div>
    );

    // Inline mode - shows form directly
    if (mode === 'inline') {
        return (
            <>
                {successMessage && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4 flex items-center gap-2">
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        <p className="text-sm text-green-800">{successMessage}</p>
                    </div>
                )}
                <FormContent />
            </>
        );
    }

    // Button/Modal mode - shows button that opens modal
    return (
        <>
            {successMessage && (
                <div className="fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2 z-50">
                    <CheckCircle className="w-4 h-4" />
                    {successMessage}
                </div>
            )}

            <button
                onClick={() => setIsOpen(true)}
                className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg px-4 py-3 font-medium hover:from-purple-700 hover:to-blue-700 transition-all duration-200 flex items-center justify-center gap-2"
            >
                <span className="text-lg">🤖</span>
                AI-Powered Custom Meal Entry
            </button>

            {isOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white rounded-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                        <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-xl">
                            <div className="flex justify-between items-center">
                                <h2 className="text-2xl font-bold">AI Custom Meal Analyzer</h2>
                                <button
                                    onClick={() => {
                                        setIsOpen(false);
                                        resetForm();
                                    }}
                                    className="text-white hover:bg-white/20 rounded-lg p-2 transition-colors"
                                >
                                    <X className="w-5 h-5" />
                                </button>
                            </div>
                            <p className="text-white/90 mt-2">
                                Describe your meal and let AI calculate the nutrition facts
                            </p>
                        </div>

                        <div className="p-6">
                            <FormContent />
                        </div>
                    </div>
                </div>
            )}
        </>
    );
};

export default CustomMealAnalyzer;