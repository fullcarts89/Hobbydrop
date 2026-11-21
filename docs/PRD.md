# HobbyDrop — Product Requirements Document

**Version:** 1.0
**Status:** Proposed / Ready for technical discovery
**Product:** HobbyDrop
**Product category:** Consumer-to-consumer social commerce marketplace
**Initial platform:** Responsive web application / PWA
**Business model:** Transaction fees
**Primary implementation partner:** Claude Code

> This is the founder's PRD as supplied, kept verbatim as the source of truth.
> Discovery findings and recommended changes to it live in [`docs/discovery/`](discovery/).

---

# 1. Executive Summary

## 1.1 Product Vision

HobbyDrop is a community-powered marketplace where enthusiasts sell hobby equipment, collectibles, and accessories through curated, shareable, limited-time drops.

Instead of listing items individually across fragmented marketplaces, sellers can create an entire collection for sale in minutes, publish an attractive storefront, and distribute it directly to their existing communities.

Buyers get a convenient, trustworthy way to browse and purchase collections from people who share their interests.

**Long-term vision:** Become the commerce infrastructure powering transactions within hobby communities.

## 1.2 Mission

Make buying and selling within hobby communities as easy as sharing a link.

## 1.3 Core Product Thesis

Three hypotheses underpin HobbyDrop:

1. Hobby enthusiasts frequently accumulate equipment, collectibles, and accessories that they eventually want to sell.
2. Existing marketplaces are optimized primarily for individual listings, search, or live selling rather than curated collections shared within communities.
3. A streamlined drop creation and purchasing experience can generate organic distribution through sellers' existing social networks.

If these hypotheses prove correct, HobbyDrop can grow through seller-led distribution rather than relying primarily on expensive paid customer acquisition.

## 1.4 Strategic Positioning

HobbyDrop should initially operate as a **bring-your-own-audience commerce platform**.

It should not attempt to compete immediately with the discovery engines of eBay, Whatnot, or Facebook Marketplace.

The primary value proposition is:

**For sellers:** Turn a collection of hobby gear into a beautiful, shoppable drop with minimal effort.

**For buyers:** Discover and purchase interesting hobby items from trusted community members.

**For communities:** Keep commerce connected to the people, interests, and conversations that already bring members together.

---

# 2. Business Objectives

## 2.1 Primary Objective

Validate that sellers will independently create and share drops, buyers will transact, and both groups will return without continuous manual intervention.

## 2.2 Secondary Objectives

- Minimize seller onboarding friction.
- Establish a sustainable transaction-based revenue model.
- Encourage repeat seller activity.
- Generate organic buyer acquisition.
- Build reusable commerce infrastructure supporting multiple hobby categories.
- Keep operational costs and customer support requirements manageable.

## 2.3 Non-Goals

The initial product is not intended to:

- Replace eBay's generalized search marketplace.
- Compete with live-stream shopping platforms.
- Build a full social network.
- Operate a warehouse or fulfillment service.
- Provide authentication, grading, or appraisal services.
- Support auctions, bidding, or complicated negotiations.
- Launch across every hobby category simultaneously.
- Optimize for venture-scale growth before proving unit economics.

---

# 3. Target Market

## 3.1 Initial Customer Segments

### Primary: Hobby Sellers

Individuals who own multiple hobby-related items and want to sell them efficiently.

Examples:

- Photography enthusiasts selling camera accessories.
- Cycling enthusiasts upgrading equipment.
- Collectors rotating their collections.
- Hobbyists exiting or changing interests.
- Community members organizing equipment cleanouts.

### Secondary: Hobby Buyers

Individuals who regularly browse, collect, trade, or purchase equipment related to their interests.

They may already participate in:

- Reddit communities.
- Discord servers.
- Facebook groups.
- Instagram communities.
- Specialty hobby forums.
- Group chats.
- Local enthusiast groups.

### Tertiary: Community Organizers

People who operate enthusiast communities and may want to facilitate member-to-member commerce.

Community organizers are a potential distribution channel, not a required initial customer type.

## 3.2 Launch Category Selection

Do not select the first hobby category solely based on market size.

Evaluate candidate categories using:

| Criterion | Weight |
|---|---:|
| Existing community activity | 20% |
| Frequency of resale transactions | 20% |
| Seller inventory depth | 15% |
| Average transaction value | 15% |
| Shipping simplicity | 10% |
| Fraud and dispute exposure | 10% |
| Existing marketplace dissatisfaction | 10% |

