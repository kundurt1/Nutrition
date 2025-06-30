// src/components/RequireAuth.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';
import { Navigate, useLocation } from 'react-router-dom';

export default function RequireAuth({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const location = useLocation();

  useEffect(() => {
    // Check initial session using the correct method
    const getInitialSession = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      setSession(session);
      setLoading(false);
    };

    getInitialSession();

    // Listen for changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // If session is still loading, show a loading indicator
  if (loading) {
    return (
      <div className="card">
        <p>Loading...</p>
      </div>
    );
  }

  // If there's no session, redirect to sign-in, preserving the attempted route
  if (!session) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  // If valid session exists, render children
  return children;
}