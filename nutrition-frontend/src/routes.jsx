// Update your App.jsx to include the Favorites route
import { Routes, Route } from 'react-router-dom'
import SignIn from './pages/SignIn'
import Preferences from './pages/Preferences'
import GroceryList from './pages/GroceryList'
import GenerateRecipe from './pages/GenerateRecipe';
import HomePage from './pages/HomePage.jsx';
import Favorites from './pages/Favorites.jsx'; 

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
        <Route path="/favorites" element={<Favorites />} /> {/* Add this route */}
        <Route path="/nutrition"element={ <RequireAuth> <NutritionPage /></RequireAuth>}/>
      </Routes>
    </div>
  )
}

export default App