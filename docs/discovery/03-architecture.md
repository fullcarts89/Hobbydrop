# 03 — Technical architecture

Status: **proposed, awaiting founder approval.** Greenfield build: the repository held no application code, CI, or deployment configuration before this work.

Stripe facts below were read from Stripe's own pages on 2026-11-21; sources are listed at the end. Anything marked *unverified* could not be confirmed on a primary page and must be checked before it is relied on.

## 1. Decisions

| # | Decision | Chosen | Main alternative, and why not |
|---|---|---|---|
| 1 | App framework | Next.js (App Router), React, TypeScript, Tailwind, one deployable | Separate API service: a second thing to deploy and secure, with no benefit at this size |
| 2 | Hosting | Vercel | Self-hosting: operational work that validates nothing |
| 3 | Database, auth, storage | Supabase (Postgres, email one-time-code auth, Storage) | Separate vendors for each: three bills and three integrations instead of one |
| 4 | Data access | Server-only, through a typed query layer (Drizzle) inside transactions; RLS on with no client policies | Browser → Supabase directly with RLS policies: authorization rules would live in two places, and inventory / money logic must be server-side anyway |
| 5 | Payments | Stripe Connect, destination charges, Stripe-hosted Checkout, Stripe-hosted seller onboarding | See section 4 |
| 6 | Background work | None as infrastructure: derived drop status, lazy reservation expiry, a Postgres outbox, and one scheduled sweep | A job queue: nothing in the MVP needs one once statuses are derived from timestamps |
| 7 | Email | Resend, for both transactional mail and Supabase Auth's SMTP | Supabase's built-in sender is rate-limited to a level unusable beyond development |
| 8 | Analytics | First-party `events` table written server-side | PostHog: a good tool, but the funnel that matters here joins to orders, which is one SQL query away in our own database. Add it later if session replay is wanted |
| 9 | Errors | Sentry | — |
| 10 | Buyer accounts | None in MVP; guests get a tokenized order link by email | Buyer sign-in: a second auth journey that no validation question depends on |
| 11 | PWA | Web manifest and icons only; no service worker or offline mode | Offline support adds cache-invalidation risk to a checkout flow for no validation value |

### Constraints found during discovery

- **`/@seller/drop-name` URLs.** A folder beginning with `@` is reserved syntax in the Next.js App Router (parallel routes). The public URL stays `/@seller/drop-name`; a rewrite maps it to an internal `/u/[username]/[slug]` route.
- **Sign-in links.** Corporate and webmail scanners pre-open links in email, which burns single-use magic links. Sign-in uses a six-digit emailed code instead.
- **Stripe Checkout's minimum session lifetime is 30 minutes** [S25]. Stock held for a checkout is therefore held for up to 30 minutes unless we expire the session ourselves. See 4.4.
- **Vercel's free tier is for non-commercial use and Supabase's free tier pauses idle projects and has no backups.** Both are fine for development; the real-money pilot needs the paid tiers (roughly $45/month combined at list price — *confirm current pricing before committing*; this is a founder approval item).
- **Photos carry GPS coordinates.** Sellers photograph gear at home. All uploads are re-encoded server-side, which strips EXIF, before anything is publicly reachable.

## 2. Structure

```
src/
  app/                      routes only — thin; parse input, call a service, render
    (marketing)/            landing, policies
    u/[username]/           seller profile            (public: /@username)
    u/[username]/[slug]/    drop storefront + item    (public: /@username/drop-slug)
    checkout/               cart review → redirect to Stripe; return page
    orders/[token]/         guest order page
    dashboard/              seller: drops, items, orders, payout setup
    admin/                  role-gated
    api/webhooks/stripe/    signature-verified webhook
    api/cron/sweep/         scheduled tidy-up + reconciliation
  server/                   business logic — no React, no request objects
    auth/                   session lookup; guards: requireUser, requireSellerOf, requireAdmin
    drops/  items/  images/
    inventory/              reserve, consume, release  (the only code that touches stock)
    checkout/  orders/  payments/  fulfillment/
    notifications/          outbox + templates
    admin/  analytics/
    db/                     schema, migrations, client
  components/               ui primitives (Radix-based) and feature components
  lib/                      money, slugs, zod schemas shared by forms and services
```

