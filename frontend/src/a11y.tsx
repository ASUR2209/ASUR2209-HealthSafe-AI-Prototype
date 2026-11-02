import { useEffect, useRef, useState, type ReactNode } from "react";

/* Polite live region shared by the whole app. Call announce() after an
   action whose result appears somewhere the user isn't looking. */

let push: ((msg: string) => void) | null = null;
export const announce = (msg: string) => push?.(msg);

export function Announcer() {
  const [msg, setMsg] = useState("");
  useEffect(() => {
    push = (m) => {
      // Clear first so repeating the same message is still announced.
      setMsg("");
      setTimeout(() => setMsg(m), 60);
    };
    return () => {
      push = null;
    };
  }, []);
  return (
    <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {msg}
    </div>
  );
}

export const SrOnly = ({ children }: { children: ReactNode }) => <span className="sr-only">{children}</span>;

/* WAI-ARIA tabs: one tab stop, arrows/Home/End move and select. */
export function Tabs<T extends string>({
  id,
  label,
  value,
  onChange,
  options,
  className = "modes",
}: {
  id: string;
  label: string;
  value: T;
  onChange: (v: T) => void;
  options: [T, string][];
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const idx = options.findIndex(([v]) => v === value);
  const move = (to: number) => {
    const n = (to + options.length) % options.length;
    onChange(options[n][0]);
    refs.current[n]?.focus();
  };
  return (
    <div className={className} role="tablist" aria-label={label}>
      {options.map(([v, l], i) => (
        <button
          key={v}
          ref={(el) => (refs.current[i] = el)}
          type="button"
          role="tab"
          id={`${id}-tab-${v}`}
          aria-controls={`${id}-panel`}
          aria-selected={v === value}
          tabIndex={v === value ? 0 : -1}
          className={v === value ? "on" : ""}
          onClick={() => onChange(v)}
          onKeyDown={(e) => {
            if (e.key === "ArrowRight") move(idx + 1);
            else if (e.key === "ArrowLeft") move(idx - 1);
            else if (e.key === "Home") move(0);
            else if (e.key === "End") move(options.length - 1);
            else return;
            e.preventDefault();
          }}
        >
          {l}
        </button>
      ))}
    </div>
  );
}

export const tabPanelProps = (id: string, value: string) => ({
  role: "tabpanel" as const,
  id: `${id}-panel`,
  "aria-labelledby": `${id}-tab-${value}`,
});
