// src/App.jsx
import { Routes, Route } from 'react-router-dom'
import SignIn from './pages/SignIn'
import Preferences from './pages/Preferences'
import GroceryList from './pages/GroceryList'
import GenerateRecipe from './pages/GenerateRecipe';
import HomePage from './pages/HomePage.jsx';


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

      </Routes>
    </div>
  )
}

export default App