// src/components/FitnessAssessment.jsx
// Updated to use correct API endpoints with /coaching prefix

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../services/supabase';
import {
    Target, User, Activity, Calendar, Trophy,
    ArrowRight, ArrowLeft, CheckCircle, AlertCircle
} from 'lucide-react';

// Error boundary component moved to top level
const ErrorBoundary = ({ children }) => {
    const [hasError, setHasError] = React.useState(false);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
        const handleError = (error) => {
            console.error('Error caught by boundary:', error);
            setHasError(true);
            setError(error);
        };

        window.addEventListener('error', handleError);
        window.addEventListener('unhandledrejection', handleError);

        return () => {
            window.removeEventListener('error', handleError);
            window.removeEventListener('unhandledrejection', handleError);
        };
    }, []);

    if (hasError) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <div className="bg-red-50 border border-red-200 rounded-lg p-8 text-center">
                    <h2 className="text-xl font-bold text-red-800 mb-4">Something went wrong</h2>
                    <p className="text-red-600 mb-4">There was an error loading the fitness assessment.</p>
                    <button
                        onClick={() => {setHasError(false); window.location.reload();}}
                        className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700"
                    >
                        Reload Page
                    </button>
                </div>
            </div>
        );
    }

    return children;
};

const FitnessAssessment = ({ onComplete }) => {
    const navigate = useNavigate();
    const [currentStep, setCurrentStep] = useState(1);
    const [userId, setUserId] = useState(null);
    const [loading, setLoading] = useState(false);
    const [availableGoals, setAvailableGoals] = useState([]);
    const [availableActivityLevels, setAvailableActivityLevels] = useState([]);

    const [assessmentData, setAssessmentData] = useState({
        // Basic Info
        age: '',
        gender: 'male',
        height_cm: '',
        current_weight: '',
        target_weight: '',

        // Body Composition (optional)
        body_fat_percentage: '',
        target_body_fat: '',

        // Activity & Goals
        activity_level: 'moderately_active',
        primary_goal: 'strength_building',
        timeline_weeks: 12,
        training_days_per_week: 3,
        experience_level: 'beginner',

        // Lifestyle
        current_injuries: [],
        supplement_preferences: [],
        meal_prep_experience: 'beginner'
    });

    const [errors, setErrors] = useState({});

    useEffect(() => {
        const fetchUser = async () => {
            const { data: { user } } = await supabase.auth.getUser();
            if (user) {
                setUserId(user.id);
            }
        };
        fetchUser();
        loadAvailableOptions();
    }, []);

    const loadAvailableOptions = async () => {
        try {
            // FIXED: Load available goals with correct endpoint
            const goalsResponse = await fetch('http://localhost:8000/coaching/available-goals');
            if (goalsResponse.ok) {
                const goalsData = await goalsResponse.json();
                setAvailableGoals(goalsData.data.goals);
            }

            // FIXED: Load activity levels with correct endpoint
            const activityResponse = await fetch('http://localhost:8000/coaching/activity-levels');
            if (activityResponse.ok) {
                const activityData = await activityResponse.json();
                setAvailableActivityLevels(activityData.data.activity_levels);
            }
        } catch (error) {
            console.error('Error loading options:', error);
        }
    };

    const validateStep = (step) => {
        const newErrors = {};

        switch (step) {
            case 1: // Basic Info
                if (!assessmentData.age || assessmentData.age < 16 || assessmentData.age > 80) {
                    newErrors.age = 'Please enter a valid age (16-80)';
                }
                if (!assessmentData.height_cm || assessmentData.height_cm < 120 || assessmentData.height_cm > 220) {
                    newErrors.height_cm = 'Please enter a valid height in cm (120-220)';
                }
                // FIXED: Increased weight range to be more realistic
                if (!assessmentData.current_weight || assessmentData.current_weight < 40 || assessmentData.current_weight > 500) {
                    newErrors.current_weight = 'Please enter a valid weight in lbs (40-500)';
                }
                break;

            case 2: // Goals
                // FIXED: Increased weight range to be more realistic
                if (!assessmentData.target_weight || assessmentData.target_weight < 40 || assessmentData.target_weight > 500) {
                    newErrors.target_weight = 'Please enter a valid target weight';
                }
                if (assessmentData.timeline_weeks < 4 || assessmentData.timeline_weeks > 52) {
                    newErrors.timeline_weeks = 'Timeline should be between 4-52 weeks';
                }
                break;

            case 3: // Activity
                if (assessmentData.training_days_per_week < 1 || assessmentData.training_days_per_week > 7) {
                    newErrors.training_days_per_week = 'Training days should be 1-7 per week';
                }
                break;
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const nextStep = () => {
        if (validateStep(currentStep)) {
            setCurrentStep(prev => Math.min(prev + 1, 4));
        }
    };

    const prevStep = () => {
        setCurrentStep(prev => Math.max(prev - 1, 1));
    };

    const handleInputChange = (field, value) => {
        setAssessmentData(prev => ({
            ...prev,
            [field]: value
        }));

        // Clear error for this field
        if (errors[field]) {
            setErrors(prev => ({
                ...prev,
                [field]: undefined
            }));
        }
    };

    const handleSubmit = async () => {
        if (!validateStep(currentStep)) return;

        setLoading(true);
        try {
            console.log('Submitting assessment data:', assessmentData);

            const response = await fetch('http://localhost:8000/coaching/assess-fitness-goals', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    ...assessmentData,
                    age: parseInt(assessmentData.age),
                    height_cm: parseFloat(assessmentData.height_cm),
                    current_weight: parseFloat(assessmentData.current_weight),
                    target_weight: parseFloat(assessmentData.target_weight),
                    body_fat_percentage: assessmentData.body_fat_percentage ? parseFloat(assessmentData.body_fat_percentage) : null,
                    target_body_fat: assessmentData.target_body_fat ? parseFloat(assessmentData.target_body_fat) : null,
                    timeline_weeks: parseInt(assessmentData.timeline_weeks),
                    training_days_per_week: parseInt(assessmentData.training_days_per_week)
                })
            });

            const result = await response.json();
            console.log('Assessment response:', result);

            if (response.ok && result.success) {
                console.log('Assessment completed successfully:', result);

                // Show success message
                alert('Fitness assessment completed successfully! Your personalized plan has been created.');

                if (onComplete) {
                    onComplete(result.data);
                } else {
                    // Navigate to coaching dashboard instead of nutrition-coach
                    navigate('/coaching-dashboard');
                }
            } else {
                console.error('Assessment submission failed:', result);
                const errorMessage = result.detail || result.message || 'Assessment submission failed. Please try again.';
                alert(`Assessment Error: ${errorMessage}`);
            }
        } catch (error) {
            console.error('Error submitting assessment:', error);
            alert('Network error: Please check your connection and try again.');
        } finally {
            setLoading(false);
        }
    };

    // Step 1: Basic Information
    const BasicInfoStep = () => (
        <div className="space-y-6">
            <div className="text-center mb-8">
                <User className="w-16 h-16 text-blue-600 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900">Tell us about yourself</h2>
                <p className="text-gray-600 mt-2">We'll use this to create your personalized plan</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
                    <input
                        type="number"
                        value={assessmentData.age}
                        onChange={(e) => handleInputChange('age', e.target.value)}
                        className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            errors.age ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="Enter your age"
                    />
                    {errors.age && <p className="text-red-500 text-sm mt-1">{errors.age}</p>}
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Gender</label>
                    <select
                        value={assessmentData.gender}
                        onChange={(e) => handleInputChange('gender', e.target.value)}
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                    </select>
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Height (cm)</label>
                    <input
                        type="number"
                        value={assessmentData.height_cm}
                        onChange={(e) => handleInputChange('height_cm', e.target.value)}
                        className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            errors.height_cm ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="e.g., 175"
                    />
                    {errors.height_cm && <p className="text-red-500 text-sm mt-1">{errors.height_cm}</p>}
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Current Weight (lbs)</label>
                    <input
                        type="number"
                        step="0.1"
                        value={assessmentData.current_weight}
                        onChange={(e) => handleInputChange('current_weight', e.target.value)}
                        className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            errors.current_weight ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="e.g., 160"
                    />
                    {errors.current_weight && <p className="text-red-500 text-sm mt-1">{errors.current_weight}</p>}
                </div>
            </div>

            <div className="border-t pt-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Body Composition (Optional)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Current Body Fat %</label>
                        <input
                            type="number"
                            step="0.1"
                            value={assessmentData.body_fat_percentage}
                            onChange={(e) => handleInputChange('body_fat_percentage', e.target.value)}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="e.g., 18.5 (optional)"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">Target Body Fat %</label>
                        <input
                            type="number"
                            step="0.1"
                            value={assessmentData.target_body_fat}
                            onChange={(e) => handleInputChange('target_body_fat', e.target.value)}
                            className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="e.g., 15.0 (optional)"
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    // Step 2: Goals & Timeline
    const GoalsStep = () => (
        <div className="space-y-6">
            <div className="text-center mb-8">
                <Target className="w-16 h-16 text-green-600 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900">What's your primary goal?</h2>
                <p className="text-gray-600 mt-2">This will shape your entire nutrition and training strategy</p>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-4">Primary Fitness Goal</label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {availableGoals.map(goal => (
                        <button
                            key={goal.value}
                            onClick={() => handleInputChange('primary_goal', goal.value)}
                            className={`p-4 border-2 rounded-lg text-left transition-colors ${
                                assessmentData.primary_goal === goal.value
                                    ? 'border-green-500 bg-green-50'
                                    : 'border-gray-200 hover:border-green-300'
                            }`}
                        >
                            <div className="font-semibold text-gray-900">{goal.display_name}</div>
                            <div className="text-sm text-gray-600 mt-1">{goal.description}</div>
                            <div className="text-xs text-gray-500 mt-2">Typical timeline: {goal.typical_timeline}</div>
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Target Weight (lbs)</label>
                    <input
                        type="number"
                        step="0.1"
                        value={assessmentData.target_weight}
                        onChange={(e) => handleInputChange('target_weight', e.target.value)}
                        className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            errors.target_weight ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="e.g., 170"
                    />
                    {errors.target_weight && <p className="text-red-500 text-sm mt-1">{errors.target_weight}</p>}
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Timeline (weeks)</label>
                    <input
                        type="number"
                        value={assessmentData.timeline_weeks}
                        onChange={(e) => handleInputChange('timeline_weeks', e.target.value)}
                        className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            errors.timeline_weeks ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="e.g., 12"
                    />
                    {errors.timeline_weeks && <p className="text-red-500 text-sm mt-1">{errors.timeline_weeks}</p>}
                </div>
            </div>
        </div>
    );

    // Step 3: Activity Level
    const ActivityStep = () => (
        <div className="space-y-6">
            <div className="text-center mb-8">
                <Activity className="w-16 h-16 text-purple-600 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900">Tell us about your activity level</h2>
                <p className="text-gray-600 mt-2">This helps us calculate your calorie and macro needs</p>
            </div>

            <div>
                <label className="block text-sm font-medium text-gray-700 mb-4">Activity Level</label>
                <div className="space-y-3">
                    {availableActivityLevels.map(level => (
                        <button
                            key={level.value}
                            onClick={() => handleInputChange('activity_level', level.value)}
                            className={`w-full p-4 border-2 rounded-lg text-left transition-colors ${
                                assessmentData.activity_level === level.value
                                    ? 'border-purple-500 bg-purple-50'
                                    : 'border-gray-200 hover:border-purple-300'
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="font-semibold text-gray-900">{level.display_name}</div>
                                    <div className="text-sm text-gray-600 mt-1">{level.description}</div>
                                </div>
                                <div className="text-sm text-gray-500">
                                    Multiplier: {level.multiplier}
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Training Days per Week</label>
                    <input
                        type="number"
                        min="1"
                        max="7"
                        value={assessmentData.training_days_per_week}
                        onChange={(e) => handleInputChange('training_days_per_week', e.target.value)}
                        className={`w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                            errors.training_days_per_week ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="e.g., 3"
                    />
                    {errors.training_days_per_week && <p className="text-red-500 text-sm mt-1">{errors.training_days_per_week}</p>}
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">Experience Level</label>
                    <select
                        value={assessmentData.experience_level}
                        onChange={(e) => handleInputChange('experience_level', e.target.value)}
                        className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    >
                        <option value="beginner">Beginner (0-1 years)</option>
                        <option value="intermediate">Intermediate (1-3 years)</option>
                        <option value="advanced">Advanced (3+ years)</option>
                    </select>
                </div>
            </div>
        </div>
    );

    // Step 4: Review & Submit
    const ReviewStep = () => (
        <div className="space-y-6">
            <div className="text-center mb-8">
                <Trophy className="w-16 h-16 text-yellow-600 mx-auto mb-4" />
                <h2 className="text-2xl font-bold text-gray-900">Review your assessment</h2>
                <p className="text-gray-600 mt-2">We'll create your personalized nutrition coaching plan</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Assessment Summary</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <h4 className="font-medium text-gray-700 mb-2">Basic Info</h4>
                        <ul className="text-sm text-gray-600 space-y-1">
                            <li>Age: {assessmentData.age} years</li>
                            <li>Gender: {assessmentData.gender}</li>
                            <li>Height: {assessmentData.height_cm} cm</li>
                            <li>Current Weight: {assessmentData.current_weight} lbs</li>
                            {assessmentData.body_fat_percentage && (
                                <li>Body Fat: {assessmentData.body_fat_percentage}%</li>
                            )}
                        </ul>
                    </div>

                    <div>
                        <h4 className="font-medium text-gray-700 mb-2">Goals & Activity</h4>
                        <ul className="text-sm text-gray-600 space-y-1">
                            <li>Goal: {availableGoals.find(g => g.value === assessmentData.primary_goal)?.display_name}</li>
                            <li>Target Weight: {assessmentData.target_weight} lbs</li>
                            <li>Timeline: {assessmentData.timeline_weeks} weeks</li>
                            <li>Activity: {availableActivityLevels.find(a => a.value === assessmentData.activity_level)?.display_name}</li>
                            <li>Training: {assessmentData.training_days_per_week} days/week</li>
                            <li>Experience: {assessmentData.experience_level}</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div className="bg-blue-50 rounded-lg p-6">
                <h3 className="font-semibold text-blue-900 mb-2 flex items-center">
                    <CheckCircle className="w-5 h-5 mr-2" />
                    What happens next?
                </h3>
                <ul className="text-sm text-blue-800 space-y-2">
                    <li>• We'll calculate your personalized macro and calorie targets</li>
                    <li>• Your AI coach will create a customized nutrition strategy</li>
                    <li>• You'll get goal-specific recipe recommendations</li>
                    <li>• Track progress with intelligent insights and adjustments</li>
                </ul>
            </div>
        </div>
    );

    const stepComponents = {
        1: BasicInfoStep,
        2: GoalsStep,
        3: ActivityStep,
        4: ReviewStep
    };

    const StepComponent = stepComponents[currentStep];

    // Loading state during submission
    if (loading) {
        return (
            <div className="max-w-4xl mx-auto p-6">
                <div className="bg-white rounded-lg shadow-lg p-8">
                    <div className="flex items-center justify-center h-64">
                        <div className="text-center">
                            <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                            <p className="text-gray-600">Creating your personalized coaching plan...</p>
                            <p className="text-sm text-gray-500 mt-2">This may take a moment as we calculate your optimal macro targets</p>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            {/* Progress indicator */}
            <div className="mb-8">
                <div className="flex items-center justify-between mb-4">
                    {[1, 2, 3, 4].map(step => (
                        <div key={step} className="flex items-center">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                                step <= currentStep
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-gray-200 text-gray-600'
                            }`}>
                                {step < currentStep ? <CheckCircle className="w-5 h-5" /> : step}
                            </div>
                            {step < 4 && (
                                <div className={`w-16 h-1 mx-2 ${
                                    step < currentStep ? 'bg-blue-600' : 'bg-gray-200'
                                }`} />
                            )}
                        </div>
                    ))}
                </div>

                <div className="text-center">
                    <span className="text-sm text-gray-600">
                        Step {currentStep} of 4
                    </span>
                </div>
            </div>

            {/* Content */}
            <div className="bg-white rounded-lg shadow-lg p-8">
                <StepComponent />

                {/* Navigation */}
                <div className="flex justify-between mt-8 pt-6 border-t">
                    <button
                        onClick={prevStep}
                        disabled={currentStep === 1}
                        className="flex items-center px-6 py-2 text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ArrowLeft className="w-4 h-4 mr-2" />
                        Previous
                    </button>

                    {currentStep < 4 ? (
                        <button
                            onClick={nextStep}
                            className="flex items-center px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                        >
                            Next
                            <ArrowRight className="w-4 h-4 ml-2" />
                        </button>
                    ) : (
                        <button
                            onClick={handleSubmit}
                            disabled={loading}
                            className="flex items-center px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                        >
                            {loading ? (
                                <>
                                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                                    Creating Plan...
                                </>
                            ) : (
                                <>
                                    Complete Assessment
                                    <CheckCircle className="w-4 h-4 ml-2" />
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>

            {/* Help text */}
            <div className="mt-6 text-center">
                <p className="text-sm text-gray-500">
                    Need help? All information is used to create your personalized nutrition plan and can be updated later.
                </p>
            </div>
        </div>
    );
};

// Wrap your main component export with the ErrorBoundary at the top level
export default function FitnessAssessmentWithBoundary(props) {
    return (
        <ErrorBoundary>
            <FitnessAssessment {...props} />
        </ErrorBoundary>
    );
}