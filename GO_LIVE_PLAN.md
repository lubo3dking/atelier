# Atelier — Go-Live Plan (step by step)

Your action plan to take Atelier from a working CLI to **live, sendable, sellable, and working**.

**Legend:** 👤 = *you do this* (decision / account / money — I can't do these for you) · 🤖 = *ask me to build this* · ⏱ = rough time · 💶 = rough cost

**Where we are now (updated 2026-06-14):** the **web app is built and verified live** — a browser page that takes a photo + notes, runs the pipeline, and returns a PDF/CSV tech pack in EN/BG. **Sending (email), payments (Stripe), privacy/consent, and deploy config are all built** and switch on from environment variables. What's left is mostly **yours to do**: make the product decisions, then create the accounts (domain, host, Stripe, Resend) and flip the switches. Run it now with `./.venv/bin/python scripts/serve.py`.

> 🤖→✅ The build items below marked **DONE** are already implemented. The 👤 items (accounts, money, domain, keys) are still yours.

**The 4 goals, defined:**
- **Working** = anyone can run it reliably from a browser, no terminal.
- **Sendable** = the finished tech pack can be emailed/shared to a sewer in one click.
- **Live** = it's on the internet at your own domain.
- **Sellable** = customers pay (subscription or per–tech-pack) before/after generating.

---

## TOMORROW (Day 1) — get a working web app + make your key decisions

Goal for the day: a browser page where you upload a photo, add notes, pick sizes/language, and download the tech pack — running on your machine. Plus the decisions everything else depends on.

### Morning — decisions (👤 ~45 min)
Write down answers to these. They unblock everything after.
- [ ] **Name & domain.** Keep "Atelier" or pick another. Check the `.com`/`.eu` is free (you'll buy it on Day 3).
- [ ] **Who's the customer?** Independent fashion brand owners / small labels? Decide the primary one.
- [x] **Pricing model — decided: freemium unlock.** Everyone gets **3 free tech packs**, then a **one-time payment unlocks unlimited** use forever (pay once, then free). Built in. You just set the free count (`ATELIER_FREE_PACKS`) and the one-time price (`ATELIER_UNLOCK_CENTS`, default €29). 👤 Decide the exact number + price.
- [ ] **Languages at launch:** EN only, or EN + BG? (Both already work.)
- [ ] **Garments at launch:** the engine covers tops, dresses, trousers, skirts. List the ones you'll advertise.

### Afternoon — first working web app (🤖→✅ **DONE**, 👤 you test)
- [x] 🤖→✅ FastAPI backend + web upload page that runs the pipeline — **built** (`src/web/`).
- [ ] 👤 Run it locally: `./.venv/bin/python scripts/serve.py` → open http://localhost:8000, generate a tech pack from the browser. ⏱ 15 min
- [ ] 👤 Try 2–3 real garment photos; note anything that looks wrong → tell me, I fix.

**End of Day 1 you have:** a working local web app (✅ already running) and a clear product definition. 💶 €0.

> ✅ **Speed:** a tech pack generates in **~30 seconds** (one Claude call). The app polls and shows a spinner while it works.

---

## Day 2 — Sending + privacy foundation (required before anyone else uses it)

### Sending the tech pack (🤖→✅ **DONE**, 👤 one decision + account)
- [x] 🤖→✅ Download buttons (PDF + POM CSV) and an **"email this tech pack to my sewer"** option — **built**. Email auto-enables when `RESEND_API_KEY` is set; otherwise the app is download-only.
- [ ] 👤 Decide the send method: **download only** (works now, €0), or also **email to the sewer**.
- [ ] If emailing: 👤 create a free **Resend** account (resend.com), verify a sender domain, and put `RESEND_API_KEY` + `ATELIER_EMAIL_FROM` in your host's secrets. 💶 free tier. *(Alternative: Postmark — would need a small code change.)*

### Privacy / consent (NON-NEGOTIABLE — you handle photos of people's designs/bodies)
- [x] 🤖→✅ Consent checkbox before upload, **auto-delete of uploaded photos** (right after generation) + retention auto-delete of packs, and a **"delete my data"** action — **built**. Placeholder `privacy.html` / `terms.html` pages are included.
- [ ] 👤 Get a **real privacy policy + terms** to replace the placeholders. Easiest: a generator like **Termly** or **iubenda** (free/low tier), or a lawyer if budget allows. Must state: what you collect (photos, notes), that **Anthropic processes images**, retention period, and deletion rights. 💶 €0–20/mo
- [ ] 👤 Decide the retention window and set `ATELIER_RETENTION_DAYS` (default 14).

**End of Day 2:** the app can deliver tech packs to sewers and is privacy-safe to show people. Still local. 💶 ~€0–20.

---

## Day 3 — Go live (on the internet at your domain)

- [ ] 👤 **Buy a domain** (Namecheap or Cloudflare Registrar). 💶 ~€10–15/yr
- [ ] 👤 **Create a hosting account.** *Recommendation: Railway* (railway.app) — easiest for a Python app + Redis. *(Alternatives: Render, Fly.io.)* 💶 ~€5–20/mo
- [ ] 👤 Put your `ANTHROPIC_API_KEY` into the host's **secret/environment settings** (never in code). I'll show you exactly where.
- [x] 🤖→✅ Deploy config prepared: `Dockerfile` (bundles Bulgarian fonts), `railway.json`, `render.yaml`. You click deploy/authorize in your account; set `ANTHROPIC_API_KEY` + `ATELIER_PUBLIC_URL=https://your-domain` in the host's secrets.
- [ ] 👤 Add **API spend limits** in the Anthropic console so costs can't run away.

**End of Day 3:** Atelier is **live** at your domain, generating real tech packs. 💶 ~€15–35 one-time + monthly.

---

## Day 4 — Make it sellable (payments)

- [ ] 👤 **Create a Stripe account** (stripe.com), verify your identity/business, add your bank for payouts. 👤 *(I cannot do this — it's your money and identity.)* 💶 Stripe takes ~2.9% + €0.30/transaction; no monthly fee.
- [x] 🤖→✅ **Stripe Checkout integration — built (freemium unlock).** Everyone gets `ATELIER_FREE_PACKS` free packs; after that, one payment (`ATELIER_UNLOCK_CENTS` / `ATELIER_CURRENCY`) unlocks unlimited use for that device. Auto-enables when `STRIPE_SECRET_KEY` is set; until then the app is free & unlimited. *(MVP verifies the Checkout session server-side rather than via webhook — simpler and accountless. Webhooks + real accounts come with the multi-tenant step later; until then "unlimited" is tracked per device/browser, which is fine for launch.)*
- [ ] 👤 In Stripe: create the account, connect a bank, set `STRIPE_SECRET_KEY` in your host's secrets, and set your free count + unlock price via `ATELIER_FREE_PACKS` / `ATELIER_UNLOCK_CENTS`.
- [ ] 👤 Test a real purchase with Stripe **test mode**, then a €1 live test, then refund yourself.
- [ ] 👤 Decide free trial / first-pack-free to lower the barrier (optional).

**End of Day 4:** Atelier is **sellable** — customers pay and get their tech pack. 💶 transaction fees only.

---

## Day 5 — Test with real users + launch

- [ ] 👤 Send the live link to **1 real sewing workshop**: have them produce (or quote) a garment from an Atelier tech pack. This is the real test of "working." Capture their feedback.
- [ ] 👤 Run **3–5 real brand-owner scenarios** end to end (upload → pay → download → send to sewer).
- [ ] 🤖 Tell me what broke or read poorly → I fix.
- [ ] 👤 Soft-launch: share with a small audience (your network, a niche community). Don't mass-market yet.

**End of Day 5:** validated, working, sellable product with first real users. 🎉

---

## Decisions cheat-sheet (fill these in)

| Decision | Your answer |
|---|---|
| Product name / domain | |
| Primary customer | |
| Pricing model & price | |
| Languages at launch | |
| Garments advertised | |
| Send method (download / email) | |
| Photo retention window | |
| Hosting platform | |

---

## Accounts you'll need (all created by 👤 you)

| Service | Purpose | Rough cost | When |
|---|---|---|---|
| Anthropic Console | Claude API (already have key) | pay-as-you-go (cents/pack) | done |
| Domain registrar (Namecheap/Cloudflare) | your web address | ~€10–15/yr | Day 3 |
| Hosting (Railway/Render/Fly) | run the app online | ~€5–20/mo | Day 3 |
| Resend (or Postmark) | email tech packs | free tier | Day 2 |
| Privacy generator (Termly/iubenda) | privacy policy + terms | €0–20/mo | Day 2 |
| Stripe | take payments | ~2.9% + €0.30/txn | Day 4 |

**Things only you can legally/financially do** (I'll guide, but you must perform them): buying the domain, creating accounts, entering the API key into the host, setting up Stripe + bank payouts, accepting any terms, and any live payment test.

---

## What "done" looks like

- **Working** ✅ a non-technical person generates a correct tech pack from a browser.
- **Sendable** ✅ one click downloads or emails the PDF to a sewer.
- **Live** ✅ reachable at your domain over HTTPS.
- **Sellable** ✅ a customer pays via Stripe and receives their tech pack.

---

## Important notes & risks (read before Day 1)

- **Realistic pace:** the 5 "days" are *work sessions*, not necessarily 5 calendar days — account verification (Stripe especially) can take 1–2 days. Don't block launch on me; block it on your accounts being ready.
- **Cost control:** set an Anthropic spend cap on Day 3. Each tech pack makes **one** Claude call (a few cents). Build a little headroom into your unlock price.
- **Privacy first:** do **not** put the public link in front of anyone until the consent + deletion step (Day 2) is done — you'll be handling other people's design IP and possibly photos of people.
- **Start narrow:** launch the few garments the flat engine renders well (tops, dresses, trousers, skirts). Add blazers/hoodies/outerwear later — just ask me.
- **Keep the API key secret:** only ever in `.env` locally and the host's secret settings. Never in the repo, the frontend, or a chat.

---

## The single most important thing to do first

👤 **Make the Day-1 decisions** (name, customer, price), then 🤖 **ask me to build the FastAPI backend + web upload page.** Everything else builds on those two.