Rules that keep this honest:

- Route handlers and server actions never query the database directly; they call a function in `server/`, and every such function starts with a guard.
- All input crosses a zod schema at the boundary. All money is integer cents and goes through `lib/money`.
- `server/inventory` is the only module allowed to write `quantity_sold` or `inventory_reservations`.

## 3. Key flows

### 3.1 Images

1. Browser downsizes the photo (longest edge ≤ 2400 px) before upload, so a phone on mobile data is not sending 12 MB originals.
2. Browser uploads to a **private** bucket using a short-lived signed upload URL issued by the server for a server-generated key.
3. Server finalizes: checks size and real file type from the bytes (JPEG, PNG, WebP, HEIC only), decodes and re-encodes with `sharp` into two WebP derivatives (grid and detail), strips metadata, writes them to the **public** bucket, records `item_images`, deletes the original.
4. Storefront serves the derivatives directly from storage's CDN with `srcset`; no per-request image transformation, so no dependency on paid transform quotas.

Limits: 8 images per item, 10 MB per upload, 40 items per drop.

### 3.2 Publishing

A drop can be drafted, filled and previewed with no payout account. **Publish** is refused server-side unless the seller's Stripe account can receive transfers — a destination charge fails otherwise [S21] — and the drop has at least one active item with an image. Publishing fixes the slug and sets `starts_at` (now, or the scheduled time). "Scheduled", "live" and "ended" are computed from the clock on every read.

### 3.3 Sharing

- `generateMetadata` plus a dynamically rendered Open Graph image per drop (cover photo, title, seller, item count), cached and regenerated when the drop changes.
- Copy-link and the Web Share API on mobile.
- `utm_*`, `ref` and the referrer's hostname are captured on first visit into a first-party cookie, written to `events`, and carried onto the checkout and the order, so each order can be traced to the community it came from. This is the measurement the whole thesis depends on.

### 3.4 Checkout

```
Buyer taps Checkout
  → server: reserve stock (one transaction; see 04-data-model.md)
  → server: create Stripe Checkout Session (destination charge, 30-minute expiry)
  → redirect to Stripe
       ├─ pays      → webhook checkout.session.completed → consume reservation, create order, queue emails
       ├─ abandons  → session expires → webhook checkout.session.expired → release
       └─ cancels   → return URL → server expires the session → release immediately
```

The return page never creates the order; only the verified webhook does. The return page polls for the order and shows "confirming payment" until it exists.

### 3.5 Webhook handling

- Verify the signature against the raw body; reject anything else [S28].
- In one transaction: insert the event id into `stripe_events` (`on conflict do nothing`); if it was already there, return 200 and stop. Otherwise apply the state change and write outbox rows, then commit.
- Handlers are written to tolerate out-of-order delivery (Stripe does not guarantee order [S28]): each one reads current state and moves it forward, never assumes the previous event arrived.
- Events handled: `checkout.session.completed`, `checkout.session.expired`, `charge.refunded`, `charge.dispute.created` / `.closed`, `account.updated`, `payout.failed`. Card and wallet payments only, so there are no delayed-notification payment methods to handle in the MVP.
- Outbound Stripe calls that create things (sessions, refunds, payouts) carry an idempotency key derived from our own row id.

### 3.6 The scheduled sweep

One endpoint, called by Vercel Cron, authenticated with a secret, safe to run twice:

- mark long-expired reservations and checkouts as released / expired;
- retry unsent outbox emails;
- release seller payouts that have passed their hold (4.3);
- send ship-by reminders and flag overdue orders for admin;
- reconcile: any Stripe session completed in the last day without a matching order raises an alert.

## 4. Payments

### 4.1 Configuration

