import { useRef, useState } from "react";
import { ingredientRisks, norm, type Result } from "./api";
import { pretty } from "./data";
import { SrOnly } from "./a11y";

/* The result rendered as a gel under UV: one well per ingredient, one lane
   per layer of the backend pipeline. Bands "run" down on mount.
   Risk is carried by band shape as well as colour (solid = high, striped =
   medium, thin = no flag), and every value is also available as a table. */

const tone = (r: string | null) => (r === "HIGH" ? "unsafe" : r === "MEDIUM" || r === "LOW" ? "mod" : "safe");
const riskWord = (r: string | null) => (r === "HIGH" ? "High risk" : r === "MEDIUM" ? "Medium risk" : r === "LOW" ? "Low risk" : "No flag");

export function Lightbox({ result, running }: { result: Result | null; running: boolean }) {
  const [hover, setHover] = useState<number | null>(null);
  const [active, setActive] = useState(0);
  const [pinned, setPinned] = useState<number | null>(null);
  const [view, setView] = useState<"gel" | "table">("gel");
  const wellRefs = useRef<(HTMLButtonElement | null)[]>([]);

  if (!result) return <IdleBox running={running} />;

  const ings = result.ingredients;
  const risks = ingredientRisks(ings, result.flagged);
  const heur = risks.map((r) => (r === "HIGH" ? 15 : r === "MEDIUM" ? 45 : r === "LOW" ? 70 : 90));
  const medHits = ings.map((ing) => result.conflicts.filter((c) => norm(ing).includes(c.matched_keyword)));
  const flagsFor = (i: number) => result.flagged.filter((f) => norm(ings[i]).includes(f.matched_keyword));
  const v = result.verdict;
  const vTone = v === "Safe" ? "safe" : v === "Moderate" ? "mod" : "unsafe";
  const fi = hover ?? pinned;

  const describe = (i: number) => {
    const parts = flagsFor(i).map((f) => `${riskWord(f.risk)} for ${f.harmful_for.map(pretty).join(", ")}: ${f.reason}`);
    medHits[i].forEach((c) => parts.push(`Interacts with ${c.medication}: ${c.conflict}`));
    return parts.length ? parts.join(". ") : "No match against your profile";
  };

  const go = (i: number) => {
    const n = Math.max(0, Math.min(ings.length - 1, i));
    setActive(n);
    setPinned(n);
    wellRefs.current[n]?.focus();
  };

  const onWellKey = (e: React.KeyboardEvent, i: number) => {
    const map: Record<string, number> = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: ings.length - 1 };
    if (e.key in map) {
      e.preventDefault();
      go(map[e.key]);
    } else if (e.key === "Escape") setPinned(null);
  };

  return (
    <section className={`lightbox is-${vTone}`} aria-labelledby="results-heading" key={result.ingredientsText + result.score}>
      <header className="lb-head">
        <h2 id="results-heading" className="lb-title" tabIndex={-1}>
          Results
        </h2>
        <span className="lb-meta">
          {ings.length} ingredients · {result.source === "photo" ? "read from label photo" : result.source === "barcode" ? "from barcode" : "typed"}
          {result.demo && <em className="lb-demo"> · demo engine, backend offline</em>}
        </span>
        <div className="lb-view" role="group" aria-label="Results view">
          <button type="button" aria-pressed={view === "gel"} onClick={() => setView("gel")}>
            Lanes
          </button>
          <button type="button" aria-pressed={view === "table"} onClick={() => setView("table")}>
            Table
          </button>
        </div>
      </header>

      <div className="lb-body">
        {view === "gel" ? (
          <div className="gel-wrap">
            <p id="gel-help" className="sr-only">
              One button per ingredient. Use the arrow keys to move between ingredients; the explanation is read with each one. Switch to
              Table for every value at once.
            </p>
            <div
              className="gel"
              style={{ ["--n" as any]: ings.length }}
              onMouseLeave={() => setHover(null)}
              role="group"
              aria-label="Ingredients"
              aria-describedby="gel-help"
            >
              <div className="lane-label" aria-hidden />
              {ings.map((ing, i) => (
                <button
                  key={"w" + i}
                  ref={(el) => (wellRefs.current[i] = el)}
                  type="button"
                  className={`well ${fi === i ? "is-focus" : ""}`}
                  tabIndex={i === active ? 0 : -1}
                  aria-label={`${i + 1} of ${ings.length}: ${ing}. ${riskWord(risks[i])}${medHits[i].length ? ", medicine conflict" : ""}. Heuristic ${heur[i]}. ${describe(i)}.`}
                  onMouseEnter={() => setHover(i)}
                  onFocus={() => (setActive(i), setPinned(i))}
                  onClick={() => setPinned(pinned === i ? null : i)}
                  onKeyDown={(e) => onWellKey(e, i)}
                >
                  <span aria-hidden>{ing}</span>
                </button>
              ))}

              <div className="lane-label" aria-hidden>
                <b>Your profile</b>
                <small>rule engine</small>
              </div>
              {ings.map((_, i) => (
                <div key={"r" + i} className={`cell ${fi === i ? "is-focus" : ""}`} aria-hidden>
                  {(risks[i] || medHits[i].length > 0) && (
                    <i className={`band b-${tone(risks[i] ?? "MEDIUM")} p-${risks[i] === "HIGH" ? "high" : "med"}`} style={{ ["--d" as any]: `${i * 45}ms` }} />
                  )}
                  {medHits[i].length > 0 && <i className="pill-dot" style={{ ["--d" as any]: `${i * 45 + 200}ms` }} />}
                </div>
              ))}

              <div className="lane-label" aria-hidden>
                <b>Ingredient</b>
                <small>heuristic {result.heuristic != null && <>· {result.heuristic}</>}</small>
              </div>
              {ings.map((_, i) => (
                <div key={"h" + i} className={`cell ${fi === i ? "is-focus" : ""}`} aria-hidden>
                  <i
                    className={`band faint b-${heur[i] >= 80 ? "safe" : heur[i] >= 45 ? "mod" : "unsafe"} p-${heur[i] >= 80 ? "none" : heur[i] >= 45 ? "med" : "high"}`}
                    style={{ ["--d" as any]: `${250 + i * 45}ms`, ["--w" as any]: `${heur[i]}%` }}
                  />
                </div>
              ))}

              <div className="lane-label" aria-hidden>
                <b>XGBoost</b>
                <small>{result.model ? `whole list · ${result.model.confidence}% ${result.model.prediction}` : "not available"}</small>
              </div>
              <div className="cell smear-cell" style={{ gridColumn: `2 / span ${ings.length}` }}>
                {result.model ? (
                  <>
                    <i
                      aria-hidden
                      className={`smear b-${result.model.prediction === "Safe" ? "safe" : "unsafe"}`}
                      style={{ ["--w" as any]: `${Math.max(8, result.model.confidence)}%` }}
                    />
                    <SrOnly>
                      XGBoost model, whole ingredient list: {result.model.prediction} with {result.model.confidence}% confidence.
                    </SrOnly>
                  </>
                ) : (
                  <span className="smear-empty">{result.demo ? "Start the Flask API to run the classifier" : "Not returned by this endpoint"}</span>
                )}
              </div>
            </div>
            <ul className="legend" aria-label="Legend">
              <li>
                <i className="lg p-high" /> High risk
              </li>
              <li>
                <i className="lg p-med" /> Medium risk
              </li>
              <li>
                <i className="lg p-none" /> No flag
              </li>
              <li>
                <i className="lg-dot" /> Medicine conflict
              </li>
            </ul>
          </div>
        ) : (
          <ResultTable ings={ings} risks={risks} heur={heur} describe={describe} medHits={medHits.map((m) => m.length)} result={result} />
        )}

        <div className="readout">
          <p className="sr-only">
            Score {result.score} out of 100, {result.scoreLabel}. Verdict: {v}.
          </p>
          <div className="score" aria-hidden>
            <span className="score-n">{result.score}</span>
            <span className="score-of">/100</span>
          </div>
          <div className="verdict" aria-hidden>
            <span className="chip">
              <VerdictIcon v={vTone} /> {v}
            </span>
            <span className="score-label">{result.scoreLabel}</span>
          </div>
          <Meter score={result.score} />
          <p className="readout-note">
            {result.flagged.length === 0 && result.conflicts.length === 0
              ? "Nothing on this label matches your conditions or medicines."
              : `${result.flagged.length} flag${result.flagged.length === 1 ? "" : "s"} for your conditions` +
                (result.conflicts.length ? `, ${result.conflicts.length} medicine conflict${result.conflicts.length === 1 ? "" : "s"}` : "") +
                "."}
          </p>
        </div>
      </div>

      {view === "gel" && (
        <footer className="lb-foot" aria-hidden>
          {fi == null ? (
            <span className="lb-hint">Hover, tap or tab to an ingredient to see why it lit up.</span>
          ) : (
            <span className="lb-detail">
              <b>{ings[fi]}</b> — {describe(fi)}.
            </span>
          )}
        </footer>
      )}
    </section>
  );
}

