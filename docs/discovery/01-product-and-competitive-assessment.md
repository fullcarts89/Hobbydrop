# 01 — Product and competitive assessment

Status: **discovery findings for founder review.** Researched 2026-11-21.

**How to read the evidence.** Fee and policy figures were read from the companies' own pages unless tagged. *(snippet)* means the primary page blocked direct access and the figure was read from a search excerpt of it. *(third-party)* means a secondary source. *(unverified)* means it could not be confirmed and should be treated as an assumption. Reddit could not be read directly during research. **Subreddit rules quoted here come from moderator posts and wiki text surfaced through search indexes and mirrors**; each is dated in section 5 and several are years old. They must be checked against the live sidebars before anything is built on them — which matters, because those rules may decide whether the product works.

## 1. Assessment of the thesis

The PRD rests on three hypotheses. They are not equally strong.

| Hypothesis | Assessment |
|---|---|
| 1. Hobbyists accumulate gear and eventually sell it | **True.** Not in doubt, and not differentiating |
| 2. Existing marketplaces are built around the single listing, not the collection | **Half true.** The big marketplaces are. But the workflow HobbyDrop actually displaces — a sale post in a swap community — is already "one link, many items, one price list", and it is free. Depop, Mercari and Whatnot already combine multiple items from one seller into one payment and one shipment |
| 3. Sellers will distribute drops through their own communities | **Unproven, and the whole model depends on it.** See below |

### The core risk: "bring your own audience" mostly means "post in someone else's community"

The PRD's primary persona is a casual seller with 5–20 items. That person does not have an audience. They have *membership* in a subreddit, Discord server or Facebook group that someone else moderates and whose rules they must follow. **The evidence found says most of them do not allow it.** Of the swap subreddits whose link rule could be found, eight ban links to outside sales pages — cameras, mechanical keyboards, fountain pens, Pokémon cards, watches, aquarium, knives, and miniatures (in posts) — and only two leave an opening: r/BoardGameExchange (fixed-price external listings allowed) and r/fragranceswap (inventory lists and order forms allowed). Several also require PayPal Goods & Services. Rule texts and dates are in section 5.

That closes Reddit's swap communities as a place to *post* a drop. What remains is Facebook groups and Discord servers (rules unknown, set group by group), links sent in private messages, and audiences the seller actually owns.

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

**The product is worth building as an experiment, not yet as a business.** The engineering is well understood and the cost of finding out is modest. But the PRD understates how good and how cheap the incumbent workflow is, and overstates how much audience the typical seller has. The fastest way to lose three months is to build the full MVP before learning whether a single target community will allow the link. The research already says the largest Reddit swap communities will not. Finding the communities that will — a few messages to Facebook group admins and Discord owners — should happen first.

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
2. The buyers are in the community, and most swap subreddits ban the link.
3. Buyers already trust PayPal's 180 days, and trade history does not carry over.
4. A sale post already is one link with many items.

From eBay:

1. eBay brings buyers, search, and sold-price history. HobbyDrop brings none; a seller without a following gets nothing for the fee.
2. eBay's guarantee and brand raise both conversion and achievable price.
3. Rare items do better at auction.

## 5. Launch niche

Seventeen niches were scored against the PRD's weighted criteria. **Method and limits:** member counts are from GummySearch (pages updated October–November 2026); posting rates are calculated from the latest 100 submissions per subreddit in a public Reddit archive on 2026-11-21; items per post and prices come from small samples (4–24 recent selling posts per subreddit). Facebook, Discord and Instagram community sizes could not be confirmed for any niche. Scores are judgements from that evidence; differences under about 0.3 are noise.

### Scores

Scale 1–5. Weights: activity 20%, resale frequency 20%, inventory depth 15%, transaction value 15%, shipping 10%, low fraud 10%, weak incumbent 10%.