| Choice | Value | Reason |
|---|---|---|
| Seller account | Connected account that only *receives transfers*, with the Express dashboard and Stripe-hosted onboarding | Stripe's own recommendation for marketplaces [S7][S8]. Sellers never get a card-processing account, which keeps their onboarding to name, date of birth, last four of SSN, and a bank account at pilot volumes [S18] |
| API generation | Accounts v2 (`recipient` configuration) if nothing we need is missing; otherwise v1 with controller properties | Stripe now labels Standard / Express / Custom as legacy [S3], but some v2 examples still use preview API versions [S8]. Decide in the first payments spike, not on paper |
| Charge type | **Destination charge** with `application_fee_amount` | Stripe's stated fit for "one seller per payment, platform-owned checkout" [S10][S11] |
| Checkout UI | Stripe-hosted Checkout, guest mode, shipping address collected by Stripe | No card data touches us; guest checkout and address collection come for free [S25] |
| Payment methods | Cards and wallets (Apple Pay, Google Pay) | Instant confirmation only; no bank debits that settle days later |
| Merchant of record | HobbyDrop (no `on_behalf_of`) | `on_behalf_of` requires sellers to hold card-payment capability, which means heavier onboarding, and does not move dispute liability off the platform anyway [S11][S12]. **Needs legal confirmation** — see section 8 |

### 4.2 What this means for liability

With destination charges the charge sits on HobbyDrop's Stripe account. **Refunds and chargebacks are debited from HobbyDrop**, which then recovers from the seller by reversing the transfer, if the seller still has a balance [S10][S12]. Stripe states the platform is "ultimately liable for chargebacks and related costs" [S12]. A dispute costs $15 when received and a further $15 if contested, the second fee returned only on a win [S2].

This is the single most important financial fact about the product: on a $110 order, one lost chargeback costs roughly $125–$140, the net margin of 30 or more orders. It is why 4.3 exists.

### 4.3 Payout timing

Sellers' funds land in their Stripe balance at purchase but are **not paid out to their bank automatically**. Their account is set to manual payouts [S6], and the sweep releases each order's funds once the order has tracking and a short hold has passed (proposed: 3 days after the seller enters tracking). Until then a refund for non-shipment is a clean transfer reversal against money that is still there.

Words matter here: Stripe does not offer escrow and lists escrow services as a restricted business [S6][S17]. This is a *delayed payout*, and seller-facing copy must call it that.

### 4.4 Stock holds and the 30-minute floor

A buyer who opens Stripe Checkout and walks away holds the item for up to 30 minutes. For one-of-a-kind used gear in a busy drop that is a real cost, and a hostile visitor could hold many items. MVP controls:

- cancel returns release stock instantly;
- one open checkout per browser, and a low per-IP rate limit on starting one;
- the storefront shows a held item as "In someone's cart — may return at 3:42 PM" rather than "Sold", so interested buyers come back.

If pilot data shows holds costing sales, the next step is to expire idle sessions ourselves after about ten minutes through Stripe's expire endpoint, which Stripe supports for exactly this [S26]. Not built until it is shown to matter.

### 4.5 Fees and unit economics

Stripe's costs under this configuration [S1][S2]:

| Cost | Rate | Paid by |
|---|---|---|
| Card processing | 2.9% + $0.30 of the total charged | Debited from HobbyDrop |
| Active connected account | $2.00 per account per month in which it receives a payout | HobbyDrop |
| Payout | 0.25% + $0.25 per payout | HobbyDrop |
| Dispute | $15 received + $15 if contested | HobbyDrop |

Worked example — $100 item, $10 shipping, buyer pays $110:

| | HobbyDrop absorbs processing | Seller bears processing |
|---|---:|---:|
| Fee taken from the seller | $4.00 | $7.49 |
| Seller receives | $106.00 | $102.51 |
| Stripe processing | −$3.49 | −$3.49 |
| Payout fee | −$0.52 | −$0.51 |
| **HobbyDrop net** | **−$0.01** | **+$3.49** |
| …if this is the seller's only payout that month (−$2.00) | −$2.01 | +$1.49 |

