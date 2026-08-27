# BAi Console

A static operational console for BAi. No build step — plain HTML, CSS and JS, deployable to
GitHub Pages as-is.

**What it shows:** the twelve-agent roster (each runnable against Claude with its own binding
constraints), the exception queue with provenance and confidence, records rendering money from
minor units across five currencies, and the platform invariants and regions.

---

## The credits question, answered plainly

**A Claude Pro or Max subscription cannot authenticate a web app.** Subscriptions cover
claude.ai and Claude Code, authenticated by your login session. A hosted page needs an API key
from [console.anthropic.com](https://console.anthropic.com), which is **billed separately** as
pay-as-you-go. There is no supported bridge between the two, and anything claiming to offer one
is scraping a session token.

So the console ships with three modes, and you pick the trade-off.

| Mode | Key lives | Works on Pages | Use when |
|---|---|---|---|
| **Demo** | nowhere | ✅ | Publishing publicly, showing the interface, no spend |
| **Supabase proxy** | Supabase secrets, server-side | ✅ | **Recommended.** A real deployment others can use |
| **Direct (BYOK)** | the viewer's own browser | ✅ | Your own machine, or each user brings their own key |

---

## Deploy to GitHub Pages

```bash
git push origin main
```

Then in the repo: **Settings → Pages → Source: GitHub Actions**. The
[`deploy-console`](../../.github/workflows/deploy-console.yml) workflow publishes `apps/console/`
on every push, after a guard job that fails the build if a credential is ever committed.

Your page lands at `https://<user>.github.io/<repo>/`.

---

## Wire up the Supabase proxy (recommended)

The key never touches the browser. The static page calls an Edge Function; the Edge Function
holds the secret.

```bash
supabase functions deploy claude-proxy
supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
supabase secrets set ALLOWED_ORIGINS=https://<user>.github.io
```

Then open the console → **Settings** → **Supabase proxy**, and paste your project URL and
**anon** key. The anon key is safe in the browser — that is what it is for. The service-role key
never is, and the console never asks for it.

The proxy ([`supabase/functions/claude-proxy`](../../supabase/functions/claude-proxy/index.ts))
also enforces an allowlist of models, a max-token ceiling and request-size limits, so a page
left public cannot run up an unbounded bill.

### Optional: Supabase data

Add tables and RLS from [`supabase/migrations/`](../../supabase/migrations/) if you want the
records and queue backed by real data rather than the built-in demo set. The console reads the
Supabase REST API directly — no client library, no bundler.

---

## Bring your own key

Settings → **Direct (BYOK)** → paste an Anthropic key. It is stored in `localStorage` on that
device only and sent straight to `api.anthropic.com` using the
`anthropic-dangerous-direct-browser-access` header.

**Never deploy a page with a key baked into the source.** Anyone can open dev tools and read it.
BYOK is safe because each viewer supplies their own; it is not a way to share yours.

---

## Cost control

- Model allowlist and token ceiling in the Edge Function
- Set a monthly spend cap in the Anthropic Console — do this before publishing anything
- `claude-haiku-4-5` is the cheapest option in the model picker for routine work