| Niche | Main swap venue (members) | Act. | Freq. | Depth | Value | Ship | Low fraud | Weak inc. | **Total** | External sale links in the main venue |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Knives / EDC | r/Knife_Swap (123k) | 5 | 5 | 3 | 5 | 5 | 3 | 4 | **4.40** | Banned — and screened out: payment-provider risk |
| Fountain pens | r/Pen_Swap (88k) | 4 | 5 | 3 | 5 | 5 | 3 | 4 | **4.20** | Banned |
| Mechanical keyboards | r/mechmarket (307k) | 5 | 4 | 4 | 5 | 4 | 3 | 3 | **4.15** | Banned |
| **Miniatures / Warhammer** | r/Miniswap (77k) | 4 | 4 | 5 | 5 | 3 | 3 | 3 | **4.00** | Banned in posts; links by private message tolerated (dated rule) |
| Trading cards | r/pkmntcgtrades (92k) | 5 | 5 | 5 | 3 | 5 | 1 | 1 | 3.90 | Banned |
| Outdoor gear | r/GearTrade (139k) | 4 | 4 | 3 | 5 | 4 | 4 | 3 | 3.90 | Banned (from a summary, not a verbatim rule) |
| Fragrance | r/fragranceswap (139k) | 5 | 5 | 3 | 4 | 2 | 2 | 4 | 3.85 | Restricted — inventory lists and order forms allowed |
| Vinyl | r/VinylCollectors (170k) | 4 | 4 | 4 | 3 | 4 | 4 | 2 | 3.65 | Not found |
| Board games | r/BoardGameExchange (38k) | 3 | 3 | 5 | 4 | 1 | 5 | 4 | 3.55 | **Allowed** for fixed-price listings |
| Yarn / fabric | r/Yarnswap | 3 | 3 | 3 | 2 | 5 | 4 | 5 | 3.35 | Not found |
| Audio | r/AVexchange (77k) | 3 | 4 | 2 | 3 | 4 | 3 | 3 | 3.15 | Not found |
| LEGO | r/Legomarket (60k) | 3 | 3 | 3 | 4 | 3 | 3 | 2 | 3.05 | Not found |
| Watches | r/Watchexchange (578k) | 5 | 5 | 1 | 1 | 3 | 1 | 3 | 3.00 | Banned |
| **Cameras** | r/photomarket (121k) | 4 | 4 | 2 | 2 | 3 | 2 | 2 | 2.90 | Banned |
| Plants / aquarium | r/AquaSwap (123k) | 4 | 4 | 3 | 1 | 1 | 2 | 4 | 2.90 | Banned |
| Synths / music gear | r/Gear4Sale (29k) | 2 | 3 | 3 | 3 | 3 | 3 | 1 | 2.60 | Not found |
| **Cycling** (low confidence) | Pinkbike BuySell | 3 | 3 | 3 | 2 | 1 | 2 | 3 | 2.55 | Not found |

Two things stand out. The PRD's own examples — camera gear and cycling — score near the bottom: cameras sell one or two high-value items at a time into a community that bans the link, and bikes are hard to ship. And the best-scoring niches are exactly the ones with the strictest, best-run swap subreddits.

### The link rules found

| Community | Rule (date of the text found) |
|---|---|
| r/photomarket | "Only link to pictures hosted on imgur.com -- no links to other marketplace or personal sites." (sidebar copy, 2023 or earlier) |
| r/mechmarket | "Linking to your item on any other market or outlet is forbidden." (moderator quoting the rule, 2018) |
| r/Pen_Swap | "Do not link to stores, items, or users on any other website or forum (e.g., eBay, Etsy, Craigslist, FPN, FPG, Instagram, etc.)." (2020) |
| r/pkmntcgtrades | "No outside links, references, or advertising: This includes eBay, auction sites, other marketplaces/groups, and other social media." (2025) |
| r/Watchexchange | "Outside sales links and referral links are not allowed." (third-party summary, July 2026) |
| r/AquaSwap | "We do not allow posts that redirect users to another website." (2018; a 2026 comment confirms it stands) |
| r/Miniswap | "No Links to eBay Auctions, Facebook Marketplace, Vinted, Craigslist, Other Trading Sites, etc." (October 2025). A 2013 moderator FAQ: "Whatever you work out with others in PM is fine, IE linking them to buy from your eBay, Etsy, etc..." |
| r/BoardGameExchange | "Links to external marketplaces, such as eBay or Craigslist are allowed, but they must be exclusively 'buy-it-now' posts." (2024) |
| r/fragranceswap | No external links except photos, "detailed lists or inventories (e.g., Google Sheets…)" and "order forms" (2025) |

### Recommendation: miniatures / Warhammer — provisionally

It is not the top score. It is the best score among niches where there is evidence of somewhere to share a link.

