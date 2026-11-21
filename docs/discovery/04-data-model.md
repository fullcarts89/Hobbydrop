# 04 — Data model

Status: **design draft for founder review** — not yet a migration. Postgres (Supabase).

## Conventions

- Primary keys are `uuid` (`gen_random_uuid()`), except `events` (`bigint identity`) and `stripe_events` (Stripe's own `evt_…` id).
- Money is integer cents in `integer` columns with a `_cents` suffix. Never floats. `currency` is `char(3)` and constrained to `'usd'` for the MVP.
- Every table has `created_at timestamptz not null default now()`; mutable tables also have `updated_at`.
- Enumerations are Postgres `enum` types; adding a value is a migration, which is the point.
- Row-level security is **enabled on every table with no policies** for the `anon` and `authenticated` roles. The browser never queries tables directly; all reads and writes go through server code, which authorizes in the service layer. RLS is the backstop that makes a leaked anon key harmless, not the primary authorization mechanism.

## Changes from the PRD's section 15

| PRD | This design | Why |
|---|---|---|
| `users.email` | Email stays in Supabase `auth.users`; `profiles` holds public fields only | One copy of PII; nothing public-facing can accidentally select it |
| `drops.status` = draft / scheduled / live / ended / archived | Stored: `draft`, `published`, `archived`, `suspended`. *Scheduled / live / ended* are derived from `starts_at` / `ends_at` at read time | Removes the need for a scheduler to flip statuses, and removes a class of "status says live but clock says ended" bugs |
| `items.quantity` | `quantity_total` + `quantity_sold`; availability is computed | Makes overselling a constraint violation rather than a logic bug |
| `orders.status` | `payment_status` + `fulfillment_status` | A refunded-after-shipping order is two facts, not one enum value |
| `inventory_reservations.checkout_reference` | FK to a new `checkouts` table | A checkout attempt is its own entity: it owns the cart snapshot and reservations, and becomes an order only if paid. Abandoned checkouts never appear in `orders` |
| Item-level `category` | Category on the drop only | One launch niche; item taxonomy is premature |
| `cover_image_url` | `cover_image_id` → `item_images` | The cover is one of the drop's own photos; no separate upload path |
| Notification preferences | Deferred with follow / drop alerts | MVP sends transactional email only, which needs no preference |

## Entities

### Identity

```sql
create type profile_status as enum ('active', 'restricted', 'suspended');

create table profiles (
  id            uuid primary key references auth.users (id) on delete cascade,
  username      citext not null unique
                check (username ~ '^[a-z0-9][a-z0-9_-]{2,29}$'),
  display_name  text   not null check (char_length(display_name) between 1 and 60),
  bio           text   check (char_length(bio) <= 280),
  avatar_key    text,
  links         jsonb  not null default '[]',   -- [{label, url}], validated server-side, https only
  status        profile_status not null default 'active',
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

create table user_roles (                       -- admin is a row here, never a client-editable flag
  user_id    uuid not null references profiles (id) on delete cascade,
  role       text not null check (role in ('admin')),
  granted_by uuid references profiles (id),
  created_at timestamptz not null default now(),
  primary key (user_id, role)
);

create table seller_accounts (
  user_id            uuid primary key references profiles (id) on delete restrict,
  stripe_account_id  text not null unique,
  details_submitted  boolean not null default false,
  charges_enabled    boolean not null default false,
  payouts_enabled    boolean not null default false,
  requirements_due   jsonb   not null default '[]',
  disabled_reason    text,
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now()
);
```

`seller_accounts` mirrors Stripe's `account.updated` webhook. "Can this seller publish?" is `charges_enabled and payouts_enabled`, read from here, never from a client claim. Reserved usernames (`admin`, `api`, `u`, `checkout`, `orders`, …) are rejected by the service layer from a static list.

### Catalog

```sql
create type drop_status    as enum ('draft', 'published', 'archived', 'suspended');
create type item_condition as enum ('new', 'like_new', 'good', 'fair', 'for_parts');
create type item_status    as enum ('active', 'hidden', 'removed');

create table categories (
  id     uuid primary key default gen_random_uuid(),
  slug   text not null unique,
  name   text not null,
  active boolean not null default true
);

create table drops (
  id            uuid primary key default gen_random_uuid(),
  seller_id     uuid not null references profiles (id) on delete restrict,
  category_id   uuid not null references categories (id),
  title         text not null check (char_length(title) between 3 and 80),
  description   text check (char_length(description) <= 2000),
  slug          text not null check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  cover_image_id uuid,                               -- FK added after item_images exists
  status        drop_status not null default 'draft',
  starts_at     timestamptz,                         -- null until published
  ends_at       timestamptz,                         -- null = open-ended
  shipping_first_cents      integer not null default 0 check (shipping_first_cents between 0 and 20000),
  shipping_additional_cents integer not null default 0 check (shipping_additional_cents between 0 and 20000),
  published_at  timestamptz,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (seller_id, slug),
  unique (id, seller_id),                            -- target for the composite FK from items
  check (ends_at is null or starts_at is null or ends_at > starts_at),
  check (status = 'draft' or starts_at is not null)
);
create index drops_seller_idx on drops (seller_id, status);

create table items (
  id             uuid primary key default gen_random_uuid(),
  drop_id        uuid not null,
  seller_id      uuid not null,
  title          text not null check (char_length(title) between 2 and 100),
  description    text check (char_length(description) <= 2000),
  price_cents    integer not null check (price_cents between 100 and 500000),   -- $1 – $5,000 pilot cap
  currency       char(3) not null default 'usd' check (currency = 'usd'),
  quantity_total integer not null default 1 check (quantity_total between 0 and 999),
  quantity_sold  integer not null default 0 check (quantity_sold >= 0),
  condition      item_condition not null,
  status         item_status not null default 'active',
  sort_order     integer not null default 0,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now(),
  foreign key (drop_id, seller_id) references drops (id, seller_id) on delete restrict,
  check (quantity_sold <= quantity_total)            -- the last line of defence against overselling
);
create index items_drop_idx on items (drop_id, sort_order);

create table item_images (
  id          uuid primary key default gen_random_uuid(),
  item_id     uuid not null references items (id) on delete cascade,
  storage_key text not null unique,                  -- server-generated; never a client-supplied path
  width       integer not null,
  height      integer not null,
  sort_order  integer not null default 0,
  created_at  timestamptz not null default now()
);
create index item_images_item_idx on item_images (item_id, sort_order);
```

- The slug is fixed once a drop is first published, so shared links never break.
- The composite foreign key on `items (drop_id, seller_id)` makes it structurally impossible for an item to claim a seller who does not own its drop.
- Items with any order history are never hard-deleted (`status = 'removed'`); `order_items.item_snapshot` preserves what the buyer actually saw.

### Checkout and inventory

```sql
create type checkout_status    as enum ('open', 'completed', 'expired');
create type reservation_status as enum ('active', 'consumed', 'released');

create table checkouts (
  id                 uuid primary key default gen_random_uuid(),
  drop_id            uuid not null references drops (id),
  seller_id          uuid not null references profiles (id),
  stripe_session_id  text unique,                    -- set once the Stripe session exists
  status             checkout_status not null default 'open',
  subtotal_cents     integer not null,
  shipping_cents     integer not null,
  fee_bps            integer not null,               -- fee rate snapshotted at checkout time
  platform_fee_cents integer not null,
  expires_at         timestamptz not null,
  anonymous_id       text,
  buyer_id           uuid references profiles (id),
  attribution        jsonb not null default '{}',    -- utm_*, ref, referrer host
  created_at         timestamptz not null default now()
);

create table checkout_items (
  checkout_id      uuid not null references checkouts (id) on delete cascade,
  item_id          uuid not null references items (id),
  quantity         integer not null check (quantity > 0),
  unit_price_cents integer not null,                 -- price at the moment of reservation
  primary key (checkout_id, item_id)
);

create table inventory_reservations (
  id          uuid primary key default gen_random_uuid(),
  item_id     uuid not null references items (id),
  checkout_id uuid not null references checkouts (id) on delete cascade,
  quantity    integer not null check (quantity > 0),
  expires_at  timestamptz not null,
  status      reservation_status not null default 'active',
  created_at  timestamptz not null default now(),
  unique (checkout_id, item_id)
);
create index reservations_active_idx on inventory_reservations (item_id) where status = 'active';
```

**Availability** of an item is always computed, never stored:

```
available = quantity_total − quantity_sold − Σ quantity of reservations
            where status = 'active' and expires_at > now()
```

**Reservation semantics** (the part that must be right):

1. *Reserve* — one transaction: `select … from items where id = any($ids) order by id for update` (ordered locking, so two carts with overlapping items cannot deadlock); verify the drop is live, the seller can accept charges, each item is `active` and `available >= requested`; insert `checkouts`, `checkout_items`, `inventory_reservations`. If any line fails the whole transaction rolls back and the buyer is told which item went. Only after commit is the Stripe Checkout Session created, with its `expires_at` matching ours; if Stripe session creation fails, the reservation is released immediately.
2. *Expiry is lazy* — an expired reservation simply stops counting in the availability formula. No timer has to fire for stock to come back. `checkout.session.expired` and a periodic sweep only tidy `status` to `released`.
3. *Grace window* — the reservation's `expires_at` is set a few minutes later than the Stripe session's, so a payment that completes in the session's last second still finds its stock held.
4. *Consume* — on `checkout.session.completed`, one transaction: dedupe the event, lock the items, flip reservations to `consumed`, increment `quantity_sold`, insert `orders` / `order_items` / `payments`, enqueue emails. `orders.checkout_id` is unique, so a retried or duplicated webhook cannot create a second order.
5. *Impossible-but-handled* — if consume finds the reservation already released and the stock gone (webhook delayed past the grace window), the `quantity_sold <= quantity_total` check fails, the handler refunds the payment in full, records the order as refunded with reason `oversold`, and alerts an admin. The buyer is never left paid-without-item silently.
6. *Seller edits during checkout* — price changes do not affect open checkouts (the price is snapshotted in `checkout_items` and in the Stripe line items). `quantity_total` cannot be lowered below `quantity_sold + active reservations`. Removing an item or unpublishing a drop hides it from new buyers but lets in-flight checkouts finish.
7. *Carts do not reserve.* The cart is client-side state; stock is held only from "Checkout" onward. Abuse controls (per-client cap on concurrent open checkouts, rate limiting) sit on the reserve endpoint.

### Orders, payments, fulfillment

```sql
create type payment_status     as enum ('paid', 'partially_refunded', 'refunded', 'disputed');
create type fulfillment_status as enum ('unfulfilled', 'shipped', 'delivered', 'cancelled');

create table orders (
  id                 uuid primary key default gen_random_uuid(),
  number             bigint generated always as identity unique,   -- human-facing "HD-10042"
  checkout_id        uuid not null unique references checkouts (id),
  drop_id            uuid not null references drops (id),
  seller_id          uuid not null references profiles (id),
  buyer_id           uuid references profiles (id),                -- null for guests
  buyer_email        citext not null,
  payment_status     payment_status not null default 'paid',
  fulfillment_status fulfillment_status not null default 'unfulfilled',
  subtotal_cents     integer not null check (subtotal_cents >= 0),
  shipping_cents     integer not null check (shipping_cents >= 0),
  tax_cents          integer not null default 0 check (tax_cents >= 0),
  fee_bps            integer not null,
  platform_fee_cents integer not null check (platform_fee_cents >= 0),
  total_cents        integer not null,
  currency           char(3) not null default 'usd',
  ship_to            jsonb,                                         -- name + address; redacted on schedule
  ship_by            timestamptz not null,
  access_token_hash  bytea not null,                                -- guest order link; raw token only ever in the email
  attribution        jsonb not null default '{}',
  created_at         timestamptz not null default now(),
  updated_at         timestamptz not null default now(),
  check (total_cents = subtotal_cents + shipping_cents + tax_cents)
);
create index orders_seller_idx on orders (seller_id, created_at desc);
create index orders_buyer_email_idx on orders (buyer_email);

create table order_items (
  id               uuid primary key default gen_random_uuid(),
  order_id         uuid not null references orders (id) on delete restrict,
  item_id          uuid not null references items (id) on delete restrict,
  quantity         integer not null check (quantity > 0),
  unit_price_cents integer not null,
  item_snapshot    jsonb not null            -- title, condition, description, primary image key at purchase
);

create table payments (
  id                       uuid primary key default gen_random_uuid(),
  order_id                 uuid not null references orders (id) on delete restrict,
  stripe_payment_intent_id text not null unique,
  stripe_charge_id         text unique,
  stripe_transfer_id       text unique,      -- seller's share, if transfers are created separately
  status                   text not null,
  amount_cents             integer not null,
  currency                 char(3) not null default 'usd',
  created_at               timestamptz not null default now()
);

create table refunds (
  id               uuid primary key default gen_random_uuid(),
  order_id         uuid not null references orders (id) on delete restrict,
  stripe_refund_id text not null unique,
  amount_cents     integer not null check (amount_cents > 0),
  reason           text not null,            -- seller_cancelled | not_shipped | not_as_described | oversold | goodwill | …
  initiated_by     uuid references profiles (id),
  restocked        boolean not null default false,
  created_at       timestamptz not null default now()
);

create table disputes (
  id                uuid primary key default gen_random_uuid(),
  order_id          uuid not null references orders (id) on delete restrict,
  stripe_dispute_id text not null unique,
  status            text not null,
  reason            text,
  amount_cents      integer not null,
  evidence_due_by   timestamptz,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);

create table shipments (
  id              uuid primary key default gen_random_uuid(),
  order_id        uuid not null references orders (id) on delete restrict,
  carrier         text not null,
  tracking_number text not null,
  shipped_at      timestamptz not null default now(),
  delivered_at    timestamptz,
  created_at      timestamptz not null default now()
);
```

Fee arithmetic is a single pure function: `platform_fee_cents = round_half_up(subtotal_cents × fee_bps / 10000)`, computed on the item subtotal only (not shipping), with `fee_bps` stored on the order so a later rate change never rewrites history.

### Operations

```sql
create table stripe_events (                 -- webhook dedupe + audit trail
  id           text primary key,             -- Stripe's evt_… id
  type         text not null,
  payload      jsonb not null,
  received_at  timestamptz not null default now(),
  processed_at timestamptz
);

create table email_outbox (                  -- written in the same transaction as the state change
  id         uuid primary key default gen_random_uuid(),
  dedupe_key text not null unique,           -- e.g. 'order_confirmation:<order_id>'
  template   text not null,
  recipient  citext not null,
  payload    jsonb not null,
  status     text not null default 'pending',
  attempts   integer not null default 0,
  sent_at    timestamptz,
  created_at timestamptz not null default now()
);

create table reports (
  id             uuid primary key default gen_random_uuid(),
  target_type    text not null check (target_type in ('drop', 'item', 'profile', 'order')),
  target_id      uuid not null,
  reporter_id    uuid references profiles (id),
  reporter_email citext,
  reason         text not null,
  details        text check (char_length(details) <= 2000),
  status         text not null default 'open',
  resolved_by    uuid references profiles (id),
  resolved_at    timestamptz,
  created_at     timestamptz not null default now()
);

create table admin_actions (                 -- append-only: no update or delete grants, even for the app role
  id          uuid primary key default gen_random_uuid(),
  admin_id    uuid not null references profiles (id),
  action      text not null,
  target_type text not null,
  target_id   uuid,
  reason      text not null,
  metadata    jsonb not null default '{}',
  created_at  timestamptz not null default now()
);

create table events (                        -- first-party funnel analytics
  id           bigint generated always as identity primary key,
  event_type   text not null,
  user_id      uuid,
  anonymous_id text,
  drop_id      uuid,
  item_id      uuid,
  order_id     uuid,
  metadata     jsonb not null default '{}',
  created_at   timestamptz not null default now()
);
create index events_drop_idx on events (drop_id, event_type, created_at);
create index events_type_idx on events (event_type, created_at);
```

`events` deliberately has no foreign keys: analytics writes must never fail or block a transaction, and rows outlive the things they describe.

## Access control summary

| Data | Public | Owner (seller) | Buyer (order token or account) | Admin |
|---|---|---|---|---|
| Profile public fields, published drops, active items, images | read | read / write own | read | read / suspend |
| Draft drops, hidden items | — | read / write own | — | read |
| `seller_accounts` | — | read own status only | — | read |
| Orders, shipments | — | read own sales; write fulfillment | read own order | read |
| Buyer shipping address | — | read for own unfulfilled / recently shipped orders | read own | read (logged) |
| Refunds | — | initiate on own orders | read own | initiate |
| `stripe_events`, `email_outbox`, `admin_actions`, `events` | — | — | — | read |

Every row above is enforced in the server service layer by an explicit guard (`requireSellerOf(order)`, `requireAdmin()`); no route handler touches the database without going through one.

## Retention

| Data | Retention | Note |
|---|---|---|
| Order financial fields, payments, refunds, disputes | 7 years | Tax and accounting records; confirm period with an accountant |
| `orders.ship_to` | Redacted 180 days after delivery or refund | Outlasts the card dispute window, then no reason to keep a home address |
| `buyer_email` on orders | Kept with the order | Needed for the order record and support |
| Deleted accounts | Profile anonymized, username released after 90 days, auth user deleted; orders retained with the seller reference pointing at the anonymized profile | Financial records survive account deletion |
| `stripe_events.payload` | 13 months | Reconciliation window |
| `events` | 25 months, then aggregate | |
| Raw uploaded images | Deleted once derivatives are written | Only re-encoded, EXIF-stripped derivatives are stored |
| Images of removed items with no orders | Deleted with the item | |
