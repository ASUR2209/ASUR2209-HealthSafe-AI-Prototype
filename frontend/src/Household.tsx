import { useEffect, useRef, useState } from "react";
import { family, needsApi, type Member, type Profile } from "./api";
import { pretty } from "./data";
import { Tabs, announce, tabPanelProps } from "./a11y";
import { ConditionPicker, MedicinePicker } from "./ProfilePanel";

export interface Session {
  familyId: string;
  headName: string;
}

interface Props {
  session: Session | null;
  online: boolean;
  onSession: (s: Session | null) => void;
  onScanFor: (p: Profile) => void;
  currentProfile: Profile;
}

export function Household({ session, online, onSession, onScanFor, currentProfile }: Props) {
  if (!session) return <Auth online={online} onSession={onSession} />;
  return <Dashboard session={session} onSession={onSession} onScanFor={onScanFor} currentProfile={currentProfile} />;
}

function Auth({ online, onSession }: { online: boolean; onSession: (s: Session) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "register") {
        const r = await family.register(f.name.trim(), f.email.trim(), f.password);
        onSession({ familyId: r.family_id, headName: f.name.trim() });
      } else {
        const r = await family.login(f.email, f.password);
        onSession({ familyId: r.family_id, headName: r.head_name });
      }
    } catch (e: any) {
      setErr(e.offline ? needsApi("Household accounts") : e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth-copy">
        <span className="kicker">Household</span>
        <h1>One kitchen, several health profiles.</h1>
        <p>
          Keep a profile for each person you shop for. Barcode scans made for a member are saved to their history, and the household score
          averages everyone's last ten scans.
        </p>
      </div>
      <form className="card auth-form" onSubmit={submit} aria-busy={busy}>
        <Tabs
          id="auth"
          label="Account"
          className="modes small"
          value={mode}
          onChange={(m) => (setMode(m), setErr(""))}
          options={[
            ["login", "Sign in"],
            ["register", "Create household"],
          ]}
        />
        <div className="auth-fields" {...tabPanelProps("auth", mode)}>
        {mode === "register" && (
          <label>
            Your name
            <input required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          </label>
        )}
        <label>
          Email
          <input required aria-invalid={!!err || undefined} aria-describedby={err ? "auth-err" : undefined} type="email" autoComplete="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} />
        </label>
        <label>
          Password
          <input
            required
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            value={f.password}
            onChange={(e) => setF({ ...f, password: e.target.value })}
          />
        </label>
        </div>
        {err && (
          <p className="err" role="alert" id="auth-err">
            {err}
          </p>
        )}
        {!online && !err && <p className="muted">{needsApi("Household accounts")}</p>}
        <button className="run" disabled={busy}>
          {busy ? <span className="dots">One moment</span> : mode === "login" ? "Sign in" : "Create household"}
        </button>
      </form>
    </div>
  );
}

type Draft = { name: string; relationship: string; age: string; conditions: string[]; medications: string[] };
const EMPTY: Draft = { name: "", relationship: "", age: "", conditions: [], medications: [] };
const RELATIONSHIPS = ["Partner", "Child", "Parent", "Grandparent", "Sibling", "Other"];

