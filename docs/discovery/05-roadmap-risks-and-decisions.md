# 05 — Roadmap, risks, and founder decisions

Status: **awaiting founder approval. No application code is written until the decisions in section 4 are made.**

## 1. Build roadmap

Effort is in focused engineering days for one senior engineer. With Claude Code doing the implementation, elapsed time will be set less by coding than by founder review, account approvals (Stripe in particular), and legal sign-off. Treat the numbers as planning estimates with real uncertainty, not commitments.

| # | Milestone | Contents | Depends on | Effort | Exit test |
|---|---|---|---|---:|---|
| V | **Validation groundwork** *(founder, runs in parallel from day one)* | Ask moderators of 3–5 target communities whether an external checkout link is allowed; 15–20 seller interviews; open the Stripe platform account; engage counsel | — | — | A written yes from at least two communities; interview notes |
| 1 | Foundation | Project scaffold, CI, local database, first migration, sign-in by emailed code, profile, design tokens and base components | Approval of this document | 3–4 | CI green; a user can sign in and create a profile; cross-user access tests pass |
| 2 | Drop creation | Drops, items, photo pipeline, drafts, preview, seller dashboard | 1 | 6–8 | A five-item drop created from a phone-sized viewport in an end-to-end test; uploads rejected for wrong type and size; EXIF confirmed stripped |
| 3 | Storefront and sharing | Public drop page, item detail, seller profile, link preview image, share actions, client-side cart, visit and attribution events, ask-the-seller form | 2 | 4–5 | **PRD Phase 1 exit:** a published drop is publicly reachable at its stable URL with a correct link preview; funnel events recorded with source |
| ◆ | **Checkpoint: share test** | Put 5–10 real drops from interviewees in front of real communities, with purchase handled by "message the seller". Measures creation effort, whether the link is tolerated, and click-through — before any payment engineering | 3, V | — | Founder decides whether to proceed to payments |
| 4 | Payments spike | Stripe account configuration (new or legacy API), hosted onboarding, one destination charge and one refund in test mode | Stripe platform account | 2 | A test seller onboarded and paid; the account-API choice recorded |
| 5 | Commerce | Stock reservation, checkout, webhook processing, orders, payout gating on publish, refunds, transactional email | 3, 4 | 8–10 | **PRD Phase 2 exit:** a complete purchase in test mode; concurrency test passes (many buyers, one unit, exactly one order); duplicate and out-of-order webhooks handled; payment-after-expiry auto-refunds |
| 6 | Fulfillment and operations | Seller order management, tracking, ship-by reminders, delayed payout release, guest order page, reporting, admin lists, suspend, audit log | 5 | 5–6 | **PRD Phase 3 exit:** an order goes purchase → shipped → payout released, and separately purchase → refund, with every state change in the audit trail |
| 7 | Hardening | Accessibility pass, mobile performance, security review executed against the checklist, failure-path testing, analytics verification, full end-to-end suite | 6 | 5–6 | **PRD Phase 4 exit:** review findings closed or explicitly accepted; Core Web Vitals measured on a mid-range phone profile |
| 8 | Controlled pilot | 10–20 sellers in one niche, live payments | 7, legal sign-off, founder go-live approval | founder-led | PRD Stage 2 and 3 gates |

**Total engineering: about 33–41 days**, roughly seven to eight working weeks.

### Fit with 90 days

| Weeks | Activity |
|---|---|
| 1–2 | Validation groundwork (founder) alongside milestones 1–2 |
| 3 | Milestone 3; share test begins |
| 4–6 | Milestones 4–5 |
| 7–8 | Milestone 6 |
| 9 | Milestone 7; legal sign-off; go-live decision |
| 10–13 | Pilot |

This reaches first real-money transactions and an early read on sharing and conversion inside 90 days. It probably does **not** reach the PRD's Stage 3 target of 50–100 completed orders in that window: four pilot weeks with 10–20 casual sellers is thin. Plan for the pilot to run past day 90 before judging the Stage 3 and Stage 4 gates.

### Dependency map

```
profile ─► drops ─► items ─► images ─► storefront ─► cart ─┐
                                          │                 ├─► checkout ─► orders ─► fulfillment ─► payout release
                              share + attribution           │        │          │
seller payout onboarding ─────────────────────────────────┘        │          ├─► refunds / disputes
                                                    stock reservation          └─► emails
admin + audit log  ◄── reports, orders, drops, users
```

The only external blockers are the Stripe platform account (before milestone 4) and legal sign-off (before milestone 8).

