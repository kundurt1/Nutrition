import { Routes, Route } from 'react-router-dom';
import SignIn from './pages/SignIn';
import HomePage from './pages/HomePage.jsx';
import Preferences from './pages/Preferences';
import GroceryList from './pages/GroceryList';
import GenerateRecipe from './pages/GenerateRecipe';
import RequireAuth from './components/RequireAuth';

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
    </Routes>
  );
}