Assess at least five candidate niches.

The final launch category must be selected through customer discovery and competitive analysis.

**Important:** Build a category-flexible technical foundation, but launch and test within one niche.

---

# 4. Problem Definition

## 4.1 Seller Problems

Current resale workflows often require sellers to:

1. Photograph every item.
2. Write individual descriptions.
3. Create separate listings.
4. Manage conversations across multiple platforms.
5. Coordinate payments and shipping.
6. Track which items remain available.
7. Promote listings individually.

These activities create friction, particularly when selling an entire collection.

## 4.2 Buyer Problems

Buyers may struggle with:

- Discovering items from community members.
- Understanding whether sellers are trustworthy.
- Purchasing multiple items in a single transaction.
- Navigating inconsistent payment arrangements.
- Finding relevant items before they sell.
- Tracking orders and seller communication.

## 4.3 Opportunity

Create a commerce experience optimized around the **collection or drop**, rather than the individual listing.

The drop becomes the primary unit of commerce, distribution, and discovery.

---

# 5. Product Principles

All design and engineering decisions should follow these principles.

### 5.1 Creation Must Be Effortless

Sellers should be able to create a basic drop without learning a complicated marketplace interface.

Target: Publish a five-item drop in under five minutes, assuming photos and prices are available.

### 5.2 Sharing Is a First-Class Feature

Every drop should be designed for sharing through existing community channels.

A drop should look compelling when previewed in a message or social feed.

### 5.3 Commerce Must Feel Trustworthy

Buyers need transparent pricing, clear item conditions, straightforward checkout, and understandable fulfillment policies.

### 5.4 The Product Should Feel Like a Hobby Community

Avoid the visual language of a generic enterprise commerce platform.

Use strong photography, expressive typography, tasteful motion, and a sense of discovery.

### 5.5 Start Narrow, Build Extensibly

The architecture should support multiple hobby categories without prematurely implementing every possible feature.

### 5.6 Automate Where It Matters

Use managed infrastructure and established commerce providers.

AI should reduce real user friction, not become a feature added merely for novelty.

### 5.7 Keep the Marketplace Operationally Lightweight

Avoid business models that require inventory ownership, manual brokerage, or intensive seller support.

---

# 6. User Personas

## Persona A: Casual Seller

**Profile:** Hobbyist with 5–20 items to sell.

**Motivation:** Clear out equipment and recover money.

**Pain points:** Listing effort, fragmented communications, shipping coordination.

**Success condition:** Sell multiple items without spending hours managing listings.

## Persona B: Enthusiast Seller

**Profile:** Active community member who frequently buys, upgrades, and resells equipment.

**Motivation:** Maintain an audience and generate repeat sales.

**Pain points:** Repetitive listing work, limited ability to showcase collections.

**Success condition:** Build a following and sell through recurring drops.

## Persona C: Community Buyer

**Profile:** Enthusiast who follows sellers and hobby communities.

**Motivation:** Find interesting items at reasonable prices.

**Pain points:** Fragmented discovery, uncertain seller reliability, cumbersome transactions.

**Success condition:** Quickly discover, purchase, and receive relevant items.

---

# 7. Core User Journeys

## 7.1 Seller Creates a Drop

1. Seller signs in.
2. Seller selects "Create Drop."
3. Seller enters a title, description, and cover image.
4. Seller uploads item photos.
5. Seller provides item names, conditions, prices, quantities, and optional descriptions.
6. Seller reviews the storefront.
7. Seller connects an eligible payout account.
8. Seller chooses whether to publish immediately or schedule the drop.
9. Seller publishes.
10. HobbyDrop generates a public URL and sharing preview.
11. Seller distributes the link to their community.
12. Seller receives purchase notifications and fulfills orders.

### Acceptance Criteria

- Seller can save an unpublished draft.
- Seller can add, edit, and remove items.
- Item images are optimized automatically.
- Seller can preview the storefront.
- Seller can publish without administrative assistance.
- Seller cannot accept payments until required payout onboarding is complete.
- Every published drop has a stable public URL.
- Publishing creates appropriate social preview metadata.
- Inventory is never oversold under concurrent checkout attempts.

## 7.2 Buyer Purchases an Item

1. Buyer opens a shared drop link.
2. Buyer views the collection.
3. Buyer selects an item.
4. Buyer reviews its condition, price, shipping terms, and seller information.
5. Buyer adds the item to the cart.
6. Buyer optionally adds other items from the same seller/drop.
7. Buyer proceeds through checkout.
8. Payment is processed.
9. Buyer receives an order confirmation.
10. Seller receives an order notification.
11. Seller fulfills the order.
12. Buyer receives shipping and delivery updates.

