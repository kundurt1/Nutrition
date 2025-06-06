// src/components/RequireAuth.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../services/supabase';
import { Navigate, useLocation } from 'react-router-dom';

export default function RequireAuth({ children }) {
  const [session, setSession] = useState(null);
  const location = useLocation();

  useEffect(() => {
    // Check initial session
    const currentSession = supabase.auth.session();
    setSession(currentSession);

    // Listen for changes
    const { data: listener } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => {
      listener.unsubscribe();
    };
  }, []);

  // If session is loading (null → initial undefined), show nothing or a loader
  if (session === null) {
    return null; // Or return a spinner
  }

  // If there’s no session, redirect to sign-in, preserving the attempted route
  if (!session) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  // If valid session exists, render children
  return children;
}