import { useState } from "react";
import { ProfileSetup } from "./pages/ProfileSetup";
import { ScanInput } from "./pages/ScanInput";
import { Results } from "./pages/Results";
import { analyseIngredients } from "./lib/analysis";
import type { AnalysisResult, Page, UserProfile } from "./types";
import { useEffect, useState } from 'react'
import { supabase } from './lib/supabase'
import LoginPage from './pages/LoginPage'
import { Session } from '@supabase/supabase-js'


const DEFAULT_PROFILE: UserProfile = { name: "", age: "", conditions: [], medications: [] };

function BottomNav({ current, onNavigate, hasProfile }: { current: Page; onNavigate: (p: Page) => void; hasProfile: boolean }) {
  const tabs = [
    {
      id: "profile" as Page,
      label: "Profile",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      ),
    },
    {
      id: "scan" as Page,
      label: "Scan",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      ),
    },
    {
      id: "results" as Page,
      label: "Results",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11" />
        </svg>
      ),
    },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 z-50" style={{ fontFamily: "'Inter', sans-serif" }}>
      <div className="max-w-lg mx-auto flex">
        {tabs.map((tab) => {
          const active = current === tab.id;
          const disabled = tab.id === "results" && !hasProfile;
          return (
            <button
              key={tab.id}
              onClick={() => !disabled && onNavigate(tab.id)}
              className={`flex-1 flex flex-col items-center gap-1 py-3 transition-all ${
                active
                  ? "text-teal-600"
                  : disabled
                  ? "text-gray-200 cursor-not-allowed"
                  : "text-gray-400 hover:text-gray-600"
              }`}
            >
              {tab.icon}
              <span className="text-xs font-medium">{tab.label}</span>
              {active && <div className="w-4 h-0.5 rounded-full bg-teal-600 -mt-0.5" />}
            </button>
          );
        })}
      </div>
    </nav>
  );
}

export default function App() {
  const [page, setPage] = useState<Page>("profile");
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);

  function handleSaveProfile(p: UserProfile) {
    setProfile(p);
    setTimeout(() => setPage("scan"), 600);
  }

  async function handleAnalyse(ingredients: string) {
    setLoading(true);
    try {
      const res = await analyseIngredients(ingredients, profile);
      setResult(res);
      setPage("results");
    } catch (err) {
      alert(
        "Cannot connect to API.\n\nMake sure app.py is running:\n  python app.py\n\nThen try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="pb-16">
      {page === "profile" && (
        <ProfileSetup profile={profile} onSave={handleSaveProfile} />
      )}
      {page === "scan" && (
        <ScanInput
          profile={profile}
          onAnalyse={handleAnalyse}
          onEditProfile={() => setPage("profile")}
          loading={loading}
        />
      )}
      {page === "results" && result && (
        <Results result={result} onScanAgain={() => setPage("scan")} />
      )}
      {page === "results" && !result && (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center p-8">
            <p className="text-gray-500 text-sm">No analysis yet.</p>
            <button
              onClick={() => setPage("scan")}
              className="mt-4 px-6 py-2 rounded-xl bg-teal-600 text-white text-sm font-medium"
            >
              Go to Scanner
            </button>
          </div>
        </div>
      )}
      <BottomNav current={page} onNavigate={setPage} hasProfile={!!result} />
    </div>
  );
}

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session)
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  if (loading) {
    return (
      <div style={{
        minHeight: '100vh', background: '#0D1117',
        display: 'flex', alignItems: 'center', justifyContent: 'center'
      }}>
        <div style={{ fontSize: '14px', color: '#4A7A8A' }}>Loading...</div>
      </div>
    )
  }

  if (!session) {
    return <LoginPage />
  }

  // Logged in — show main app
  return (
    <div style={{ minHeight: '100vh', background: '#0D1117' }}>
      <div style={{ padding: '20px', color: '#E8F4F1' }}>
        Welcome, {session.user.email}
        <button
          onClick={() => supabase.auth.signOut()}
          style={{
            marginLeft: '16px', padding: '6px 12px',
            background: 'transparent', border: '1px solid #1E2D3D',
            borderRadius: '8px', color: '#4A7A8A',
            fontSize: '12px', cursor: 'pointer'
          }}
        >Sign out</button>
      </div>
    </div>
  )
}