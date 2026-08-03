# Palkay — E-Commerce Platform

> "Good taste shouldn't cost more."

A fully-featured Django e-commerce platform built with a premium editorial design. Cash-on-Delivery (COD) model, Austin TX market, Phase 1.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Django 4.2 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Auth | Custom UUID User model, Argon2 hashing |
| Static files | WhiteNoise + Django staticfiles |
| Media storage | Local (dev) / S3/DO Spaces (prod) |
| Web server | Gunicorn |
| Styling | Custom CSS (Fraunces + Sora fonts) |

---

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> palkay
cd palkay
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values (SECRET_KEY at minimum)
```

### 3. Database setup

```bash
python manage.py migrate
python manage.py seed_data       # Load categories, brands, 15 products, CMS pages
python manage.py createsuperuser # Create admin account
```

### 4. Run

```bash
python manage.py runserver
```

Visit: http://127.0.0.1:8000  
Admin: http://127.0.0.1:8000/admin/

---

## Project Structure

```
palkay/
├── palkay/               # Django project config
│   ├── settings.py       # All settings (env-var driven)
│   └── urls.py           # Root URL configuration
│
├── users/                # Custom User model + auth views
│   ├── models.py         # UUID User, email-based auth
│   ├── views.py          # Login, register, dashboard, profile
│   └── forms.py          # Registration with password validation
│
├── catalog/              # Products, categories, brands
│   ├── models.py         # Product, Category, Brand, Images, Variants
│   ├── views.py          # Product list/detail, category, brand, search
│   └── management/
│       └── commands/
│           └── seed_data.py   # Phase 1 seed data command
│
├── cart/                 # Shopping cart (user + guest sessions)
│   ├── models.py         # Cart, CartItem
│   ├── middleware.py     # Attaches cart to every request
│   └── views.py          # Add/update/remove, cart merge on login
│
├── orders/               # Checkout, COD orders, status tracking
│   ├── models.py         # Address, Order, OrderItem, StatusHistory
│   ├── views.py          # Checkout flow, order history, cancel
│   └── forms.py          # Address form, guest checkout form
│
├── pages/                # Homepage, CMS pages, contact, wishlist
│   ├── models.py         # Wishlist, ContactSubmission, Page
│   └── views.py          # Home, about, contact, CMS page renderer
│
├── templates/            # All HTML templates
│   ├── base.html         # Site layout (nav, footer, messages)
│   ├── partials/         # Reusable components
│   │   ├── product_card.html
│   │   └── account_sidebar.html
│   ├── pages/            # Home, about, contact, CMS
│   ├── catalog/          # Product list, detail, category, brand
│   ├── cart/             # Cart page
│   ├── orders/           # Checkout, confirmation, list, detail
│   └── users/            # Login, register, dashboard, profile
│
└── static/
    ├── css/palkay.css    # Full design system (Palkay tokens)
    └── js/main.js        # AJAX cart, wishlist, UI interactions
```

---

## Key Features

### 🛒 Cart
- Guest carts via Django sessions
- Registered user carts
- **Automatic cart merge** on login (quantities summed for duplicates)
- AJAX add-to-cart with live badge update

### 📦 Orders
- Full COD checkout flow (no payment gateway needed)
- Price snapshots on OrderItem (immutable after order creation)
- 2-hour self-cancellation window
- Atomic stock decrement at checkout (`select_for_update`)
- Full status history audit log
- Order confirmation email

### 👤 Accounts
- UUID primary keys (prevents enumeration)
- Argon2 password hashing
- Guest checkout (no account required)
- Wishlist, saved addresses, order history

### 🔐 RBAC
- **Admin**: full access
- **Employee**: can manage products and view orders (no customer PII)
- **Customer**: own orders/addresses/wishlist only
- **Guest**: browse + checkout

### 🛍 Catalog
- 6 root categories (Fashion, Home & Decor, Beauty, Pet Care, Medicine, Tools)
- Self-referential subcategories
- Product variants (size, color) with independent stock
- Soft-delete throughout (is_active flags)
- Full-text search, filtering, sorting, pagination

---

## Deployment (Railway / Heroku)

```bash
# Set production env vars:
SECRET_KEY=<long-random-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgres://...

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate
python manage.py seed_data
```

The `Procfile` is pre-configured for Gunicorn.

---

## Admin Notes

- Access Django Admin at `/admin/`
- Use **seed_data** management command to load sample data
- Product images: upload via Django Admin → Products → Images inline
- Employee accounts: create User, assign to **Employee** group
- CMS pages editable at Admin → Pages

---

## Phase 2 Roadmap (stub models ready)

- [ ] Blog / Content hub (BlogPost model stubbed)
- [ ] Product Reviews + AggregateRating
- [ ] Coupon / Discount codes
- [ ] Celery tasks (cart expiry, email queues)
- [ ] Search improvements (PostgreSQL full-text)
- [ ] Redis caching for catalogue pages
