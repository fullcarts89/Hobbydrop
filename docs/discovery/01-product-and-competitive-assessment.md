# 01 — Product and competitive assessment

Status: **discovery findings for founder review.** Researched 2026-11-21.

**How to read the evidence.** Fee and policy figures were read from the companies' own pages unless tagged. *(snippet)* means the primary page blocked direct access and the figure was read from a search excerpt of it. *(third-party)* means a secondary source. *(unverified)* means it could not be confirmed and should be treated as an assumption. Reddit was unreachable during research, so **every statement about subreddit rules is unverified** — which matters, because one of those rules may decide whether the product works.

## 1. Assessment of the thesis

The PRD rests on three hypotheses. They are not equally strong.

| Hypothesis | Assessment |
|---|---|
| 1. Hobbyists accumulate gear and eventually sell it | **True.** Not in doubt, and not differentiating |
| 2. Existing marketplaces are built around the single listing, not the collection | **Half true.** The big marketplaces are. But the workflow HobbyDrop actually displaces — a sale post in a swap community — is already "one link, many items, one price list", and it is free. Depop, Mercari and Whatnot already combine multiple items from one seller into one payment and one shipment |
| 3. Sellers will distribute drops through their own communities | **Unproven, and the whole model depends on it.** See below |

### The core risk: "bring your own audience" mostly means "post in someone else's community"

The PRD's primary persona is a casual seller with 5–20 items. That person does not have an audience. They have *membership* in a subreddit, Discord server or Facebook group that someone else moderates and whose rules they must follow. Whether those communities allow a link to an external checkout is unknown, and at least one large swap community is reported to require PayPal or Venmo Goods & Services for US sellers *(snippet)*. If moderators say no, the main distribution channel is closed regardless of how good the product is.

The seller who genuinely has an audience is the PRD's Persona B — the enthusiast with an Instagram following, a Discord presence, or a known name on a forum. That is a smaller group, but it is the one for whom the product works as described. **Recommendation: treat Persona B as the launch customer and Persona A as the expansion.**

### Price position

Worked on a $200 item with $15 buyer-paid shipping:

| Where the seller sells | Seller's cost | % of $215 |
|---|---:|---:|
| Reddit or Discord + PayPal Goods & Services (2.99%, no fixed fee) | $6.43 | 3.0% |
| Depop (0% selling fee, 3.3% + $0.45 processing; buyer pays up to 5% + $1 on top) | $7.55 | 3.5% |
| **HobbyDrop: 4% + card processing** | **$15.14** | **7.0%** |
| Reverb (5% + processing; processing rate third-party) | ≈ $18.10 | 8.4% |
| Facebook Marketplace, shipped (10%) | $21.50 | 10.0% |
| Mercari (10%; buyer pays a further 3.6%) | $21.50 | 10.0% |
| Whatnot, standard tier (8% + 2.9% + $0.30) | $22.54 | 10.5% |
| eBay, most categories (13.6% + $0.40) | $29.64 | 13.8% |
| Poshmark (20%) | $40.00 | 18.6% |

HobbyDrop is roughly **half the cost of the marketplaces it says it is not competing with, and more than double the cost of the workflow it is actually replacing.** The seller on a swap subreddit is being asked to pay about four extra points for:

- a page that looks better than a text post;
- stock that updates itself, instead of editing "SOLD" into a post and juggling direct messages;
- one checkout for the buyer instead of one invoice per deal;
- buyers who can pay by card or Apple Pay without a PayPal account.

On a $1,000 clear-out that is about $40. Sellers who value their evening will pay it; the price-sensitive will not. That is a real but narrow wedge, and seller interviews should test the *number*, not the concept.

### The buyer side

A buyer on a swap subreddit has PayPal's 180-day purchase protection and can see the seller's trade history. HobbyDrop offers an unfamiliar domain and a seller with no history there. Three things soften this: the payment page is Stripe's, which buyers recognise; the seller's existing community identity can be shown on the drop; and a short, plainly worded protection promise can sit on the checkout path. None of them removes the problem, and the protection promise is funded by HobbyDrop (see [03-architecture.md](03-architecture.md) 4.2).

### "Limited-time"

Nothing found suggests buyers or sellers of used gear want a deadline. Existing event-style selling is live and auction-led (Whatnot, District, Poshmark shows). The PRD itself lists "drop timing adds friction rather than urgency" as a warning sign. An end date stays optional and off by default; the product is the *collection page*, and "drop" is the name.

### Retention

A casual seller clears out once or twice a year. The PRD's north-star metric — monthly GMV from repeat active sellers — will barely register inside 90 days for that persona. For the pilot, use leading proxies: a second drop within 60 days, unprompted re-shares of the same drop, and buyers who purchase from a second seller.

### Overall

**The product is worth building as an experiment, not yet as a business.** The engineering is well understood and the cost of finding out is modest. But the PRD understates how good and how cheap the incumbent workflow is, and overstates how much audience the typical seller has. The fastest way to lose three months is to build the full MVP before learning whether a single target community will allow the link. That check costs a few messages to moderators and should happen first.