### Acceptance Criteria

- Buyers can browse without creating an account.
- Guest checkout is supported where permitted by the payment provider.
- Item prices and shipping charges are disclosed before payment.
- The system prevents duplicate orders caused by payment retries.
- Checkout inventory reservations expire safely.
- Failed payments do not create completed orders.
- Buyers receive order confirmations.
- Sellers can update fulfillment status.
- Buyers can access order details securely.

## 7.3 Buyer Follows a Seller

1. Buyer visits a seller storefront.
2. Buyer chooses to follow.
3. Buyer authenticates or provides a verified notification address.
4. Seller publishes a future drop.
5. Buyer receives a notification, subject to consent and preferences.
6. Buyer returns to browse.

Following is a post-MVP feature unless validation demonstrates that it is essential to repeat transactions.

---

# 8. MVP Functional Requirements

## 8.1 Authentication and Accounts

**Priority: P0**

Requirements:

- Email-based authentication.
- Passwordless sign-in preferred.
- Secure session management.
- Seller profile creation.
- Buyer account creation when necessary.
- Guest browsing.
- Guest checkout where supported.
- Account deletion workflow.
- Basic privacy settings.

Do not implement a custom authentication framework.

Use a mature authentication provider.

## 8.2 Seller Profiles

**Priority: P0**

Fields:

- Display name.
- Username.
- Profile image.
- Short biography.
- Optional external community links.
- Public drops.
- Basic seller status.

Future enhancements:

- Follower count.
- Seller reputation.
- Transaction history.
- Verified seller badges.

Never display sensitive payout or personal identity information publicly.

## 8.3 Drop Creation

**Priority: P0**

Each drop contains:

- Unique identifier.
- Seller identifier.
- Title.
- Description.
- Cover image.
- Category.
- Start timestamp.
- Optional end timestamp.
- Status.
- Public slug.
- Associated items.
- Created and updated timestamps.

Supported states:

- Draft.
- Scheduled.
- Live.
- Ended.
- Archived.

Requirements:

- Draft saving.
- Item management.
- Cover image selection.
- Drop preview.
- Publish/unpublish controls.
- Immediate publishing.
- Basic scheduling.
- Public sharing.

Use server-side authorization for all state changes.

## 8.4 Item Listings

**Priority: P0**

Fields:

- Item ID.
- Drop ID.
- Seller ID.
- Title.
- Description.
- Price.
- Currency.
- Quantity.
- Condition.
- Category.
- Images.
- Availability status.
- Shipping attributes where required.

Supported conditions:

- New.
- Like new.
- Good.
- Fair.
- For parts.

The initial product should support fixed-price sales only.

## 8.5 Image Management

**Priority: P0**

Requirements:

- Multiple images per item.
- Image compression.
- Thumbnail generation.
- Image ordering.
- Upload validation.
- File-size restrictions.
- Secure object storage.
- Image deletion.
- Responsive image delivery.

Do not allow arbitrary executable uploads.

## 8.6 Public Drop Storefront

**Priority: P0**

Requirements:

- Responsive layout.
- Drop cover and description.
- Seller identity.
- Item grid.
- Item detail view.
- Price and availability.
- Add-to-cart functionality.
- Share functionality.
- Clear purchase CTA.
- Social preview metadata.
- Loading, empty, and error states.

The storefront should feel like a curated collection rather than a generic classified listing page.

## 8.7 Cart and Checkout

**Priority: P0**

Requirements:

- Cart management.
- Multiple items from one seller.
- Fixed-price purchases.
- Shipping address collection.
- Shipping fee calculation or validated seller-configured shipping charges.
- Payment provider integration.
- Payment confirmation.
- Order creation.
- Payment failure handling.
- Inventory reservation.
- Refund handling.
- Transaction fee calculation.

**MVP constraint:** One seller per checkout.

Do not build multi-seller cart settlement until the business case is validated.

## 8.8 Payments and Seller Payouts

**Priority: P0**

Preferred provider: Stripe Connect, subject to current provider capabilities, pricing, marketplace eligibility, and legal review.

Requirements:

- Connected seller accounts.
- Required identity verification.
- Payment collection.
- Platform fees.
- Seller payouts.
- Payment webhooks.
- Refund processing.
- Chargeback handling.
- Payment reconciliation.
- Clear transaction records.