- **The collection is already the unit of sale.** Sampled r/Miniswap posts list a median of 8 priced items or lots (up to 35), with whole armies sold as one lot for $45 to $5,000. This is the behaviour the product assumes, already happening.
- **Trading is spread across venues.** Players name Facebook buy/sell/trade groups alongside eBay and r/Miniswap. No single gated community controls the niche.
- **The incumbents are expensive.** eBay takes 13.6% + $0.40. The niche's own vertical marketplace, miniswap.gg, charges "7% commission on the item price + Stripe processing" — evidence that sellers in this niche will pay more than HobbyDrop proposes, and it points sellers of mixed lots back to eBay.
- **Baskets, not items, carry the economics.** The median item is about $30, where a 4% fee is $1.20 and fixed payment costs bite. The model works on multi-item orders and whole-army lots, and needs watching.

### The strongest argument against it

- **A direct vertical competitor already exists** in miniswap.gg, with a structured catalogue and eBay sync. Its ownership, scale, and any relationship to the subreddit are unverified.
- **The subreddit's rules still point the other way.** Its wiki says deals should happen "through Reddit, not someone's personal store", and the private-message allowance dates from 2013.
- **Facebook group sizes and rules are unverified** — and they are the channel this recommendation leans on.
- **Authenticity disputes are built in.** Recasts and 3D prints are a known problem; painted models are fragile in the post.

### What would change the pick

- Written permission from r/Pen_Swap moderators for a compliant flow would put **fountain pens** first: best fundamentals (about 55 selling posts a day, $132 median item, envelope shipping, no vertical marketplace found).
- If the founder already belongs to, or has standing in, any of these communities, that outweighs a half-point of score. Access to the first twenty sellers matters more than the table.
- **Board games** are the only niche where the main swap subreddit explicitly allows fixed-price external listings; shipping cost ("$12–$18 a game") is what holds the score down.

### Where to find the first 15–20 seller interviews

| Community | Note |
|---|---|
| r/Miniswap — https://www.reddit.com/r/Miniswap/ | Transaction posts only; a research post would likely be removed. Message sellers with 10+ item posts individually, and ask the moderators first |
| Warhammer 40K / AOS Buy Sell Trade USA / Canada (Facebook) — https://www.facebook.com/groups/284832079554329/ | Size and solicitation rules unverified; ask admins. This is also the first place to ask whether a drop link may be posted |
| American Warhammer / 40k Trade Sale Buy (Facebook) — https://www.facebook.com/groups/American.Warhammer/ | As above |
| City groups, e.g. Pittsburgh Warhammer 40K (Facebook) — https://www.facebook.com/groups/Pittsburgh40k/ | Members report selling there to avoid eBay |
| DakkaDakka Swap Shop — https://www.dakkadakka.com/dakkaforum/ | Long-standing traders, some with 100+ trades; solicitation rules unverified |
| eBay sellers of army lots | The fee-sensitive segment, reachable directly |
| **Do not post in:** r/Warhammer40k, Bolter & Chainsword | Both prohibit selling and promotion |

## Key sources

- Subreddit rules and niche data: r/mechmarket https://www.reddit.com/r/mechmarket/comments/36fw58/meta_rules_are_not_an_option/ · r/photomarket sidebar copy https://redditrebuilt.com/r/photomarket · r/Pen_Swap https://www.reddit.com/r/Pen_Swap/comments/ib9hna/wording_change_to_rule_c8_advertising_rule/ · r/Miniswap https://www.reddit.com/r/Miniswap/comments/1o8kgzh/how_to_miniswap_safety_tips_and_verification/ and https://www.reddit.com/r/Miniswap/comments/18ina2/rminiswap_faq/ · r/pkmntcgtrades https://www.reddit.com/r/pkmntcgtrades/comments/1iztvrc/updated_rules_guidelines_february_27_2025/ · r/BoardGameExchange https://www.reddit.com/r/BoardGameExchange/comments/1avdee5/new_to_the_sub_read_this_first/ · r/AquaSwap https://www.reddit.com/r/AquaSwap/comments/9ghqbp/rule_and_flair_changes/ · r/fragranceswap https://www.reddit.com/r/fragranceswap/comments/1kqe9ft/offsite_links/ · r/Knife_Swap https://www.reddit.com/r/Knife_Swap/comments/q5ibtj/meta_whats_with_paypal_and_knives/ · miniswap.gg fees https://miniswap.gg/help-center/blog/miniswap-vs-ebay
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
