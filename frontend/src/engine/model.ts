/* In-browser copy of ml/healthsafe_model_v6.pkl: sklearn TfidfVectorizer → XGBClassifier.
   The JSON comes from ml/export_browser_model.py. Arithmetic follows the libraries:
   TF-IDF in float64, XGBoost features, thresholds and margin in float32. */

export interface ModelJSON {
  tfidf: { vocab: string[]; idf: number[]; ngram: [number, number]; token_pattern: string };
  xgb: {
    base_score: number;
    classes: number[];
    trees: { l: number[]; r: number[]; f: number[]; c: number[]; d: number[] }[];
  };
}

const f32 = Math.fround;

export class SafetyModel {
  private index = new Map<string, number>();
  private idf: number[];
  private ngram: [number, number];
  private token: RegExp;
  private trees: { l: Int32Array; r: Int32Array; f: Int32Array; c: Float32Array; d: Uint8Array }[];
  private baseMargin: number;
  readonly classes: number[];

  constructor(m: ModelJSON) {
    m.tfidf.vocab.forEach((t, i) => this.index.set(t, i));
    this.idf = m.tfidf.idf;
    this.ngram = m.tfidf.ngram;
    // sklearn applies token_pattern with re.findall.
    this.token = new RegExp(m.tfidf.token_pattern, "g");
    // JSON holds the shortest decimal that round-trips to float32, which as a double can
    // sit just above the real threshold; Float32Array restores XGBoost's exact values.
    this.trees = m.xgb.trees.map((t) => ({
      l: Int32Array.from(t.l),
      r: Int32Array.from(t.r),
      f: Int32Array.from(t.f),
      c: Float32Array.from(t.c),
      d: Uint8Array.from(t.d),
    }));
    const p = m.xgb.base_score;
    // binary:logistic stores base_score as a probability; trees add to its logit.
    this.baseMargin = f32(Math.log(p / (1 - p)));
    this.classes = m.xgb.classes;
  }

  /** TfidfVectorizer.transform for one document: sparse {featureIndex: value}. */
  vectorize(doc: string): Map<number, number> {
    // strip_accents="unicode" after lowercasing; the caller already reduced text to a-z.
    const text = doc.toLowerCase().normalize("NFKD").replace(/\p{M}/gu, "");
    const tokens = text.match(this.token) ?? [];
    const counts = new Map<number, number>();
    const add = (term: string) => {
      const i = this.index.get(term);
      if (i !== undefined) counts.set(i, (counts.get(i) ?? 0) + 1);
    };
    const [minN, maxN] = this.ngram;
    for (let n = minN; n <= Math.min(maxN, tokens.length); n++) {
      for (let i = 0; i + n <= tokens.length; i++) add(n === 1 ? tokens[i] : tokens.slice(i, i + n).join(" "));
    }
    // Tree thresholds sit exactly on training values, so this must be bit-identical to
    // sklearn: CSR rows are in column order, and the l2 norm is summed sequentially in it.
    const cols = [...counts.keys()].sort((a, b) => a - b);
    const vals = cols.map((i) => (1 + Math.log(counts.get(i)!)) * this.idf[i]); // sublinear_tf
    let sq = 0;
    for (const v of vals) sq += v * v;
    const norm = Math.sqrt(sq);
    const out = new Map<number, number>();
    cols.forEach((i, k) => out.set(i, norm > 0 ? vals[k] / norm : vals[k]));
    return out;
  }

  /** Probability of class 1 ("Unsafe"), as XGBClassifier.predict_proba()[:, 1]. */
  probaUnsafe(doc: string): number {
    const x = this.vectorize(doc);
    let margin = this.baseMargin;
    for (const t of this.trees) {
      let n = 0;
      while (t.l[n] !== -1) {
        const v = x.get(t.f[n]);
        // Sparse input: absent features are "missing" and follow the default branch.
        if (v === undefined) n = t.d[n] ? t.l[n] : t.r[n];
        else n = f32(v) < t.c[n] ? t.l[n] : t.r[n];
      }
      margin = f32(margin + t.c[n]); // leaf value is stored in split_conditions
    }
    return f32(1 / (1 + f32(Math.exp(-margin))));
  }
}

export async function loadModel(url: string): Promise<SafetyModel> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load the model (${res.status})`);
  return new SafetyModel(await res.json());
}