Never store raw payment card information.

Use hosted payment components wherever practical.

The platform must correctly handle payment failures, webhook retries, duplicate events, delayed confirmations, and seller onboarding restrictions.

Payout timing and liability must follow the selected provider's actual supported model.

## 8.9 Order Management

**Priority: P0**

Seller capabilities:

- View orders.
- View buyer shipping details for authorized fulfillment purposes.
- Mark orders as shipped.
- Enter tracking information.
- View payment and fulfillment status.
- Request or initiate refunds according to permissions.

Buyer capabilities:

- View order confirmation.
- Access order details.
- View fulfillment status.
- Access tracking information.
- Contact support.

## 8.10 Shipping

**Priority: P0 — Basic**

Initial shipping model:

- Seller-fulfilled orders.
- Domestic shipping only.
- Clearly disclosed shipping fees.
- Seller-provided tracking.
- No platform-operated warehousing.

Shipping label generation through a provider such as Shippo or EasyPost is a future enhancement.

Do not require a shipping aggregation integration for the earliest pilot unless it materially improves fulfillment reliability.

## 8.11 Sharing and Distribution

**Priority: P0**

Requirements:

- Copy link.
- Native mobile sharing where supported.
- Social preview images.
- Human-readable URLs.
- Campaign attribution.
- Referral source tracking.
- Seller-specific share links where appropriate.

Example URL structure:

`hobbydrop.com/@seller/drop-name`

Public sharing must not expose private buyer or seller data.

## 8.12 Notifications

**Priority: P0**

Initial notifications:

- Order confirmation.
- New seller order.
- Shipping confirmation.
- Refund confirmation.
- Important payment/account issues.

Email is sufficient for MVP.

Marketing and drop alerts require appropriate consent and unsubscribe controls.

## 8.13 Admin Operations

**Priority: P0**

A minimal protected admin interface should support:

- Viewing users.
- Viewing drops.
- Viewing orders.
- Reviewing reported content.
- Suspending problematic listings.
- Managing user restrictions.
- Reviewing payment status.
- Investigating fulfillment issues.
- Viewing audit logs for sensitive administrative actions.

Administrative actions must use explicit role-based authorization.

---

# 9. Post-MVP Features

## P1 — Retention and Marketplace Growth

- Follow sellers.
- Upcoming drop reminders.
- Seller dashboards.
- Repeat drop templates.
- Buyer wishlists.
- Personalized drop recommendations.
- Basic category browsing.
- Seller reputation and reviews.
- Better seller analytics.
- Integrated shipping labels.
- AI-assisted listing creation.

## P2 — Marketplace Expansion

- Cross-seller discovery.
- Search and filtering.
- Seller subscriptions.
- Community storefronts.
- Referral rewards.
- Bundling and seller discounts.
- Buyer offers.
- More sophisticated recommendation systems.
- International transactions where operationally justified.

## P3 — Advanced Commerce

- Auctions.
- Live drops.
- Verified collectibles.
- Authentication services.
- Community commerce APIs.
- Embedded checkout integrations.
- Seller storefront customization.
- Premium seller subscriptions.

Features must be prioritized using observed customer behavior rather than assumptions about what competitors offer.

---

# 10. AI Strategy

AI should primarily reduce seller effort.

## 10.1 AI-Assisted Listing Creation

Potential workflow:

1. Seller uploads photos.
2. AI suggests an item title.
3. AI suggests a description.
4. AI proposes a category.
5. AI suggests visible attributes.
6. Seller reviews and edits all information.
7. Seller publishes.

### Guardrails

- AI must not invent product specifications.
- AI must not fabricate authenticity or condition claims.
- AI must not claim ownership verification.
- Seller remains responsible for listing accuracy.
- AI suggestions must be editable.
- No automatic publishing without seller approval.

## 10.2 AI-Assisted Pricing

Potential future feature:

Suggest pricing ranges using relevant market data.

Do not implement until trustworthy comparable sales data is available.

Do not fabricate comparable sales or imply pricing accuracy without evidence.

## 10.3 AI Prioritization

AI is not a launch dependency.

Prioritize the core transaction workflow before adding model inference costs.

---

# 11. Design and User Experience

## 11.1 Design Direction

HobbyDrop should feel like a combination of:

- A curated product collection.
- A contemporary consumer shopping experience.
- An enthusiast community.
- A lightweight creator storefront.

The interface should be visually distinctive, but conversion and usability must take priority over decoration.

## 11.2 Visual Principles

