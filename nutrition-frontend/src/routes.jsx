// routes.jsx - Updated with AI Nutrition Coach routes
import { Routes, Route } from 'react-router-dom'
import SignIn from './pages/SignIn'
import Preferences from './pages/Preferences'
import GroceryList from './pages/GroceryList'
import GenerateRecipe from './pages/GenerateRecipe';
import HomePage from './pages/HomePage.jsx';
import Favorites from './pages/Favorites.jsx';
import RequireAuth from './components/RequireAuth';
import NutritionPage from './pages/NutritionPage';

// NEW IMPORTS - Add these for AI Nutrition Coach
import NutritionCoachPage from './pages/NutritionCoachPage';
import FitnessAssessment from './components/FitnessAssessment';

import './App.css'

function App() {
  return (
      <div className="app-container">
        <Routes>
          <Route path="/" element={<SignIn />} />
          <Route path="/preferences" element={<Preferences />} />
          <Route path="/grocery" element={<GroceryList />} />
          <Route path="/generate" element={<GenerateRecipe />} />
          <Route path="/home" element={<HomePage />} />
          <Route path="/favorites" element={<Favorites />} />
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
            import SocialMediaImport from './components/SocialMediaImport';

            // Add the route (inside your Routes component)
            <Route
                path="/import-recipe"
                element={
                    <RequireAuth>
                        <SocialMediaImport />
                    </RequireAuth>
                }
            />
        </Routes>
      </div>
  )
}

export default App