## 2. Competitors

### Fees — US individual seller

| Platform | Seller pays | Buyer pays | Notes |
|---|---|---|---|
| eBay | 13.6% of sale total up to $7,500 in most categories + $0.30 / $0.40 per order; trading cards 13.25%; guitars 6.7%; no separate processing fee | — | Closed its acquisition of Depop 2026-07-30 *(third-party)* |
| Whatnot | 8% commission (standard tier) + 2.9% + $0.30 processing on item, shipping and tax | Shipping at Whatnot's rates | Tiered rates since 2026-09-21; lower only above $100k per four weeks |
| Facebook Marketplace | 10% per shipped order ($0.80 minimum) on item, shipping and tax; local pickup free *(snippet)* | — | Was 5% before 2025 *(third-party)* |
| Depop | 0% selling fee; 3.3% + $0.45 processing | Marketplace fee up to 5% + $1 | Selling fee removed in the US 2024-07-18 |
| Mercari | 10% of item + buyer-paid shipping | 3.6% buyer-protection fee | Since 2025-01-06 |
| Poshmark | $2.95 under $15; 20% from $15 *(snippet)* | Flat-rate label *(third-party)* | |
| Shopify | Basic $39/month ($29 billed yearly) + 2.9% + $0.30 *(snippet)* | — | Starter plan closed to new stores; Linkpop shut down 2025-07-07 *(third-party)* |
| District (district.net) | Community owner: $29 or $99/month + 5% selling fee *(snippet)*. Sellers inside a community: owner-set commission + processing *(snippet)* | None found | $14.7M seed, May 2026 |
| Reddit / Discord + PayPal G&S | 2.99%, no fixed fee | — | PayPal fee page updated 2026-11-04 |

### Capabilities

| | One link for a whole collection, multi-item checkout | Seller can take the audience elsewhere | Buyer protection window | Shipping | Listing help |
|---|---|---|---|---|---|
| eBay | Cart; combined shipping by seller request *(snippet)* | No — sharing contact details or links before a sale is prohibited | 30 days from delivery | Tracked required | AI photo-to-listing and bulk tool *(snippet)* |
| Whatnot | Per-show link; orders auto-bundled onto one label | No — off-platform contact prohibited *(snippet)* | Earlier of 30 days from purchase or 14 from delivery | Platform label on every order | Manual, CSV, Shopify sync |
| Facebook Marketplace | *(unverified)* | No export *(unverified)* | On-site checkout only *(snippet)*; seller protection only ≤ $500 with a Meta label | Ship within 7 days | Meta AI drafts listing and price |
| Depop | Automatic bundle discount / combined shipping | *(unverified)* | 30 days from purchase | Depop label or own | Auto tags |
| Mercari | Cart up to 10 items / $2,000 from one seller *(snippet)* | *(unverified)* | 72 hours from delivery *(snippet)* | Prepaid labels *(snippet)* | *(unverified)* |
| Poshmark | Bundles at seller's discretion *(third-party)* | *(unverified)* | 3 days from delivery *(third-party)* | Prepaid label | AI listing *(snippet)*, CSV *(third-party)* |
| Shopify | Yes | Yes — seller owns the customer list *(unverified)* | None beyond card disputes *(unverified)* | Seller-fulfilled | Full store setup |
| District | Each community is its own marketplace URL | Owner-run community with chat *(snippet)* | Advertised; terms *(unverified)* | *(unverified)* | "AI commerce builder" *(snippet)* |
| Reddit + G&S | One post lists many items; one invoice per deal | Audience belongs to the subreddit | PayPal: 180 days | Seller's own label | Free-text post |

### Closest competitors the PRD did not name

| Product | What it is | Why it matters |
|---|---|---|
| **ClearList** (clearlist.me) | One link for a whole sale; photo → AI listing with price range in about 30 seconds; no buyer account; 0% commission, paid tiers ($20 for 50 items) | The nearest thing to HobbyDrop's core mechanic. **Local pickup only and takes no payments** — it has the page but not the commerce |
| **Yardio** (useyardio.com) | One-link moving sale with checkout; 1% + provider fee | Same shape, aimed at household goods; shipping and protection not mentioned |
| **ClaimDrop**, CommentSold | Turn Instagram "sold / mine" replies into payment requests; ClaimDrop takes no cut and never touches money | This is where sellers with a real audience already sell. It shows the behaviour exists — and that the going rate for the tooling is zero |
| **Vertical venues**: Reverb (5% + processing), Swappa (3% + 3% + PayPal) *(snippet)*, Pinkbike BuySell (no fees, no payments) *(third-party)* | Category incumbents | Where demand already sits in each niche |
| **MPB / KEH** | Instant quote for a whole camera kit, prepaid insured label, no fees *(snippet)* | The "sell everything at once" substitute for cameras — lower price, zero effort |
| **District** | Community-owned marketplaces with live shows and auctions | Closest to the PRD's *long-term* vision of "commerce infrastructure for hobby communities", well funded, approaching from the community owner down rather than the individual seller up |

