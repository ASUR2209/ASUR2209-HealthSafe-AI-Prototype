import { useEffect, useRef, useState } from "react";
import { ApiError, checkHealth, scanBarcode, scanPhoto, scanText, type Profile, type Result } from "./api";
import { Composer } from "./Composer";
import { Findings } from "./Findings";
import { Household, type Session } from "./Household";
import { Lightbox } from "./Lightbox";
import { ProfilePanel } from "./ProfilePanel";
import { Announcer, announce } from "./a11y";

const load = <T,>(k: string, fallback: T): T => {
  try {
    const v = localStorage.getItem(k);
    return v ? (JSON.parse(v) as T) : fallback;
  } catch {
    return fallback;
  }
};
const save = (k: string, v: unknown) => {
  try {
    localStorage.setItem(k, JSON.stringify(v));
  } catch {}
};

const DEFAULT: Profile = { name: "", conditions: ["diabetes", "hypertension"], medications: ["metformin"] };

export default function App() {
  const [view, setView] = useState<"scan" | "household">("scan");
  const [profile, setProfile] = useState<Profile>(() => load("hs.profile", DEFAULT));
  const [session, setSession] = useState<Session | null>(() => load("hs.session", null));
  const [result, setResult] = useState<Result | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<{ msg: string; tip?: string } | null>(null);
  const [online, setOnline] = useState<boolean | null>(null);
  const resultRef = useRef<HTMLDivElement>(null);

  useEffect(() => save("hs.profile", profile), [profile]);
  useEffect(() => save("hs.session", session), [session]);
  useEffect(() => {
    const ping = () => checkHealth().then(setOnline);
    ping();
    const t = setInterval(ping, 15000);
    return () => clearInterval(t);
  }, []);

  const run = async (fn: () => Promise<Result>) => {
    setRunning(true);
    setError(null);
    setResult(null);
    announce("Analysing…");
    try {
      const r = await fn();
      setResult(r);
      const flags = r.flagged.length;
      const meds = r.conflicts.length;
      announce(
        `Analysis complete. ${r.verdict}, score ${r.score} out of 100. ` +
          `${flags} flag${flags === 1 ? "" : "s"} for your conditions` +
          (meds ? `, ${meds} medicine conflict${meds === 1 ? "" : "s"}.` : ".")
      );
      // Move focus to the results so keyboard and screen-reader users land on them.
      setTimeout(() => {
        const h = document.getElementById("results-heading");
        h?.focus({ preventScroll: true });
        resultRef.current?.scrollIntoView({ behavior: reduceMotion() ? "auto" : "smooth", block: "start" });
      }, 50);
    } catch (e) {
      const err = e as ApiError;
      setError({
        msg: err.offline ? "Photo and barcode scans need the Flask API. Start it with: python backend/app.py" : err.message,
        tip: err.tip,
      });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to {view === "scan" ? "scanner" : "household"}
      </a>
      <Announcer />
      <header className="top">
        <a className="mark" href="#" aria-label="HealthSafe AI, go to Scan" onClick={(e) => (e.preventDefault(), setView("scan"))}>
          <Logo />
          <span>
            HealthSafe<em>AI</em>
          </span>
        </a>
        <nav className="nav" aria-label="Main">
          <button className={view === "scan" ? "on" : ""} aria-current={view === "scan" ? "page" : undefined} onClick={() => setView("scan")}>
            Scan
          </button>
          <button className={view === "household" ? "on" : ""} aria-current={view === "household" ? "page" : undefined} onClick={() => setView("household")}>
            Household
          </button>
        </nav>
        <span className={`status ${online ? "is-on" : online === false ? "is-off" : ""}`} role="status">
          <i aria-hidden />
          {online == null ? "Checking API" : online ? "Model online" : "Demo mode"}
        </span>
      </header>

      {view === "scan" ? (
        <main className="scan" id="main" tabIndex={-1}>
          <div className="intro">
            <h1>
              Every ingredient, read against <span className="u">your</span> conditions and <span className="u">your</span> medicines.
            </h1>
            <p>
              Rules for 30 conditions and 40+ medicines run first, an XGBoost classifier scores the whole list, and an ingredient heuristic
              weighs each item. The result shows you where each signal came from.
            </p>
          </div>

          <ProfilePanel profile={profile} onChange={setProfile} />

          <div className="work">
            <Composer
              running={running}
              onText={(t) => run(() => scanText(t, profile, session?.familyId))}
              onPhoto={(d) => run(() => scanPhoto(d, profile, session?.familyId))}
              onBarcode={(c) => run(() => scanBarcode(c, profile, session?.familyId))}
            />
            {error && (
              <div className="alert" role="alert">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="M12 3 2 21h20L12 3zM12 10v5M12 18v.01" />
                </svg>
                <b>{error.msg}</b>
                {error.tip && <span>{error.tip}</span>}
              </div>
            )}
            <div ref={resultRef} className="result-anchor">
              <Lightbox result={result} running={running} />
            </div>
            {result && <Findings result={result} profile={profile} />}
          </div>
        </main>
      ) : (
        <main className="hh" id="main" tabIndex={-1}>
          <Household
            session={session}
            online={!!online}
            onSession={setSession}
            currentProfile={profile}
            onScanFor={(p) => {
              setProfile(p);
              setResult(null);
              setView("scan");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        </main>
      )}
    </div>
  );
}

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden focusable="false">
      <rect width="32" height="32" rx="8" fill="var(--lightbox)" />
      <rect x="7" y="9" width="18" height="3" rx="1.5" fill="var(--g-safe)" />
      <rect x="7" y="15" width="12" height="3" rx="1.5" fill="var(--g-mod)" />
      <rect x="7" y="21" width="15" height="3" rx="1.5" fill="var(--g-unsafe)" />
    </svg>
  );
}

const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