- Photography-led presentation.
- Strong editorial typography.
- Clear visual hierarchy.
- Generous spacing.
- Tasteful microinteractions.
- Mobile-first layouts.
- Accessible contrast.
- Clear purchase actions.
- Consistent design tokens.
- Fast perceived performance.

## 11.3 Motion Principles

Use motion to communicate state and improve comprehension.

Examples:

- Smooth cart additions.
- Item image transitions.
- Subtle drop publication confirmation.
- Inventory status changes.
- Checkout progress.
- Lightweight page transitions.

Respect reduced-motion preferences.

Avoid animation that delays purchasing or harms accessibility.

## 11.4 Critical Screens

Design and implement:

1. Landing page.
2. Sign-in flow.
3. Seller onboarding.
4. Seller dashboard.
5. Create/edit drop.
6. Add/edit item.
7. Drop preview.
8. Public drop storefront.
9. Item detail.
10. Cart.
11. Checkout.
12. Order confirmation.
13. Buyer order details.
14. Seller order management.
15. Seller public profile.
16. Minimal admin interface.

## 11.5 Responsive Requirements

Primary design target: Mobile.

Secondary targets:

- Tablet.
- Desktop.

All core workflows must function on mobile without requiring desktop access.

---

# 12. Trust, Safety, and Marketplace Policies

HobbyDrop will facilitate transactions between individuals.

Trust and safety are foundational requirements.

## 12.1 Prohibited Items

Define and enforce a prohibited-products policy covering illegal, dangerous, counterfeit, stolen, and otherwise restricted merchandise.

Use the payment provider's restrictions as a baseline.

## 12.2 Fraud Prevention

Implement:

- Seller identity verification through the payment provider.
- Checkout abuse protection.
- Rate limiting.
- Suspicious activity logging.
- Basic transaction risk controls.
- Reporting functionality.
- Seller suspension capability.
- Duplicate payment prevention.

## 12.3 Disputes and Refunds

Establish documented procedures for:

- Items not received.
- Materially inaccurate descriptions.
- Damaged items.
- Unauthorized transactions.
- Refund requests.
- Payment disputes.

Clarify platform responsibilities, seller obligations, and buyer protections before accepting public transactions.

## 12.4 Privacy

Collect only necessary information.

Protect:

- Customer addresses.
- Seller payout information.
- Contact details.
- Order histories.
- Authentication credentials.

Implement retention and deletion policies appropriate to financial and legal obligations.

---

# 13. Monetization

## 13.1 Initial Business Model

Charge sellers a transaction fee on completed sales.

**Proposed validation range:** 4–8%.

Initial pricing hypothesis: 4% platform fee, with payment processing separately disclosed.

Final pricing requires validation against:

- Payment processing costs.
- Competitor fees.
- Refund exposure.
- Chargeback costs.
- Customer support.
- Hosting costs.
- Seller willingness to pay.

## 13.2 Example Transaction

For a hypothetical $100 merchandise sale:

| Component | Amount |
|---|---:|
| Item sale | $100.00 |
| Platform fee at 4% | $4.00 |
| Seller proceeds before other fees | $96.00 |

Payment processing, shipping, taxes, refunds, and other applicable costs are excluded from this simplified example.

The implementation must calculate fees precisely and avoid ambiguous fee presentation.

## 13.3 Future Revenue Opportunities

- Premium seller accounts.
- Advanced seller analytics.
- Storefront customization.
- Integrated shipping services.
- Community commerce infrastructure.
- Optional promoted discovery.

Do not implement these before demonstrating repeat transaction demand.

---

# 14. Technical Architecture

Claude should evaluate the actual project environment before finalizing the stack.

For a greenfield implementation, the preferred architecture is:

## 14.1 Frontend

- Next.js.
- React.
- TypeScript.
- Tailwind CSS.
- Accessible component primitives.
- Responsive PWA-oriented design.

## 14.2 Backend

- TypeScript server-side application logic.
- PostgreSQL.
- Managed authentication.
- Managed object storage.
- Background jobs for asynchronous processing.
- Provider-backed transactional email.

## 14.3 Infrastructure

Preferred options to evaluate:

- Vercel for deployment.
- Supabase for PostgreSQL, authentication, and storage.
- Stripe Connect for payments.
- Resend or equivalent for transactional email.
- Sentry for error monitoring.
- PostHog or equivalent for product analytics.

These are proposed defaults, not mandatory selections.

Evaluate costs, limitations, security, and operational complexity before committing.

