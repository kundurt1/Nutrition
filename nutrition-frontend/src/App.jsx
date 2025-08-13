// src/App.jsx - Updated with AI Nutrition Coach routes
import { Routes, Route } from 'react-router-dom';
import SignIn from './pages/SignIn';
import HomePage from './pages/HomePage.jsx';
import Preferences from './pages/Preferences';
import GroceryList from './pages/GroceryList';
import GenerateRecipe from './pages/GenerateRecipe';
import Favorites from './pages/Favorites';
import RequireAuth from './components/RequireAuth';
import NutritionPage from './pages/NutritionPage';

// NEW IMPORTS - Add these for AI Nutrition Coach
import NutritionCoachPage from './pages/NutritionCoachPage';
import FitnessAssessment from './components/FitnessAssessment';
import SocialMediaImport from "./components/SocialMediaImport.jsx";

export default function AppRoutes() {
    return (
        <Routes>
            {/* public route */}
            <Route path="/" element={<SignIn />} />

            {/* protected routes */}
            <Route
                path="/home"
                element={
                    <RequireAuth>
                        <HomePage />
                    </RequireAuth>
                }
            />

            <Route
                path="/preferences"
                element={
                    <RequireAuth>
                        <Preferences />
                    </RequireAuth>
                }
            />

            <Route
                path="/grocery"
                element={
                    <RequireAuth>
                        <GroceryList />
                    </RequireAuth>
                }
            />

            <Route
                path="/generate"
                element={
                    <RequireAuth>
                        <GenerateRecipe />
                    </RequireAuth>
                }
            />

            <Route
                path="/favorites"
                element={
                    <RequireAuth>
                        <Favorites />
                    </RequireAuth>
                }
            />

            <Route
                path="/nutrition"
                element={
                    <RequireAuth>
                        <NutritionPage />
                    </RequireAuth>
                }
            />

            {/* NEW ROUTES - Add these for AI Nutrition Coach */}
            <Route
                path="/nutrition-coach"
                element={
                    <RequireAuth>
                        <NutritionCoachPage />
                    </RequireAuth>
                }
            />

            <Route
                path="/fitness-assessment"
                element={
                    <RequireAuth>
                        <FitnessAssessment />
                    </RequireAuth>
                }
            />
            <Route
                path="/social-media"
                element={
                    <RequireAuth>
                        <SocialMediaImport />
                    </RequireAuth>
                }
            />
        </Routes>
    );
}