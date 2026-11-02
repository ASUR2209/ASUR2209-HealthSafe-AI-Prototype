import { useState } from "react";
import { recommend, type Alternative, type Profile, type Result } from "./api";
import { pretty } from "./data";

const tone = (r: string) => (r === "HIGH" ? "unsafe" : r === "MEDIUM" ? "mod" : "safe");

export function Findings({ result, profile }: { result: Result; profile: Profile }) {
  const [alts, setAlts] = useState<{ state: "idle" | "loading" | "done" | "error"; items: Alternative[]; msg?: string }>({ state: "idle", items: [] });

  // One row per distinct keyword; the API can match the same keyword in several ingredients.
  const byKeyword = new Map<string, (typeof result.flagged)[number] & { count: number }>();
  for (const f of result.flagged) {
    const prev = byKeyword.get(f.matched_keyword);
    if (prev) prev.count++;
    else byKeyword.set(f.matched_keyword, { ...f, count: 1 });
  }
  const flags = [...byKeyword.values()].sort((a, b) => (a.risk === b.risk ? a.position_in_list - b.position_in_list : a.risk === "HIGH" ? -1 : 1));

  const conflicts = result.conflicts.filter(
    (c, i, all) => all.findIndex((x) => x.medication === c.medication && x.matched_keyword === c.matched_keyword) === i
  );

  const loadAlts = async () => {
    setAlts({ state: "loading", items: [] });
    try {
      const r = await recommend(result, profile);
      setAlts({ state: "done", items: r.alternatives ?? [], msg: r.error });
    } catch (e: any) {
      setAlts({ state: "error", items: [], msg: e.offline ? "Alternatives need the Flask API running." : e.message });
    }
  };

  return (
    <div className="findings">
      {result.product && (
        <section className="card product">
          <div>
            <span className="kicker">Product</span>
            <h3>{result.product.name}</h3>
            <span className="muted">{result.product.brand}</span>
          </div>
          {result.product.nutriscore && result.product.nutriscore !== "UNKNOWN" && (
            <span className={`nutri n-${result.product.nutriscore.toLowerCase()}`}>
              <span className="sr-only">Nutri-Score </span>
              {result.product.nutriscore}
            </span>
          )}
          {result.product.warnings.length > 0 && (
            <ul className="nwarn">
              {result.product.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
        </section>
      )}

      <section className="card">
        <header className="card-head">
          <h3>What we flagged</h3>
          <span className="muted">ordered by risk, then by position on the label</span>
        </header>
        {flags.length === 0 ? (
          <p className="empty">
            {profile.conditions.length === 0
              ? "Add conditions to the profile to get personal flags. The score above comes from the model and heuristic alone."
              : "No ingredient matched a rule for the conditions in this profile."}
          </p>
        ) : (
          <ul className="flags">
            {flags.map((f) => (
              <li key={f.matched_keyword} className={`flag t-${tone(f.risk)}`}>
                <span className="flag-pos">
                  <span className="sr-only">Position on label: </span>#{f.position_in_list}
                </span>
                <div>
                  <b>{pretty(f.matched_keyword)}</b>
                  {f.count > 1 && <span className="muted"> ×{f.count}</span>}
                  <p>{f.reason}</p>
                </div>
                <div className="flag-side">
                  <span className={`risk r-${tone(f.risk)}`}>{f.risk}</span>
                  <span className="for">{f.harmful_for.map(pretty).join(" · ")}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      {conflicts.length > 0 && (
        <section className="card">
          <header className="card-head">
            <h3>Medicine conflicts</h3>
          </header>
          <ul className="conflicts">
            {conflicts.map((c, i) => (
              <li key={i}>
                <span className="pill">{pretty(c.medication)}</span>
                <span className="plus">
                  <span aria-hidden>+</span>
                  <span className="sr-only">with</span>
                </span>
                <span className="ingr">{c.matched_keyword}</span>
                <span className={`risk r-${tone(c.severity)}`}>{c.severity}</span>
                <p>{c.conflict}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result.verdict !== "Safe" && (
        <section className="card alts" aria-labelledby="alts-heading">
          <header className="card-head">
            <h3 id="alts-heading">Alternatives</h3>
            {alts.state === "idle" && (
              <button className="ghost" onClick={loadAlts}>
                Find alternatives
              </button>
            )}
          </header>
          <div aria-live="polite">
          {alts.state === "idle" && <p className="muted">Scores similar products from the same category against this profile.</p>}
          {alts.state === "loading" && <p className="muted dots">Scoring candidates</p>}
          {alts.state === "error" && <p className="empty">{alts.msg}</p>}
          {alts.state === "done" && alts.items.length === 0 && <p className="empty">{alts.msg ?? "No safer product found in this category."}</p>}
          {alts.items.length > 0 && alts.items.every((a) => a.score <= result.score) && (
            <p className="muted">None of these scored higher than this product for this profile.</p>
          )}
          {alts.items.length > 0 && (
            <ol className="alt-list">
              {alts.items.map((a) => (
                <li key={a.product_name}>
                  <div>
                    <b>{a.product_name}</b>
                    <span className="muted">{a.brand}</span>
                  </div>
                  <span className={`altscore t-${a.verdict === "Safe" ? "safe" : a.verdict === "Moderate" ? "mod" : "unsafe"}`}>
                    {a.score}
                    <span className="sr-only"> out of 100, {a.verdict}</span>
                  </span>
                </li>
              ))}
            </ol>
          )}
          </div>
        </section>
      )}

      {result.ocrText && (
        <details className="card ocr">
          <summary>Text the OCR read from the photo</summary>
          <pre>{result.ocrText}</pre>
        </details>
      )}

      <p className="disclaimer">
        Prototype assessment. The ingredient and medicine rules are not clinically validated and don't replace advice from your doctor or
        pharmacist.
      </p>
    </div>
  );
}
