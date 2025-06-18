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

  return (
    <div className="card">
      <h1>Nutrition App</h1>

      <div className="form-group">
        <label htmlFor="email">Email address</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          onKeyPress={(e) => e.key === 'Enter' && handleSignIn()}
          required
        />
      </div>

      <button
        className="primary"
        onClick={handleSignIn}
        disabled={loading || !email.trim()}
      >
        {loading ? 'Sending magic link...' : 'Continue'}
      </button>
    </div>
  )
}