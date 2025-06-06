// src/App.jsx
import { Routes, Route } from 'react-router-dom'
import SignIn from './pages/SignIn'
import Preferences from './pages/Preferences'
import GroceryList from './pages/GroceryList'
import './App.css'

function App() {
  return (
    <div className="app-container">
      <Routes>
        <Route path="/" element={<SignIn />} />
        <Route path="/preferences" element={<Preferences />} />
        <Route path="/grocery" element={<GroceryList />} />
      </Routes>
    </div>
  )
}

export default App