function ResultTable({
  ings,
  risks,
  heur,
  medHits,
  describe,
  result,
}: {
  ings: string[];
  risks: (string | null)[];
  heur: number[];
  medHits: number[];
  describe: (i: number) => string;
  result: Result;
}) {
  return (
    <div className="lb-table-wrap" tabIndex={0} role="region" aria-label="Ingredient results table">
      <table className="lb-table">
        <caption className="sr-only">
          Each ingredient with its profile rule result, heuristic score and explanation.
          {result.model && ` The XGBoost model scored the whole list ${result.model.prediction}, ${result.model.confidence}% confidence.`}
        </caption>
        <thead>
          <tr>
            <th scope="col">#</th>
            <th scope="col">Ingredient</th>
            <th scope="col">Your profile</th>
            <th scope="col">Heuristic</th>
            <th scope="col">Why</th>
          </tr>
        </thead>
        <tbody>
          {ings.map((ing, i) => (
            <tr key={i}>
              <td>{i + 1}</td>
              <th scope="row">{ing}</th>
              <td>
                <span className={`tr-risk t-${tone(risks[i])}`}>
                  <i className={`lg p-${risks[i] === "HIGH" ? "high" : risks[i] ? "med" : "none"}`} aria-hidden /> {riskWord(risks[i])}
                </span>
                {medHits[i] > 0 && <span className="tr-med"> + medicine</span>}
              </td>
              <td>{heur[i]}</td>
              <td className="tr-why">{describe(i)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {result.model && (
        <p className="tr-model">
          XGBoost (whole list): <b>{result.model.prediction}</b>, {result.model.confidence}% confidence
        </p>
      )}
    </div>
  );
}

function VerdictIcon({ v }: { v: string }) {
  // Shape differs per verdict so it never depends on colour alone.
  if (v === "safe")
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
        <path d="M2 6.5 5 9l5-6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (v === "mod")
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
        <path d="M2.5 6h7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden>
      <path d="M3 3l6 6M9 3 3 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function Meter({ score }: { score: number }) {
  return (
    <div className="meter" aria-hidden>
      <div className="meter-track">
        <span style={{ left: "25%" }} />
        <span style={{ left: "45%" }} />
        <span style={{ left: "65%" }} />
        <span style={{ left: "80%" }} />
      </div>
      <i className="meter-pin" style={{ left: `${score}%` }} />
      <div className="meter-scale">
        <span>Dangerous</span>
        <span>Moderate</span>
        <span>Excellent</span>
      </div>
    </div>
  );
}

function IdleBox({ running }: { running: boolean }) {
  return (
    <section className={`lightbox idle ${running ? "is-running" : ""}`} aria-labelledby="results-heading" aria-busy={running}>
      <header className="lb-head">
        <h2 id="results-heading" className="lb-title" tabIndex={-1}>
          Results
        </h2>
        <span className="lb-meta">{running ? "Running all three layers…" : "Waiting for a label"}</span>
      </header>
      <div className="idle-gel" aria-hidden>
        {Array.from({ length: 14 }).map((_, i) => (
          <div key={i} className="idle-col" style={{ ["--d" as any]: `${i * 90}ms` }}>
            <i />
            <i />
            <i />
          </div>
        ))}
      </div>
      <p className="idle-copy">
        {running
          ? "Matching each ingredient against your profile, then scoring the whole list."
          : "Each ingredient becomes a column. Rows show what your profile rules, the ingredient heuristic and the XGBoost model each found."}
      </p>
    </section>
  );
}
