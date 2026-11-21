# 02 — Recommended MVP scope

Status: **proposed, awaiting founder approval.**

## What the MVP has to prove

Four questions, in order. Each later one is pointless if an earlier one fails.

1. Will a hobbyist put a real collection into a drop **without help**?
2. Will they **post the link** in their own community, and will that community allow it?
3. Will strangers from that community **pay through an unfamiliar checkout**?
4. Will the seller **do it again**?

Everything below is in scope only if it is needed to get a clean answer to one of these.

## In scope

### Seller

| Capability | Notes |
|---|---|
| Sign in with an emailed six-digit code | No passwords, no social login |
| Profile: username, display name, photo, bio, links to community profiles | The links are the seller's borrowed reputation; show them prominently |
| Create a drop: title, description, category (fixed to the launch niche), optional end date | |
| Add items: photos (up to 8), title, condition, price, quantity (default 1), optional description | Built for speed on a phone: add photos first, then fill a compact row per item |
| Shipping: one flat rule per drop — "$X for the first item, $Y each additional", US only | Covers combined shipping, which is the point of buying several things from one seller |
| Save as draft, preview exactly as buyers will see it | |
| Connect payouts through Stripe-hosted onboarding | Required before publish, not before drafting |
| Publish now or schedule a start time | "Scheduled / live / ended" derived from the clock |
| Share: copy link, native share sheet, rich link preview image | |
| Orders: list, buyer address, mark shipped with carrier and tracking, cancel-and-refund | |
| Email on each new order; reminder when a ship-by date approaches | |

### Buyer

| Capability | Notes |
|---|---|
| Open a drop with no account | |
| Item grid, item detail with photo gallery, condition, price, availability | "Sold" items stay visible, greyed — a half-sold drop is social proof |
| Cart for several items from the one drop | Client-side; nothing reserved until checkout |
| Guest checkout on Stripe-hosted Checkout: card, Apple Pay, Google Pay | Item total, shipping and order total shown before redirect |
| Order page from a private link in the confirmation email: status, tracking, "report a problem" | |
| Ask the seller a question before buying | A form that emails the seller with the buyer's address as reply-to. Not in-app messaging |
| Report a listing | |

### Platform

| Capability | Notes |
|---|---|
| Stock reservation at checkout; no overselling under concurrency | See [04-data-model.md](04-data-model.md) |
| Fee calculation, delayed seller payout, refunds, dispute recording | See [03-architecture.md](03-architecture.md) section 4 |
| Transactional email: order confirmation, new order, shipped, refunded, payout-account problem | |
| Funnel events with traffic source carried through to the order | |
| Admin: read-only lists of users, drops, orders and reports; suspend a drop or user; issue a refund; audit log | Deliberately thin — see below |
| Policies page: prohibited items, refunds and disputes, privacy, terms | Text supplied or approved by the founder and counsel |

## Cut or reduced from the PRD's P0, with reasons

| PRD P0 item | Recommendation | Why |
|---|---|---|
| Buyer accounts | **Cut.** Guests only, with tokenized order links | No validation question depends on buyers signing in. Halves the auth surface |
| Background job system | **Cut.** Derived statuses, lazy expiry, outbox, one scheduled sweep | Nothing needs a queue once drop status is computed from timestamps |
| Full admin interface (payment review, fulfillment investigation, user restriction management) | **Reduced** to lists, suspend, refund, audit log | At 50–100 orders the Stripe and Supabase dashboards do the rest. Build admin tooling in response to real incidents |
| PWA | **Reduced** to a manifest and icons | Offline caching adds risk to checkout and proves nothing |
| "Campaign attribution, referral tracking, seller-specific share links" | **Reduced** to capturing `utm_*`, `ref` and referrer on visit and carrying them to the order | Same insight, a fraction of the surface |
| Account deletion workflow | **Reduced** to a "delete my account" request that an admin processes with a tested anonymization routine | Correct handling of financial-record retention matters more than self-service |
| Privacy settings | **Cut.** There is nothing to configure yet | The profile is public by design; everything else is private by default |
| Item-level category and shipping attributes | **Cut.** | One niche, one flat shipping rule per drop |
| Product analytics vendor | **Deferred.** First-party events table | The funnel that matters joins to orders in our own database |
| Shipping-rate calculation | **Cut.** Seller-set flat rule | Carrier-rate integration is P1 at the earliest, alongside labels |
| Partial refunds from the seller UI | **Deferred.** Full refund only for sellers; partials by admin through Stripe | Rare at pilot scale; meaningful UI and accounting complexity |
| Sales tax collection | **Not built; schema-ready.** | Below every economic-nexus threshold at pilot volume; home-state position to be confirmed by counsel |

## Added — missing from the PRD but required

| Addition | Why |
|---|---|
| **Delayed seller payout until tracking is entered** | The platform is liable for every chargeback and refund. Paying sellers out before they ship converts each no-show into a direct loss |
| **Ship-by deadline with reminder and admin-triggered refund** | Without one, "item not received" has no defined point at which the buyer is made whole |
| **Seller cancel-and-refund** | Used gear gets dropped, lost, or sold elsewhere. There has to be a clean way out that restores stock or marks it gone |
| **Pre-purchase question to the seller** | Buyers of used gear ask about specifics before paying. Without a route they bounce, or take the deal off-platform |
| **A written buyer-protection statement** | The PRD asks for dispute procedures; buyers need the short version on the checkout path: what happens if it does not arrive or is not as described |
| **Item price cap for the pilot** (proposed $1,500) | Caps the worst-case loss from a single fraudulent order while the dispute process is untested |
| **EXIF stripping on photos** | Phone photos embed the seller's home coordinates |
| **Total seller cost shown as one number** | "4%" plus processing is about 6.8% + $0.30. Showing only "4%" would be the ambiguous fee presentation the PRD forbids |

## Explicitly out

Follow and drop alerts, reviews and ratings, search, cross-seller browsing or discovery, offers and negotiation, bundles and discount codes, shipping labels, international shipping, local pickup, AI-assisted listing, multi-seller carts, auctions, live selling, seller subscriptions, native apps.

Two of these deserve a note because they will be tempting early:

- **AI-assisted listing** is the most plausible accelerator of "five items in five minutes", and it is cheap to add later behind the existing item form. It stays out until sessions with real sellers show where creation time actually goes.
- **Follow / notify me** is the natural answer to question 4 (repeat sellers need a way to bring buyers back). If pilot sellers ask for it unprompted, it is first in line after the MVP.

## Critical screens

All sixteen screens in the PRD's section 11.4 remain, with three changes: sign-in and seller onboarding collapse into one short flow; "buyer order details" is the tokenized guest page; and the admin interface is a handful of tables. Design target is a phone held in one hand; every seller workflow must be completable there.

## Definition of done for the MVP

- A seller who has never seen the product publishes a five-item drop from a phone in under five minutes, measured with real pilot sellers, not by us.
- A full purchase works end to end in Stripe test mode: reserve, pay, order, emails, ship, delayed payout, refund.
- The concurrency test (many buyers, one unit) passes in CI on every commit.
- The security review in [03-architecture.md](03-architecture.md) section 5 has been executed, not just written.
- The legal items in 03 section 8 are resolved before live mode — a founder gate, not an engineering one.