Conclusions:

1. **"4% with processing separately disclosed" must mean the seller pays processing.** Absorbing it makes every order a loss.
2. The seller's all-in cost is then about **6.8% + $0.30** on this order, and that is the number to put in front of sellers — as one line, with the breakdown underneath.
3. The $2 monthly account fee hits hardest on exactly the casual seller the PRD targets (one small drop, one payout). Batching each seller's payouts weekly limits payout fees but not the $2.
4. Small orders are unprofitable: on a $15 item the fixed costs exceed the fee. A minimum item price or minimum order value is worth considering once real basket sizes are known.

Fee calculation lives in one pure, exhaustively unit-tested function. The fee rate is stored on each checkout and order.

### 4.6 Alternatives considered

- **Separate charges and transfers** — same liability, more moving parts; Stripe advises it only when the use case needs it [S10] (multi-seller carts). Revisit if those are ever built.
- **Direct charges** — puts refunds and disputes on the seller, but requires every seller to hold a full card-processing account and makes the seller the merchant of record on a checkout page we own. Wrong fit for casual individuals.
- **PayPal multiparty** — requires partner approval, no published platform rates, higher base rate (3.49% + $0.49) [S29][S30].
- **No platform payments** (each seller pastes their own payment link) — zero liability and zero payment engineering, but also no fee, no stock locking tied to payment, and no buyer protection. It is the right answer only for a pre-product smoke test; see 05.

## 5. Security

| Risk | Control |
|---|---|
| Broken access control | Every service function begins with a guard; RLS denies all direct client access; automated tests attempt cross-seller reads and writes on every mutating endpoint |
| Privilege escalation to admin | Role is a database row checked server-side on every admin request; no role in client-editable user metadata; every admin action written to an append-only log with a required reason |
| Overselling / double charge | Row locks, a database check constraint, unique `checkout_id` on orders, event dedupe table, idempotency keys on outbound Stripe calls |
| Forged webhooks | Signature verification on the raw body; unverified requests rejected before any parsing |
| XSS | React escaping; no raw HTML rendering of seller text; seller links restricted to `https:`; a content security policy |
| CSRF | Mutations via server actions (origin-checked) with `SameSite=Lax` cookies; no state changes on GET |
| Injection | Parameterized queries only, through the query layer |
| Upload abuse | Server-chosen keys, type sniffed from bytes, size and count limits, mandatory re-encode, originals never public |
| Guest order links | 256-bit random token, stored hashed, compared in constant time; pages marked `noindex` and `Referrer-Policy: no-referrer` |
| Address exposure | Sellers see a buyer address only for their own orders; redacted on a schedule; never logged |
| Abuse and scraping | Vercel firewall rate limits on sign-in, checkout start, report and upload-URL endpoints; Supabase Auth's own limits on code requests |
| Secrets | Vercel environment variables per environment; service-role key and Stripe secret only in server code; a build-time check that no server-only variable is referenced from client bundles |
| Sensitive logging | Structured logs with an allow-list of fields; emails and addresses excluded |

## 6. Testing

| Layer | Tool | Must cover |
|---|---|---|
| Unit | Vitest | Fee and shipping math (including rounding edges), drop state derivation, slug and username rules, validation schemas |
| Integration | Vitest against real local Postgres (Supabase CLI) | Reserve / consume / release; **concurrency: N parallel buyers for one unit — exactly one succeeds**; seller edits mid-checkout; every guard, with a wrong-user case |
| Webhook | Recorded Stripe event fixtures, signed with a test secret | Each handled event; duplicate delivery; out-of-order delivery; payment after reservation expiry → automatic refund |
| End to end | Playwright, mobile and desktop viewports | Seller: sign in → create drop → add items with photos → publish. Buyer: open link → cart → checkout start → (webhook simulated) → order page. Seller: mark shipped. Refund path |
| Manual, per milestone | Stripe test mode with the Stripe CLI | Real hosted Checkout and hosted onboarding, which Stripe advises against automating |

