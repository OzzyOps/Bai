/**
 * Compile bai-core.tokens.json into CSS custom properties, a Tailwind preset
 * and typed TS constants.
 *
 * Tokens have exactly one source of truth. Nothing downstream may hardcode a
 * value — `scripts/validate-tokens.py` fails CI if a product theme overrides a
 * locked path, and this build is what makes the tokens usable so nobody needs to.
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const SRC = resolve(here, 'src/bai-core.tokens.json');
const OUT = resolve(here, 'dist');

type Node = { $value?: unknown; $type?: string; [k: string]: unknown };

const core = JSON.parse(readFileSync(SRC, 'utf8')) as Node;

/** Flatten to dotted paths, skipping $-prefixed metadata. */
function flatten(node: Node, prefix = ''): Map<string, unknown> {
  const out = new Map<string, unknown>();
  if (node && typeof node === 'object') {
    if ('$value' in node) { out.set(prefix, node.$value); return out; }
    for (const [k, v] of Object.entries(node)) {
      if (k.startsWith('$')) continue;
      for (const [p, val] of flatten(v as Node, prefix ? `${prefix}.${k}` : k)) out.set(p, val);
    }
  }
  return out;
}

const tokens = flatten(core);

/** Resolve {alias.path} references. Depth-limited so a cycle fails loudly. */
function resolveAlias(value: unknown, depth = 0): unknown {
  if (typeof value !== 'string' || !value.startsWith('{') || !value.endsWith('}')) return value;
  if (depth > 10) throw new Error(`token alias cycle at ${value}`);
  const target = value.slice(1, -1);
  if (!tokens.has(target)) throw new Error(`token ${value} does not resolve`);
  return resolveAlias(tokens.get(target), depth + 1);
}

const cssVar = (path: string) => '--' + path.replace(/\./g, '-').toLowerCase();

// ── CSS ────────────────────────────────────────────────────────────────────
const light: string[] = [];
const dark: string[] = [];

for (const [path, raw] of tokens) {
  const value = resolveAlias(raw);
  const rendered = Array.isArray(value) ? value.join(', ') : String(value);
  // surface.light.* and text.light.* become the root palette; .dark.* the override
  if (/\.light\./.test(path)) light.push(`  ${cssVar(path.replace('.light', ''))}: ${rendered};`);
  else if (/\.dark\./.test(path)) dark.push(`  ${cssVar(path.replace('.dark', ''))}: ${rendered};`);
  else light.push(`  ${cssVar(path)}: ${rendered};`);
}

const css = `/* GENERATED from bai-core.tokens.json — do not edit. */
:root {
${light.join('\n')}
}

/* Default "system" theme: only prefers-color-scheme separates light from dark. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
${dark.join('\n')}
  }
}

/* Explicit choice wins in both directions. */
:root[data-theme="dark"] {
${dark.join('\n')}
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
`;

// ── Tailwind preset ────────────────────────────────────────────────────────
const colorEntries = [...tokens.keys()]
  .filter((p) => p.startsWith('color.') && !/\.(light|dark)\./.test(p))
  .map((p) => `      '${p.replace('color.', '').replace(/\./g, '-')}': 'var(${cssVar(p)})',`);

const preset = `/* GENERATED from bai-core.tokens.json — do not edit. */
export default {
  theme: {
    extend: {
      colors: {
${colorEntries.join('\n')}
      },
      fontFamily: {
        sans: 'var(--typography-fontfamily-sans)',
        display: 'var(--typography-fontfamily-display)',
        mono: 'var(--typography-fontfamily-mono)',
      },
      borderRadius: {
        sm: 'var(--radius-sm)', md: 'var(--radius-md)',
        lg: 'var(--radius-lg)', xl: 'var(--radius-xl)', pill: 'var(--radius-pill)',
      },
    },
  },
};
`;

// ── JS constants ───────────────────────────────────────────────────────────
// index.js must be plain JavaScript. It was emitted with type annotations and a
// `as const`, which typechecked fine (nothing compiles it) and then failed at
// bundle time — Rollup parses it as JS and stops at the first colon. Types
// belong in index.d.ts, written below.
const ts = `/* GENERATED from bai-core.tokens.json — do not edit. */
export const CONFIDENCE_FLOOR = 0.7;

/** Drives which token a fact renders with. Low confidence must never read as safe. */
export function displayState(confidence) {
  if (confidence >= 0.9) return 'high';
  if (confidence >= CONFIDENCE_FLOOR) return 'medium';
  return 'unknown';
}

export const tokens = ${JSON.stringify(
  Object.fromEntries([...tokens].map(([k, v]) => [k, resolveAlias(v)])), null, 2,
)};
`;

mkdirSync(OUT, { recursive: true });
writeFileSync(resolve(OUT, 'tokens.css'), css);
writeFileSync(resolve(OUT, 'tailwind-preset.js'), preset);
writeFileSync(resolve(OUT, 'index.js'), ts);
writeFileSync(
  resolve(OUT, 'index.d.ts'),
  `/* GENERATED from bai-core.tokens.json — do not edit. */
export declare const CONFIDENCE_FLOOR: number;
export declare function displayState(confidence: number): 'high' | 'medium' | 'unknown';
export declare const tokens: Readonly<Record<string, string | readonly string[] | number>>;
export type TokenPath = keyof typeof tokens;
`,
);

console.log(`✓ tokens built — ${tokens.size} tokens → tokens.css, tailwind-preset.js, index.js`);