function Dashboard({ session, onSession, onScanFor }: Omit<Props, "session" | "online"> & { session: Session }) {
  const [data, setData] = useState<{ family_score: number | null; members: Member[] } | null>(null);
  const [meds, setMeds] = useState<Record<string, string[]>>({});
  const [err, setErr] = useState("");
  // null = dialog closed, "new" = adding, otherwise the member being edited
  const [editing, setEditing] = useState<"new" | Member | null>(null);
  const addBtn = useRef<HTMLButtonElement>(null);

  const load = async () => {
    try {
      const [d, m] = await Promise.all([family.dashboard(session.familyId), family.members(session.familyId)]);
      setData(d);
      setMeds(Object.fromEntries(m.members.map((x) => [x.member_id, x.medications ?? []])));
    } catch (e: any) {
      setErr(e.message);
    }
  };
  useEffect(() => {
    load();
  }, [session.familyId]);

  const save = async (d: Draft) => {
    const body = {
      name: d.name.trim(),
      relationship: d.relationship || "Family Member",
      age: d.age ? Number(d.age) : null,
      conditions: d.conditions,
      medications: d.medications,
    };
    if (editing === "new") await family.addMember(session.familyId, body);
    else if (editing) await family.updateMember(session.familyId, editing.member_id, body);
    announce(editing === "new" ? `${body.name} added to the household.` : `${body.name} updated.`);
    setEditing(null);
    await load();
  };

  const remove = async (m: Member) => {
    if (!window.confirm(`Remove ${m.name} from the household? Their scan history stays in the database.`)) return;
    try {
      await family.removeMember(session.familyId, m.member_id);
      announce(`${m.name} removed.`);
      await load();
      addBtn.current?.focus();
    } catch (e: any) {
      setErr(e.message);
    }
  };

  return (
    <div className="household">
      <header className="hh-head">
        <div>
          <span className="kicker">{session.headName.trim()}'s household</span>
          <h1>
            {data?.family_score != null ? (
              <>
                Household score <span className="hh-score">{data.family_score}</span>
              </>
            ) : (
              "No scans saved yet"
            )}
          </h1>
          {data?.family_score == null && (
            <p className="muted hh-sub">Press “Scan for …” on a member, then scan a product. The result is saved to their history.</p>
          )}
        </div>
        <div className="hh-actions">
          <button ref={addBtn} className="run small" onClick={() => setEditing("new")}>
            Add member
          </button>
          <button className="link" onClick={() => onSession(null)}>
            Sign out
          </button>
        </div>
      </header>
      {err && (
        <p className="err" role="alert">
          {err}
        </p>
      )}
      <div className="members">
        {data?.members.map((m) => (
          <article key={m.member_id} className="card member" aria-labelledby={`m-${m.member_id}`}>
            <div className="member-top">
              <div>
                <h2 id={`m-${m.member_id}`} className="member-name">
                  {m.name}
                </h2>
                <span className="muted">
                  {m.is_head ? "Account holder" : m.relationship}
                  {m.age ? ` · ${m.age}` : ""}
                </span>
              </div>
              <Ring value={m.stats?.avg_safety_score ?? null} />
            </div>
            <div className="chips">
              {m.conditions.length === 0 && <span className="empty">No conditions</span>}
              {m.conditions.map((c) => (
                <span key={c} className="tag">
                  {pretty(c)}
                </span>
              ))}
              {(meds[m.member_id] ?? []).map((c) => (
                <span key={c} className="tag tag-med">
                  {pretty(c)}
                </span>
              ))}
            </div>
            <dl className="mstats">
              <div>
                <dt>Scans</dt>
                <dd>{m.stats?.total_scans ?? 0}</dd>
              </div>
              <div>
                <dt>Unsafe</dt>
                <dd>{m.stats?.unsafe_scans ?? 0}</dd>
              </div>
              <div>
                <dt>Last</dt>
                <dd>{m.stats?.last_scan ? new Date(m.stats.last_scan).toLocaleDateString() : "—"}</dd>
              </div>
            </dl>
            <div className="member-actions">
              <button
                className="run small"
                aria-label={`Scan a product for ${m.name}`}
                onClick={() => onScanFor({ name: m.name, conditions: m.conditions, medications: meds[m.member_id] ?? [], memberId: m.member_id })}
              >
                Scan for {m.name.trim().split(" ")[0]}
              </button>
              <button className="ghost" aria-label={`Edit ${m.name}`} onClick={() => setEditing({ ...m, medications: meds[m.member_id] ?? [] })}>
                Edit
              </button>
              {!m.is_head && (
                <button className="ghost danger" aria-label={`Remove ${m.name}`} onClick={() => remove(m)}>
                  Remove
                </button>
              )}
            </div>
          </article>
        ))}
      </div>

      {editing && (
        <MemberDialog
          initial={
            editing === "new"
              ? EMPTY
              : {
                  name: editing.name,
                  relationship: editing.relationship ?? "",
                  age: editing.age ? String(editing.age) : "",
                  conditions: editing.conditions,
                  medications: editing.medications ?? [],
                }
          }
          isNew={editing === "new"}
          isHead={editing !== "new" && !!editing.is_head}
          onSave={save}
          onClose={() => setEditing(null)}
        />
      )}
    </div>
  );
}

