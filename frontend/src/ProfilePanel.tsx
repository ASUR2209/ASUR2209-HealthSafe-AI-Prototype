import { useRef, useState } from "react";
import type { Profile } from "./api";
import { CONDITION_GROUPS, MEDICATIONS, pretty } from "./data";
import { announce } from "./a11y";

export function ProfilePanel({ profile, onChange }: { profile: Profile; onChange: (p: Profile) => void }) {
  return (
    <section className="profile" aria-labelledby="profile-heading">
      <h2 id="profile-heading" className="sr-only">
        Health profile
      </h2>
      <div className="rx">
        <div className="rx-top">
          <label className="rx-kicker" htmlFor="rx-name">
            Checking for
          </label>
          {profile.memberId && <span className="rx-linked">household member</span>}
        </div>
        <input
          id="rx-name"
          className="rx-name"
          value={profile.name}
          onChange={(e) => onChange({ ...profile, name: e.target.value, memberId: undefined })}
          placeholder="Your name"
          autoComplete="name"
        />
        <p className="rx-summary">
          <span>
            <b>{profile.conditions.length}</b> condition{profile.conditions.length === 1 ? "" : "s"}
          </span>
          <span>
            <b>{profile.medications.length}</b> medicine{profile.medications.length === 1 ? "" : "s"}
          </span>
        </p>
      </div>

      <section className="p-sec" aria-labelledby="cond-heading">
        <h3 id="cond-heading">Conditions</h3>
        <ConditionPicker idPrefix="p" value={profile.conditions} onChange={(conditions) => onChange({ ...profile, conditions })} />
      </section>

      <section className="p-sec" aria-labelledby="med-heading">
        <h3 id="med-heading">Medicines</h3>
        <MedicinePicker idPrefix="p" value={profile.medications} onChange={(medications) => onChange({ ...profile, medications })} />
      </section>
    </section>
  );
}

export function ConditionPicker({ idPrefix, value, onChange }: { idPrefix: string; value: string[]; onChange: (v: string[]) => void }) {
  const toggle = (c: string) => onChange(value.includes(c) ? value.filter((x) => x !== c) : [...value, c]);
  return (
    <>
      <p className="hint p-hint">Select every condition that applies. Each button shows whether it's on.</p>
      {CONDITION_GROUPS.map((g) => {
        const gid = `${idPrefix}-cg-${g.label.replace(/\W+/g, "-").toLowerCase()}`;
        return (
          <div key={g.label} className="cgroup" role="group" aria-labelledby={gid}>
            <span id={gid} className="cgroup-label">
              {g.label}
            </span>
            <div className="chips">
              {g.items.map((c) => {
                const on = value.includes(c);
                return (
                  <button key={c} type="button" aria-pressed={on} className="tog" onClick={() => toggle(c)}>
                    <svg className="tog-mark" width="12" height="12" viewBox="0 0 12 12" aria-hidden>
                      {on ? (
                        <path d="M2 6.5 5 9l5-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      ) : (
                        <path d="M6 2v8M2 6h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                      )}
                    </svg>
                    {pretty(c)}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </>
  );
}

export function MedicinePicker({ idPrefix, value, onChange }: { idPrefix: string; value: string[]; onChange: (v: string[]) => void }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [activeOpt, setActiveOpt] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const id = (s: string) => `${idPrefix}-${s}`;

  const add = (m: string) => {
    if (!value.includes(m)) onChange([...value, m]);
    setQuery("");
    setOpen(false);
    announce(`${pretty(m)} added to medicines.`);
  };
  const remove = (m: string) => {
    onChange(value.filter((x) => x !== m));
    announce(`${pretty(m)} removed.`);
    // The removed chip took focus with it; return it somewhere predictable.
    input.current?.focus();
  };

  const matches = query ? MEDICATIONS.filter((m) => m.includes(query.toLowerCase()) && !value.includes(m)).slice(0, 6) : [];
  const expanded = open && matches.length > 0;

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActiveOpt((i) => Math.min(matches.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveOpt((i) => Math.max(0, i - 1));
    } else if (e.key === "Enter" && expanded) {
      e.preventDefault();
      add(matches[activeOpt] ?? matches[0]);
    } else if (e.key === "Escape" && expanded) {
      // Stop the Escape here so it doesn't also close a surrounding dialog.
      e.preventDefault();
      e.stopPropagation();
      setOpen(false);
    }
  };

  return (
    <>
      <div className="medbox">
        <label className="sr-only" htmlFor={id("med-input")}>
          Add a medicine
        </label>
        <input
          ref={input}
          id={id("med-input")}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={expanded}
          aria-controls={id("med-listbox")}
          aria-activedescendant={expanded ? id(`med-opt-${activeOpt}`) : undefined}
          aria-describedby={id("med-hint")}
          autoComplete="off"
          value={query}
          onChange={(e) => (setQuery(e.target.value), setOpen(true), setActiveOpt(0))}
          onKeyDown={onKey}
          onBlur={() => setTimeout(() => setOpen(false), 120)}
          placeholder="Search, e.g. metformin"
        />
        <ul id={id("med-listbox")} className="med-suggest" role="listbox" aria-label="Matching medicines" hidden={!expanded}>
          {matches.map((m, i) => (
            <li
              key={m}
              id={id(`med-opt-${i}`)}
              role="option"
              aria-selected={i === activeOpt}
              className={i === activeOpt ? "on" : ""}
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => add(m)}
            >
              {pretty(m)}
            </li>
          ))}
        </ul>
        <p id={id("med-hint")} className="hint">
          Use the arrow keys to pick a match, Enter to add.
        </p>
      </div>
      {value.length === 0 ? (
        <p className="empty meds-empty">None added. Medicine conflicts are only checked for medicines listed here.</p>
      ) : (
        <ul className="chips meds" aria-label="Medicines added">
          {value.map((m) => (
            <li key={m} className="med">
              {pretty(m)}
              <button type="button" aria-label={`Remove ${pretty(m)}`} onClick={() => remove(m)}>
                <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden>
                  <path d="M2 2l6 6M8 2 2 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
                </svg>
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