CI (GitHub Actions) on every push: typecheck, lint, unit, integration against a Postgres service container, build. End-to-end on pull requests. Nothing is reported as working on the strength of a successful compile.

## 7. Environments and deployment

| Environment | App | Database | Stripe |
|---|---|---|---|
| Local | `next dev` | Supabase CLI (Docker) | Test mode + Stripe CLI webhook forwarding |
| Preview | Vercel preview per pull request | Shared staging Supabase project | Test mode |
| Production | Vercel production | Production Supabase project with daily backups | Test mode until the founder activates live mode |

Migrations are plain SQL files in the repository, applied by CI to staging on merge and to production by an explicit, manually triggered job. Migrations are written to be backward-compatible with the previously deployed code (add, backfill, switch, then remove).

**Founder-gated steps:** creating the Stripe platform account and completing its marketplace profile; creating the paid Vercel and Supabase projects; pointing a domain; flipping Stripe to live mode.

## 8. Before real money moves — needs a lawyer or accountant

These are not engineering decisions and I have not treated them as settled.

1. **Merchant-of-record status** and consumer-law liability for goods HobbyDrop never handles.
2. **Money-transmission exposure** of delayed payouts, and the wording used to describe them.
3. **Sales tax.** In the 45 states with a sales tax, a marketplace facilitator must collect and remit once past each state's economic nexus threshold — typically $100,000 of sales or 200 transactions into the state, counting the platform's total volume [S23]. A pilot under $15k GMV is far below those, but the founder's home state is the exception: physical presence can create nexus from the first sale. Confirm registration and facilitator status there. The schema carries `tax_cents` from day one; Stripe Tax supports Connect when it is needed [S24].
4. **1099-K.** Where the platform sets pricing, the platform is the filer [S22]. The federal threshold is back to more than $20,000 *and* more than 200 transactions per seller per year [S13][S14]; some states are lower (*unverified*).
5. **Terms**: seller agreement (including chargeback recovery and delayed payout), buyer terms, privacy policy, prohibited-items policy, refund and dispute procedure.
6. **Category rules.** Stripe prohibits counterfeit goods and restricts weapons, including "other weapons" such as swords and machetes [S17]. Whether knives or airsoft fall inside that is *unverified*; exclude them from the pilot rather than find out.

## Sources

- S1 https://stripe.com/connect/pricing
- S2 https://stripe.com/pricing
- S3 https://docs.stripe.com/connect/accounts
- S6 https://docs.stripe.com/connect/manual-payouts
- S7 https://docs.stripe.com/connect/marketplace
- S8 https://docs.stripe.com/connect/marketplace/tasks/onboard
- S10 https://docs.stripe.com/connect/charges
- S11 https://docs.stripe.com/connect/destination-charges
- S12 https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes
- S13 https://support.stripe.com/questions/1099-k-tax-forms-for-platforms-and-marketplaces
- S14 https://www.irs.gov/businesses/understanding-your-form-1099-k
- S17 https://stripe.com/legal/restricted-businesses
- S18 https://docs.stripe.com/connect/required-verification-information
- S21 https://docs.stripe.com/connect/account-capabilities (read from a search excerpt, not the full page)
- S22 https://support.stripe.com/questions/1099-forms-for-platforms-and-marketplaces (search excerpt)
- S23 https://stripe.com/resources/more/marketplace-facilitator-laws
- S24 https://docs.stripe.com/tax/connect (search excerpt)
- S25 https://docs.stripe.com/api/checkout/sessions/create
- S26 https://docs.stripe.com/payments/checkout/managing-limited-inventory (search excerpt)
- S28 https://docs.stripe.com/webhooks
- S29 https://developer.paypal.com/docs/multiparty/ (search excerpt)
- S30 https://www.paypal.com/us/business/paypal-business-fees