## 14.4 Architecture Principles

- Server-side authorization.
- Explicit service boundaries.
- Type-safe interfaces.
- Database migrations.
- Transactional integrity.
- Idempotent payment processing.
- Minimal custom infrastructure.
- Clear separation between business logic and UI.
- Automated testing.
- Environment-specific configuration.
- Secure secret management.

## 14.5 Concurrency and Inventory

Inventory correctness is a critical technical requirement.

The implementation must handle:

- Multiple simultaneous buyers.
- Expired checkout sessions.
- Payment confirmation delays.
- Duplicate webhooks.
- Failed payments.
- Refunds.
- Seller listing changes during checkout.

Use transactional database operations and explicit inventory reservation semantics.

Never rely on frontend state to enforce inventory availability.

---

# 15. Initial Data Model

Claude should design a normalized schema covering at least:

## Users

- id
- email
- display_name
- username
- avatar_url
- created_at
- updated_at

## Seller Accounts

- id
- user_id
- payment_provider_account_id
- onboarding_status
- payout_status
- created_at

## Drops

- id
- seller_id
- title
- description
- slug
- cover_image_url
- category_id
- status
- starts_at
- ends_at
- created_at
- updated_at

## Items

- id
- drop_id
- seller_id
- title
- description
- price_amount
- currency
- quantity
- condition
- status
- created_at
- updated_at

## Item Images

- id
- item_id
- storage_key
- sort_order

## Orders

- id
- buyer_id (nullable for guest checkout)
- seller_id
- status
- subtotal_amount
- shipping_amount
- tax_amount
- platform_fee_amount
- total_amount
- currency
- created_at

## Order Items

- id
- order_id
- item_id
- quantity
- unit_price_amount
- item_snapshot

## Payments

- id
- order_id
- provider_payment_id
- status
- amount
- currency
- created_at

## Inventory Reservations

- id
- item_id
- checkout_reference
- quantity
- expires_at
- status

## Shipments

- id
- order_id
- carrier
- tracking_number
- status
- shipped_at

## Event Tracking

- id
- event_type
- user_id
- anonymous_id
- drop_id
- metadata
- created_at

Additional entities should cover:

- Refunds.
- Disputes.
- Seller reports.
- Admin actions.
- Notification preferences.
- Payment webhook deduplication.

Claude must define foreign keys, indexes, uniqueness constraints, access controls, and retention requirements.

---

# 16. Analytics and Growth Measurement

Instrument the complete acquisition and transaction funnel.

## 16.1 Seller Funnel

Track:

- Seller signups.
- Seller onboarding completion.
- Drops started.
- Drops published.
- Items per drop.
- Time to publish.
- Share actions.
- First sale conversion.
- Repeat drop creation.

## 16.2 Buyer Funnel

Track:

- Drop visits.
- Traffic source.
- Item views.
- Add-to-cart events.
- Checkout starts.
- Completed purchases.
- Average order value.
- Repeat purchases.

## 16.3 Marketplace Metrics

Core metrics:

- Gross merchandise volume.
- Net platform revenue.
- Completed orders.
- Average order value.
- Seller activation.
- Buyer conversion.
- Repeat seller rate.
- Refund rate.
- Dispute rate.
- Contribution margin.
- Organic acquisition percentage.

## 16.4 North Star Metric

**Monthly GMV generated by repeat active sellers.**

This combines transaction volume with evidence of recurring seller value.

Supporting metrics should distinguish genuine marketplace growth from isolated large transactions.

---

# 17. Validation Framework

Do not treat the MVP as validated merely because it is functional.

## Stage 1 — Problem Validation

Interview 15–20 potential sellers.

Questions to answer:

- How frequently do they sell hobby equipment?
- How many items do they typically sell?
- Which platforms do they use?
- What takes the most time?
- Would they create a curated drop?
- Would they share a new platform link?
- Would buyers trust that link?
- What fee would they accept?

**Gate:** Demonstrated recurring pain and credible willingness to try the workflow.

## Stage 2 — Concierge Pilot

Recruit 10–20 sellers in one hobby category.

Help them create and distribute drops.

Observe:

- Drop creation time.
- Sharing behavior.
- Buyer traffic.
- Purchase conversion.
- Fulfillment issues.
- Seller feedback.

**Gate:** Evidence that sellers can generate real buyer demand through existing communities.

## Stage 3 — Transaction Validation

Initial targets:

- 50–100 completed orders.
- $5,000–$15,000 GMV.
- Meaningful seller-led traffic.
- Repeat selling intent.
- Manageable support requirements.