## 3. What this means for the product

### Must match

- **Multi-item cart, one payment, combined shipping.** Every credible alternative has it.
- **A stated buyer-protection window.** The market range is 3 to 30 days on marketplaces and 180 on PayPal. HobbyDrop needs a specific number on the checkout path.
- **Tracking captured on every order.** PayPal and Meta both make seller protection conditional on tracked delivery to the order address; it is also the evidence a card dispute turns on.
- **Visible seller identity and history.** Swap communities provide this for free through flair and scammer lists; HobbyDrop has to at least display the seller's existing community identity.

### Differentiate

No product found combines all five of: one shareable page for a whole collection; fixed-price *shipped* checkout; stated buyer protection; no lock-in of the seller's audience; and a single-digit fee. The one-link tools are local or unprotected; the marketplaces protect buyers but forbid taking them elsewhere. "None found" is not proof that none exists.

Shopify has also vacated the casual end — its cheapest plan for a new store is now $29–39 a month — so there is no low-commitment "small store for a weekend" from the obvious provider.

### Deliberately exclude

Discovery and search (eBay's ground), live and auction selling (Whatnot, District), prepaid-label logistics (every marketplace; revisit after the pilot), and trade-in (MPB).

### Table stakes HobbyDrop will launch without — knowingly

- **AI photo-to-listing.** eBay, Facebook, Poshmark and ClearList all have it. It is no longer a differentiator; it is an expectation among sellers who use those platforms. It stays out of the MVP only because it does not change the answer to any validation question, and it becomes the first post-MVP item if sellers stall during creation.
- **Platform shipping labels.** Their absence weakens dispute evidence. Mitigated by requiring tracking before payout.

## 4. Strongest reasons a seller will say no

Worth putting directly to interviewees.

From a swap community with PayPal:

1. It is cheaper — about 3% against about 7%.
2. The buyers are in the community, and the community may not allow the link.
3. Buyers already trust PayPal's 180 days, and trade history does not carry over.
4. A sale post already is one link with many items.

From eBay:

1. eBay brings buyers, search, and sold-price history. HobbyDrop brings none; a seller without a following gets nothing for the fee.
2. eBay's guarantee and brand raise both conversion and achievable price.
3. Rare items do better at auction.

## Key sources

- eBay fees: https://www.ebay.com/help/selling/fees-credits-invoices/selling-fees?id=4822 · off-platform policy: https://www.ebay.com/help/policies/payment-policies/offers-buy-sell-outside-ebay-policy?id=4272 · guarantee: https://www.ebay.com/help/policies/ebay-money-back-guarantee-policy/ebay-money-back-guarantee-policy?id=4210
- Whatnot fees: https://help.whatnot.com/hc/en-us/articles/4847069165965 · shipping: https://help.whatnot.com/hc/en-us/articles/46768886074765-Shipping-for-sellers-in-the-US
- Meta merchant policies: https://www.facebook.com/legal/merchant_policies · AI listing: https://about.fb.com/news/2026/03/facebook-marketplace-new-meta-ai-tools-make-selling-faster-and-easier
- Depop fees: https://depophelp.zendesk.com/hc/en-gb/articles/360001791127 · marketplace fee: https://depophelp.zendesk.com/hc/en-gb/articles/21752555753361-What-is-the-Marketplace-fee · bundles: https://depophelp.zendesk.com/hc/en-gb/articles/360017585774-Bundles
- Mercari fees: https://www.mercari.com/us/help_center/article/169/
- Poshmark fees: https://support.poshmark.com/s/article/297755057?language=en_US
- Shopify Starter: https://help.shopify.com/en/manual/intro-to-shopify/pricing-plans/plans-features/shopify-starter-plan · pricing: https://www.shopify.com/pricing
- District: https://district.net/pricing · https://help.district.net/selling/setting-up-to-sell/fees · funding: https://finance.yahoo.com/markets/stocks/articles/district-founded-three-snapchat-alumni-113847380.html
- PayPal fees: https://www.paypal.com/us/webapps/mpp/merchant-fees · buyer protection: https://www.paypal.com/us/legalhub/paypal/buyer-protection · seller protection: https://www.paypal.com/us/legalhub/paypal/seller-protection
- r/mechmarket rules (seen only as a mirror excerpt): https://www.reddit.com/r/mechmarket/wiki/rules/rules
- ClearList: https://clearlist.me/ · Yardio: https://www.useyardio.com/pricing · ClaimDrop: https://www.useclaimdrop.com/
- Reverb fees: https://help.reverb.com/hc/en-us/articles/40917652290843-What-fees-will-I-pay-for-selling-on-Reverb · Swappa: https://swappa.com/blog/marketplace-selling-fees/ · MPB: https://www.mpb.com/en-us/selling-to-mpb
