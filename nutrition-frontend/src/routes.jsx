// src/routes.jsx
import { Routes, Route } from 'react-router-dom';
import SignIn from './pages/SignIn';
import Preferences from './pages/Preferences';
import GroceryList from './pages/GroceryList';
import RequireAuth from './components/RequireAuth';

export default function AppRoutes() {
  return (
    <Routes>
      {/** Public route **/}
      <Route path="/" element={<SignIn />} />

      {/** Protected routes **/}
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
    </Routes>
  );
}