These are experimental targets, not guaranteed outcomes.

**Gate:** Evidence of repeatable transactions with acceptable operational costs.

## Stage 4 — Retention Validation

Measure whether sellers voluntarily return to create additional drops.

Investigate why buyers do or do not return.

**Gate:** Repeat activity sufficient to justify broader marketplace investment.

---

# 18. Success and Failure Criteria

## Success Indicators

- Sellers independently create drops.
- Sellers share links without prompting.
- Buyers transact through those links.
- Seller acquisition remains inexpensive.
- Repeat sellers emerge.
- Customer support is manageable.
- Transaction economics remain positive after variable costs.

## Warning Indicators

- Sellers need extensive manual assistance.
- Buyers distrust unfamiliar checkout links.
- Sellers prefer existing marketplaces.
- Transaction volume requires paid acquisition.
- Most sellers never create a second drop.
- Payment and shipping support costs overwhelm fees.
- Drop timing adds friction rather than urgency.

## Stop/Pivot Conditions

Reevaluate the business if:

- Sellers consistently refuse to share drops.
- Transaction conversion is materially weaker than existing alternatives.
- Repeat seller activity remains low after meaningful iteration.
- Operational costs prevent viable contribution margins.
- The product offers insufficient differentiation to justify switching.

Do not continue adding features to compensate for an unvalidated core value proposition.

---

# 19. Competitive Analysis Requirements

Before implementation, Claude should research current offerings and capabilities from relevant competitors, including:

- eBay.
- Whatnot.
- Facebook Marketplace.
- Depop.
- Mercari.
- Poshmark.
- Shopify.
- District.
- Community-based selling workflows in Discord and Reddit.

Assess:

1. Seller listing friction.
2. Collection and bundle selling.
3. Audience ownership.
4. Marketplace discovery.
5. Seller fees.
6. Buyer protections.
7. Payment processing.
8. Shipping.
9. Social sharing.
10. Community integration.
11. Seller retention tools.
12. Competitive defensibility.

Distinguish verified capabilities from assumptions.

Identify which features HobbyDrop must match, which should be differentiated, and which should deliberately be excluded.

---

# 20. Execution Roadmap

## Phase 0 — Product and Technical Discovery

Deliverables:

- Competitive analysis.
- Launch niche recommendation.
- Technical architecture.
- Data model.
- Payment feasibility review.
- Trust and safety requirements.
- MVP scope confirmation.
- Risk register.
- Implementation plan.

Do not begin full implementation before resolving material payment and marketplace architecture questions.

## Phase 1 — Seller Experience

Build:

- Authentication.
- Seller profile.
- Seller dashboard.
- Drop creation.
- Item management.
- Image uploads.
- Drop preview.
- Public storefront.

**Exit criterion:** A seller can create and publish a fully functional public drop using realistic test data.

## Phase 2 — Commerce

Build:

- Cart.
- Checkout.
- Payment integration.
- Seller onboarding.
- Inventory reservations.
- Order creation.
- Refund handling.
- Transactional notifications.

**Exit criterion:** A complete purchase can be executed and verified in a test environment.

## Phase 3 — Fulfillment and Operations

Build:

- Seller order dashboard.
- Shipping status.
- Tracking.
- Buyer order view.
- Admin operations.
- Reporting.
- Basic support workflows.

**Exit criterion:** A transaction can progress from purchase through fulfillment with auditable state changes.

## Phase 4 — Product Quality

Complete:

- Mobile UX review.
- Accessibility review.
- Performance optimization.
- Security testing.
- Payment failure testing.
- Inventory concurrency testing.
- Analytics verification.
- End-to-end testing.

**Exit criterion:** The application is reliable enough for a controlled real-money pilot, subject to legal and operational readiness.

## Phase 5 — Controlled Pilot

Recruit initial sellers.

Collect product analytics and qualitative feedback.

Iterate based on observed behavior.

Do not broaden category support or add advanced features until the pilot demonstrates product value.

---

# 21. Engineering Quality Requirements

## Testing

Implement:

- Unit tests for business logic.
- Integration tests for database operations.
- Payment webhook tests.
- Inventory concurrency tests.
- Authentication and authorization tests.
- End-to-end seller and buyer journeys.
- Checkout failure tests.
- Refund tests.
- Mobile browser testing.

## Security

Review:

- Broken access control.
- Row-level security where applicable.
- Cross-site scripting.
- Cross-site request forgery.
- Injection attacks.
- File upload abuse.
- Webhook authenticity.
- Secret exposure.
- Rate limiting.
- Sensitive data logging.
- Administrative privilege escalation.

## Reliability

Requirements:

- Error monitoring.
- Structured logs.
- Database backups.
- Safe migrations.
- Payment reconciliation.
- Retry-safe background jobs.
- Recoverable checkout failures.

## Performance

Initial targets:

- Strong mobile Core Web Vitals.
- Fast public storefront loading.
- Efficient image delivery.
- Minimal unnecessary client-side JavaScript.
- Responsive cart interactions.
- Graceful loading and error states.

Performance should be measured using realistic data and devices.

---

# 22. Claude Code Operating Instructions

You are acting as:

- Senior product manager.
- Principal software architect.
- Senior full-stack engineer.
- Marketplace commerce specialist.
- Senior product designer.
- Application security reviewer.

Your job is to translate this PRD into a practical, maintainable product.

## Step 1 — Inspect the Environment

Before writing code:

1. Inspect the repository.
2. Identify existing frameworks and infrastructure.
3. Determine whether reusable components exist.
4. Review dependencies.
5. Identify deployment configuration.
6. Identify existing tests and CI.
7. Document technical constraints.

Do not invent existing implementation details.

If the repository is empty, explicitly state that this is a greenfield build.

## Step 2 — Challenge the PRD

Review the requirements critically.

Identify:

- Unnecessary complexity.
- Missing commerce requirements.
- Operational risks.
- Security concerns.
- Marketplace assumptions.
- Opportunities to simplify.
- Features that should be deferred.

Do not blindly implement every feature.

Recommend the smallest viable architecture that can validate the business.

## Step 3 — Produce a Build Plan

Create:

- Architecture decision record.
- Feature dependency map.
- Database design.
- API/service design.
- UI component architecture.
- Testing strategy.
- Deployment plan.
- Implementation milestones.

Identify blocking decisions requiring founder approval.

## Step 4 — Implement in Vertical Slices

Each slice must include:

- Working UI.
- Backend logic.
- Database changes.
- Authorization.
- Validation.
- Error handling.
- Tests.
- Documentation.

Avoid building disconnected mock screens that are not integrated with real application behavior.

## Step 5 — Verify Functionality

For every completed milestone:

- Run tests.
- Verify build.
- Check type safety.
- Review security implications.
- Validate responsive layouts.
- Verify the complete relevant user journey.
- Report unresolved issues.

Never report a feature as production-ready based solely on a successful compilation.

## Step 6 — Provide Demonstrations

Provide:

- Deployment or preview URL when available.
- Screenshots of critical flows.
- Test results.
- Known limitations.
- Manual testing instructions.
- Remaining blockers.

Clearly distinguish:

- Implemented.
- Tested.
- Demonstrated.
- Production-ready.

## Step 7 — Preserve Founder Decision Gates

Request founder approval for:

- Final launch niche.
- Payment architecture.
- Monetization changes.
- Major scope expansion.
- Significant recurring infrastructure costs.
- Production deployment.
- Real-money transaction activation.

Do not silently expand scope.

---

# 23. Required Initial Response from Claude

Before beginning implementation, return the following:

### A. Product Assessment

Evaluate the business thesis, differentiation, and likelihood of attracting sellers and buyers.

### B. Competitive Assessment

Identify direct competitors and any significant weaknesses in HobbyDrop's positioning.

### C. MVP Recommendation

Recommend the smallest viable product that could validate the business within approximately 90 days.

### D. Technical Architecture

Propose the stack, infrastructure, data model, payment architecture, and deployment approach.

### E. Build Roadmap

Provide phased milestones, dependencies, estimated engineering effort, and test requirements.

### F. Risks and Open Questions

Identify the five most important unresolved questions and recommend decisions.

### G. Founder Approval Gate

Pause before substantial implementation and request approval of the recommended MVP scope and architecture.

Do not begin a broad autonomous build until this gate is approved.

---

# 24. Final Product Standard

HobbyDrop should ultimately enable the following experience:

A hobbyist opens the application, photographs several items, creates a beautiful collection storefront, publishes it, and shares one link with their community.

Buyers open that link, browse the collection, purchase items securely, and receive their orders.

The seller gets paid.

The platform earns a small transaction fee.

The experience is sufficiently simple and useful that sellers want to do it again.

**That repeatable behavior—not the number of implemented features—is the foundation of HobbyDrop.**