function MemberDialog({
  initial,
  isNew,
  isHead,
  onSave,
  onClose,
}: {
  initial: Draft;
  isNew: boolean;
  isHead: boolean;
  onSave: (d: Draft) => Promise<void>;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [d, setD] = useState<Draft>(initial);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  // Native modal dialog: traps focus, closes on Escape, restores focus on close.
  useEffect(() => {
    const el = ref.current!;
    el.showModal();
    document.getElementById("mf-name")?.focus();
    return () => el.close();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!d.name.trim()) {
      setErr("Enter a name.");
      document.getElementById("mf-name")?.focus();
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await onSave(d);
    } catch (e: any) {
      setErr(e.message);
      setBusy(false);
    }
  };

  return (
    <dialog ref={ref} className="member-dialog" aria-labelledby="mf-title" onCancel={(e) => (e.preventDefault(), onClose())}>
      <form onSubmit={submit} noValidate aria-busy={busy}>
        <header className="md-head">
          <h2 id="mf-title">{isNew ? "Add a household member" : `Edit ${initial.name.trim()}`}</h2>
          <button type="button" className="md-close" aria-label="Close" onClick={onClose}>
            <svg width="14" height="14" viewBox="0 0 14 14" aria-hidden>
              <path d="M2 2l10 10M12 2 2 12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
        </header>

        <div className="md-body">
          <div className="md-row">
            <label className="md-field md-grow">
              Name
              <input
                id="mf-name"
                value={d.name}
                onChange={(e) => setD({ ...d, name: e.target.value })}
                autoComplete="off"
                aria-invalid={(!!err && !d.name.trim()) || undefined}
                aria-describedby={err ? "mf-err" : undefined}

              />
            </label>
            <label className="md-field md-age">
              Age
              <input inputMode="numeric" value={d.age} onChange={(e) => setD({ ...d, age: e.target.value.replace(/\D/g, "").slice(0, 3) })} />
            </label>
          </div>

          {!isHead && (
            <fieldset className="md-rel">
              <legend>Relationship</legend>
              <div className="chips">
                {RELATIONSHIPS.map((r) => (
                  <label key={r} className="radio-chip">
                    <input type="radio" name="rel" value={r} checked={d.relationship === r} onChange={() => setD({ ...d, relationship: r })} />
                    <span>{r}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          <section className="md-sec" aria-labelledby="mf-cond">
            <h3 id="mf-cond">Conditions</h3>
            <ConditionPicker idPrefix="mf" value={d.conditions} onChange={(conditions) => setD({ ...d, conditions })} />
          </section>

          <section className="md-sec" aria-labelledby="mf-med">
            <h3 id="mf-med">Medicines</h3>
            <MedicinePicker idPrefix="mf" value={d.medications} onChange={(medications) => setD({ ...d, medications })} />
          </section>
        </div>

        <footer className="md-foot">
          {err && (
            <p className="err" role="alert" id="mf-err">
              {err}
            </p>
          )}
          <button type="button" className="ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="run small" disabled={busy}>
            {busy ? <span className="dots">Saving</span> : isNew ? "Add member" : "Save changes"}
          </button>
        </footer>
      </form>
    </dialog>
  );
}

function Ring({ value }: { value: number | null }) {
  const r = 22;
  const C = 2 * Math.PI * r;
  const t = value == null ? "none" : value >= 65 ? "safe" : value >= 45 ? "mod" : "unsafe";
  return (
    <svg className={`ring t-${t}`} width="56" height="56" viewBox="0 0 56 56" role="img" aria-label={value == null ? "No scans yet" : `Average score ${value} out of 100`}>
      <circle cx="28" cy="28" r={r} className="ring-bg" />
      {value != null && <circle cx="28" cy="28" r={r} className="ring-fg" strokeDasharray={`${(value / 100) * C} ${C}`} />}
      <text x="28" y="33" textAnchor="middle" aria-hidden>
        {value ?? "–"}
      </text>
    </svg>
  );
}