## 2. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| 1 | Target communities prohibit external checkout links | **Already found** for eight of the ten swap subreddits whose rule could be located; unknown for Facebook groups and Discord | Fatal to the channel | Ask group admins before building commerce; choose the niche by where the answer is yes; favour channels the seller controls (Instagram, Discord, own following) | Founder |
| 2 | Sellers will not pay about 7% when their current workflow costs about 3% | Medium–high | High | Test the all-in number in interviews; keep the fee rate configurable; consider a buyer-side fee as Depop and Mercari do | Founder |
| 3 | Buyers do not trust an unfamiliar checkout | Medium | High | Stripe-hosted payment page; seller's community identity on the drop; a plain protection promise on the path to payment; measure checkout-start → paid | Product |
| 4 | Chargeback and fraud losses exceed fee revenue | Medium | High — one lost $110 dispute erases the margin on 30+ orders | Delayed payout until tracking; item price cap; card and wallet only; Stripe Radar; a pilot loss budget approved by the founder | Founder / Eng |
| 5 | Seller does not ship | Medium | Medium | Ship-by deadline, reminders, refund from funds not yet paid out, suspension | Eng / Ops |
| 6 | Overselling or duplicate orders | Low with the design | High (trust) | Row locks, database constraint, unique checkout on orders, event dedupe, automatic refund path; concurrency test in CI | Eng |
| 7 | Stock held by abandoned or hostile checkouts (30-minute Stripe minimum) | Medium | Low–medium | Instant release on cancel, one open checkout per browser, rate limits, "may return at…" display; self-expiry of idle sessions if data warrants | Eng |
| 8 | Merchant-of-record, sales-tax, or money-transmission exposure | Unknown | High | Counsel review before live mode; pilot volume is below economic-nexus thresholds; "delayed payout", never "escrow" | Founder |
| 9 | Stripe declines or restricts the platform account | Low–medium | Blocks payments | Apply early with an accurate description; keep prohibited categories out of the pilot niche | Founder |
| 10 | Stripe per-account and per-payout fees consume the margin on casual sellers | High | Medium | Weekly payout batching; consider a minimum order value; watch net revenue per seller, not GMV | Founder / Eng |
| 11 | Casual sellers do not return within the measurement window | High | Medium (ambiguous result, not failure) | Recruit enthusiast sellers first; use leading proxies for repeat intent | Founder |
| 12 | Personal data exposure (buyer addresses, photo location data) | Low with controls | High | Server-only data access, address redaction schedule, EXIF stripping, access tests | Eng |
| 13 | Scope growth before the core loop is validated | Medium | Medium | The cut list in [02-mvp-scope.md](02-mvp-scope.md) stands unless the founder reopens an item | Founder |
| 14 | A funded competitor (District) moves into individual-seller drops | Medium | Medium, later | Nothing to do now except learn faster; the pilot's value is knowing whether the behaviour exists | Founder |

## 3. The five open questions that matter most

| # | Question | Recommended decision |
|---|---|---|
| 1 | **Will the communities allow the link?** Most Reddit swap communities ban it, on the rule texts found (dated; to be checked against live sidebars). Facebook groups and Discord servers are unknown | Do not build milestones 4–7 until at least two target communities have said yes in writing, or the launch channel has been redefined as seller-owned audiences (Instagram, Discord, mailing lists) where no permission is needed |
| 2 | **Which niche?** Seventeen scored in [01](01-product-and-competitive-assessment.md), section 5 | **Miniatures / Warhammer, provisionally** — sellers already post 8-item price lists and whole armies, trading is spread across Facebook groups rather than one gated subreddit, and the incumbents charge 7% + processing or 13.6%. Confirm only after Facebook group admins answer question 1. Fountain pens if r/Pen_Swap's moderators would permit a compliant flow; and any niche where the founder already has standing beats the scores |
| 3 | **What does the seller pay, and how is it shown?** | Seller bears card processing: 4% + 2.9% + $0.30, presented as a single all-in figure ("about 7%") with the breakdown beneath. Absorbing processing makes every order a loss. Put the all-in figure to interviewees; if it is rejected, the alternative to test is a buyer-side service fee, not a lower rate |
| 4 | **What does HobbyDrop promise buyers, and who pays when it goes wrong?** Under the recommended payment design HobbyDrop is liable for every refund and chargeback | A short written promise: full refund if not shipped within 5 business days; report "not as described" within 3 days of delivery; otherwise sales are final. Funded by delayed payout first, then by a founder-approved loss budget for the pilot (suggested $1,000) with a $1,500 item cap |
| 5 | **Is HobbyDrop the merchant of record, and what follows for tax and licensing?** | Engineering assumes yes, because it keeps seller onboarding light. This needs counsel before live mode; the alternative (seller as settlement merchant) is a contained change to the payment configuration, not a rewrite |

## 4. Founder approval gate

Nothing beyond these documents has been built. To proceed I need a decision on each of the following.

| # | Decision | Recommendation |
|---|---|---|
| A | MVP scope as set out in [02-mvp-scope.md](02-mvp-scope.md), including the cuts | Approve |
| B | Stack and architecture in [03-architecture.md](03-architecture.md) | Approve |
| C | Payment architecture: Stripe Connect, destination charges, hosted Checkout, delayed payout, HobbyDrop as merchant of record pending counsel | Approve for test-mode build |
| D | Fee model: seller pays 4% plus card processing, shown all-in | Approve as the hypothesis to test |
| E | Launch niche | Miniatures / Warhammer, provisionally, pending the community-permission check. Not needed to start milestones 1–3, which are niche-neutral |
| F | Sequencing: build milestones 1–3, run the share test, then decide on payments — rather than building straight through | Approve the checkpoint |
| G | Recurring cost for the pilot: paid Vercel and Supabase tiers, roughly $45/month plus a domain, starting only when the pilot is near | Approve in principle; development uses free tiers |

Still gated and **not** requested now: production deployment, Stripe live mode, and any real-money transaction.

### What I need to start milestone 1

- Approval of A, B and F at minimum.
- A Supabase project for development (I can create one on the free tier through the connected Supabase account if you want me to — say so explicitly, since it creates a resource in your account).
- Later, before milestone 4: Stripe test-mode keys from a platform account you open. Before milestone 5: a Resend account and a domain for sending mail.
