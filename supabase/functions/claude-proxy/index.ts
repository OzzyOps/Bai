// BAi · claude-proxy
//
// Keeps the Anthropic API key server-side so a static site on GitHub Pages can
// call Claude without shipping a secret to the browser.
//
//   supabase functions deploy claude-proxy
//   supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
//
// Note: a Claude Pro/Max subscription cannot authenticate this. Subscriptions
// cover claude.ai and Claude Code. This needs an API key from
// console.anthropic.com, billed separately as pay-as-you-go.

const ANTHROPIC_API = "https://api.anthropic.com/v1/messages";

// Fails CLOSED. An unset ALLOWED_ORIGINS used to default to "*", which turns
// this into an open proxy to a paid Anthropic account: anyone who finds the URL
// spends your credit. The cost of forgetting a secret should be a broken deploy,
// not a bill.
const ALLOWED_ORIGINS = (Deno.env.get("ALLOWED_ORIGINS") ?? "")
  .split(",").map((s) => s.trim().replace(/\/+$/, "")).filter(Boolean);

/** Explicit opt-in for local development only. */
const ALLOW_ANY_ORIGIN = Deno.env.get("ALLOW_ANY_ORIGIN") === "true";

function originAllowed(origin: string | null): boolean {
  if (ALLOW_ANY_ORIGIN) return true;
  if (ALLOWED_ORIGINS.length === 0) return false;
  if (!origin) return false;
  return ALLOWED_ORIGINS.includes(origin.replace(/\/+$/, ""));
}

// Only these models may be requested. Prevents a caller running up your bill
// on a model you did not budget for.
const ALLOWED_MODELS = new Set([
  "claude-opus-5",
  "claude-sonnet-5",
  "claude-haiku-4-5-20251001",
]);

const MAX_TOKENS_CEILING = 4096;
const MAX_SYSTEM_CHARS = 20_000;
const MAX_MESSAGE_CHARS = 40_000;

function corsHeaders(origin: string | null): Record<string, string> {
  const allow = ALLOW_ANY_ORIGIN ? "*" : (originAllowed(origin) ? origin ?? "" : "");
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Headers": "authorization, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
}

function json(body: unknown, status: number, origin: string | null): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
  });
}

Deno.serve(async (req: Request): Promise<Response> => {
  const origin = req.headers.get("origin");

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }
  if (req.method !== "POST") {
    return json({ error: "Method not allowed. Use POST." }, 405, origin);
  }

  if (!originAllowed(origin)) {
    return json({
      error: "This origin is not permitted to call the proxy.",
      fix: ALLOWED_ORIGINS.length === 0
        ? "supabase secrets set ALLOWED_ORIGINS=https://<user>.github.io"
        : "Add this origin to ALLOWED_ORIGINS. No path, no trailing slash.",
      origin: origin ?? "(none sent)",
    }, 403, origin);
  }

  const apiKey = Deno.env.get("ANTHROPIC_API_KEY");
  if (!apiKey) {
    // Never leak whether the secret exists to an unauthenticated caller in prod;
    // this message is deliberately actionable because it is a setup-time failure.
    return json({
      error: "ANTHROPIC_API_KEY is not set on this project.",
      fix: "supabase secrets set ANTHROPIC_API_KEY=sk-ant-...",
    }, 500, origin);
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return json({ error: "Body is not valid JSON. Nothing was sent to Claude." }, 400, origin);
  }

  const model = String(body.model ?? "");
  if (!ALLOWED_MODELS.has(model)) {
    return json({
      error: `Model ${model || "(none)"} is not permitted by this proxy.`,
      allowed: [...ALLOWED_MODELS],
    }, 400, origin);
  }

  const system = typeof body.system === "string" ? body.system : "";
  const messages = Array.isArray(body.messages) ? body.messages : [];
  if (messages.length === 0) {
    return json({ error: "No messages supplied." }, 400, origin);
  }

  const totalChars = messages.reduce(
    (n: number, m: { content?: unknown }) =>
      n + (typeof m.content === "string" ? m.content.length : 0),
    0,
  );
  if (system.length > MAX_SYSTEM_CHARS || totalChars > MAX_MESSAGE_CHARS) {
    return json({ error: "Request too large for this proxy." }, 413, origin);
  }

  const maxTokens = Math.min(Number(body.max_tokens ?? 1024) || 1024, MAX_TOKENS_CEILING);

  const upstream = await fetch(ANTHROPIC_API, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({ model, max_tokens: maxTokens, system, messages }),
  });

  const text = await upstream.text();
  if (!upstream.ok) {
    return json({
      error: `Anthropic returned ${upstream.status}.`,
      detail: text.slice(0, 500),
    }, upstream.status, origin);
  }

  return new Response(text, {
    status: 200,
    headers: { "Content-Type": "application/json", ...corsHeaders(origin) },
  });
});
