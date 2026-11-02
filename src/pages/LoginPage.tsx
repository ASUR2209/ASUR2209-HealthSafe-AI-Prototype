import { useState } from 'react'
import { supabase } from '../lib/supabase'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSignUp, setIsSignUp] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const handleEmailAuth = async () => {
    setLoading(true)
    setError(null)
    setMessage(null)

    try {
      if (isSignUp) {
        const { error } = await supabase.auth.signUp({ email, password })
        if (error) throw error
        setMessage('Check your email for a confirmation link!')
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password })
        if (error) throw error
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: window.location.origin
      }
    })
    if (error) setError(error.message)
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0D1117',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        width: '100%',
        maxWidth: '380px',
        background: '#0D1F2D',
        borderRadius: '24px',
        border: '1px solid #1E2D3D',
        padding: '32px 24px'
      }}>

        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            width: '56px', height: '56px',
            borderRadius: '16px',
            background: 'linear-gradient(135deg, #1D9E75, #0F6E56)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 12px'
          }}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div style={{ fontSize: '22px', fontWeight: 500, color: '#E8F4F1' }}>HealthSafe AI</div>
          <div style={{ fontSize: '13px', color: '#4A7A8A', marginTop: '4px' }}>
            Your family's food safety companion
          </div>
        </div>

        {/* Toggle */}
        <div style={{
          display: 'flex',
          background: '#131C27',
          borderRadius: '10px',
          padding: '3px',
          marginBottom: '20px'
        }}>
          {['Sign in', 'Sign up'].map((tab, i) => (
            <button
              key={tab}
              onClick={() => setIsSignUp(i === 1)}
              style={{
                flex: 1, padding: '8px',
                borderRadius: '8px', border: 'none',
                background: isSignUp === (i === 1) ? '#1E2D3D' : 'transparent',
                color: isSignUp === (i === 1) ? '#E8F4F1' : '#4A7A8A',
                fontSize: '13px', fontWeight: 500,
                cursor: 'pointer', transition: 'all 0.2s'
              }}
            >{tab}</button>
          ))}
        </div>

        {/* Email */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '11px', color: '#4A7A8A', marginBottom: '6px', letterSpacing: '0.04em' }}>
            EMAIL ADDRESS
          </div>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com"
            style={{
              width: '100%', padding: '12px 14px',
              background: '#131C27',
              border: '1px solid #1E2D3D',
              borderRadius: '10px',
              color: '#E8F4F1', fontSize: '14px',
              outline: 'none'
            }}
          />
        </div>

        {/* Password */}
        <div style={{ marginBottom: '8px' }}>
          <div style={{ fontSize: '11px', color: '#4A7A8A', marginBottom: '6px', letterSpacing: '0.04em' }}>
            PASSWORD
          </div>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            placeholder="••••••••"
            onKeyDown={e => e.key === 'Enter' && handleEmailAuth()}
            style={{
              width: '100%', padding: '12px 14px',
              background: '#131C27',
              border: '1px solid #1E2D3D',
              borderRadius: '10px',
              color: '#E8F4F1', fontSize: '14px',
              outline: 'none'
            }}
          />
        </div>

        {!isSignUp && (
          <div style={{ textAlign: 'right', marginBottom: '16px' }}>
            <span style={{ fontSize: '12px', color: '#1D9E75', cursor: 'pointer' }}>
              Forgot password?
            </span>
          </div>
        )}

        {/* Error / Message */}
        {error && (
          <div style={{
            background: 'rgba(226,75,74,0.1)', border: '1px solid rgba(226,75,74,0.2)',
            borderRadius: '8px', padding: '10px 12px',
            fontSize: '12px', color: '#E24B4A', marginBottom: '12px'
          }}>{error}</div>
        )}
        {message && (
          <div style={{
            background: 'rgba(29,158,117,0.1)', border: '1px solid rgba(29,158,117,0.2)',
            borderRadius: '8px', padding: '10px 12px',
            fontSize: '12px', color: '#1D9E75', marginBottom: '12px'
          }}>{message}</div>
        )}

        {/* Primary button */}
        <button
          onClick={handleEmailAuth}
          disabled={loading}
          style={{
            width: '100%', padding: '13px',
            background: loading ? '#0F3D2E' : 'linear-gradient(135deg, #1D9E75, #0F6E56)',
            border: 'none', borderRadius: '12px',
            color: 'white', fontSize: '14px', fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
            marginBottom: '12px', transition: 'opacity 0.2s'
          }}
        >
          {loading ? 'Please wait...' : isSignUp ? 'Create account' : 'Sign in'}
        </button>

        {/* Divider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '12px' }}>
          <div style={{ flex: 1, height: '0.5px', background: '#1E2D3D' }}></div>
          <span style={{ fontSize: '11px', color: '#4A7A8A' }}>or continue with</span>
          <div style={{ flex: 1, height: '0.5px', background: '#1E2D3D' }}></div>
        </div>

        {/* Google button */}
        <button
          onClick={handleGoogleLogin}
          style={{
            width: '100%', padding: '12px',
            background: '#131C27',
            border: '1px solid #1E2D3D',
            borderRadius: '12px',
            color: '#8B9DB0', fontSize: '13px',
            cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center', gap: '8px'
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24">
            <path fill="#4A7A8A" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#4A7A8A" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#4A7A8A" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
            <path fill="#4A7A8A" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
          </svg>
          Continue with Google
        </button>

      </div>
    </div>
  )
}