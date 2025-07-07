// src/pages/SignIn.jsx
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../services/supabase'

export default function SignIn() {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  // Check if user is already signed in
  useEffect(() => {
    const checkSession = async () => {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (session) {
          navigate('/home');
        }
      } catch (error) {
        console.log('No session found:', error)
      }
    }
    
    checkSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session) {
        navigate('/preferences')
      }
    })

    return () => subscription.unsubscribe()
  }, [navigate])

  const handleSignIn = async () => {
    if (!email.trim()) {
      alert('Please enter an email address')
      return
    }
    
    setLoading(true)
    try {
      const { error } = await supabase.auth.signInWithOtp({ 
        email,
        options: {
          emailRedirectTo: window.location.origin + '/preferences'
        }
      })
      
      if (error) {
        alert(error.message)
      } else {
        alert('Check your email for a login link!')
        setEmail('')
      }
    } catch (err) {
      console.error('Sign in error:', err)
      alert('Error sending login link.')
    }
    setLoading(false)
  }

  const handleGoogleSignIn = () => {
    // Placeholder for Google OAuth
    alert('Google sign-in will be implemented with OAuth')
  }

  const handleAppleSignIn = () => {
    // Placeholder for Apple OAuth
    alert('Apple sign-in will be implemented with OAuth')
  }

  return (
    
    <div className="app-container">
      <div className="card">
        {/* App Name/Logo */}
        <div className="text-center mb-4">
          <h1 style={{ 
            fontSize: '2.5rem', 
            fontWeight: '700', 
            background: 'linear-gradient(135deg, #007bff, #0056b3)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '16px'
          }}>
            NutriPlan
          </h1>
        </div>

        <h2 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Create an account</h2>
        <p className="subtitle">Enter your email to sign up for this app</p>

        <div className="form-group">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="email@domain.com"
            onKeyPress={(e) => e.key === 'Enter' && handleSignIn()}
            required
            style={{
              fontSize: '1rem',
              padding: '16px',
              border: '2px solid #e9ecef',
              borderRadius: '12px'
            }}
          />
        </div>

        <button
          className="btn-primary"
          onClick={handleSignIn}
          disabled={loading || !email.trim()}
          style={{
            background: '#000',
            color: 'white',
            marginBottom: '24px'
          }}
        >
          {loading ? 'Sending magic link...' : 'Continue'}
        </button>

        <div style={{ 
          textAlign: 'center', 
          margin: '24px 0',
          color: '#6c757d',
          fontSize: '0.9rem'
        }}>
          or
        </div>

        <button
          className="btn-secondary"
          onClick={handleGoogleSignIn}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            background: '#f8f9fa',
            border: '2px solid #e9ecef',
            color: '#495057',
            marginBottom: '12px'
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>

        <button
          className="btn-secondary"
          onClick={handleAppleSignIn}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '12px',
            background: '#f8f9fa',
            border: '2px solid #e9ecef',
            color: '#495057',
            marginBottom: '24px'
          }}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M18.71 19.5C17.88 20.74 17 21.95 15.66 21.97C14.32 22 13.89 21.18 12.37 21.18C10.84 21.18 10.37 21.95 9.09997 22C7.78997 22.05 6.79997 20.68 5.95997 19.47C4.24997 17 2.93997 12.45 4.69997 9.39C5.56997 7.87 7.13997 6.91 8.85997 6.88C10.15 6.86 11.38 7.75 12.1 7.75C12.81 7.75 14.28 6.68 15.84 6.84C16.45 6.87 18.05 7.1 19.11 8.82C19.02 8.88 17.25 9.97 17.27 12.42C17.3 15.45 19.96 16.5 20 16.52C19.97 16.57 19.56 18.04 18.71 19.5ZM12.84 6.79C13.48 6.04 13.97 4.96 13.83 3.9C12.95 3.94 11.9 4.52 11.22 5.26C10.61 5.93 10.02 7.04 10.18 8.09C11.19 8.16 12.24 7.58 12.84 6.79Z"/>
          </svg>
          Continue with Apple
        </button>

        <div className="footer-text">
          By clicking continue, you agree to our{' '}
          <a href="#" style={{ color: '#007bff', textDecoration: 'none' }}>
            Terms of Service
          </a>
          {' '}and{' '}
          <a href="#" style={{ color: '#007bff', textDecoration: 'none' }}>
            Privacy Policy
          </a>
        </div>
      </div>
    </div>
    
  )
  
}