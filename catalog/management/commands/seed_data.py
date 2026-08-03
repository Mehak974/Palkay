# -*- coding: utf-8 -*-
"""
Management command to seed Palkay with Phase 1 data.
Usage: python manage.py seed_data
       python manage.py seed_data --flush  (wipe and re-seed)
"""
import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.utils.text import slugify


class Command(BaseCommand):
    help = 'Seed Palkay Phase 1 data: categories, brands, products, CMS pages, employee group'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete existing data before seeding')

    def handle(self, *args, **options):
        from catalog.models import Category, Brand, Product, AttributeType, AttributeValue
        from pages.models import Page

        if options['flush']:
            self.stdout.write('Flushing existing data...')
            Product.objects.all().delete()
            Category.objects.all().delete()
            Brand.objects.all().delete()
            Page.objects.all().delete()
            self.stdout.write(self.style.WARNING('Data flushed.'))

        # -- Categories ----------------------------------------------
        self.stdout.write('Creating categories...')
        cat_data = [
            ('Fashion', '\U0001F455', 0),
            ('Home & Decor', '\U0001F3E0', 1),
            ('Beauty & Cosmetics', '\U0001F484', 2),
            ('Pet Care', '\U0001F43E', 3),
            ('Medicine & Supplements', '\U0001F48A', 4),
            ('Tools', '\U0001F527', 5),
        ]
        categories = {}
        for name, icon, order in cat_data:
            cat, created = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    'name': name,
                    'sort_order': order,
                    'description': f'Browse our curated {name.lower()} selection.',
                    'seo_meta_title': f'{name} | Palkay',
                    'seo_meta_description': f'Shop quality {name.lower()} at Palkay. Vetted products, honest prices.',
                }
            )
            categories[name] = cat
            if created:
                self.stdout.write(f'  Created category: {name}')

        # Kitchen as subcategory of Home & Decor
        kitchen, _ = Category.objects.get_or_create(
            slug='kitchen',
            defaults={
                'name': 'Kitchen',
                'parent': categories['Home & Decor'],
                'sort_order': 0,
                'description': 'Quality kitchen tools and cookware.',
            }
        )
        categories['Kitchen'] = kitchen

        # -- Brands --------------------------------------------------
        self.stdout.write('Creating brands...')
        brand_data = [
            ('Bexley', 'Premium fashion and lifestyle brand.'),
            ("Nature's Blend", 'Organic supplements and wellness products.'),
            ('LYNX', 'Modern tools and home improvement essentials.'),
            ('Alexander Handcraft Mills', 'Artisan home goods and decor.'),
            ('Med-Q', 'Trusted medicines and health supplements.'),
        ]
        brands = {}
        for name, desc in brand_data:
            brand, created = Brand.objects.get_or_create(
                slug=slugify(name),
                defaults={'name': name, 'description': desc}
            )
            brands[name] = brand
            if created:
                self.stdout.write(f'  Created brand: {name}')

        # -- Attribute Types ----------------------------------------─
        size_type, _ = AttributeType.objects.get_or_create(name='Size', defaults={'slug': 'size'})
        color_type, _ = AttributeType.objects.get_or_create(name='Color', defaults={'slug': 'color'})

        size_values = {}
        for i, size in enumerate(['XS', 'S', 'M', 'L', 'XL', 'XXL']):
            av, _ = AttributeValue.objects.get_or_create(
                attribute_type=size_type, value=size,
                defaults={'sort_order': i}
            )
            size_values[size] = av

        color_values = {}
        for i, color in enumerate(['Black', 'White', 'Navy', 'Beige', 'Olive']):
            av, _ = AttributeValue.objects.get_or_create(
                attribute_type=color_type, value=color,
                defaults={'sort_order': i}
            )
            color_values[color] = av

        # -- Products ------------------------------------------------─
        self.stdout.write('Creating products...')
        products_data = [
            # Fashion
            {
                'sku': 'BEX-001', 'name': 'Classic Oxford Shirt', 'category': 'Fashion',
                'brand': 'Bexley', 'price': '49.99', 'compare_at_price': '69.99',
                'stock': 150, 'featured': True,
                'description': 'A timeless Oxford shirt crafted from 100% premium cotton. The structured weave offers a distinctive texture while maintaining breathability throughout the day. Available in multiple colors, this versatile piece transitions effortlessly from casual to smart-casual settings. Features a button-down collar, single chest pocket, and adjustable cuffs. Machine washable for everyday convenience. Cut with a relaxed but tailored silhouette that flatters all body types without compromising on comfort or mobility.',
            },
            {
                'sku': 'BEX-002', 'name': 'Merino Wool Crew Sweater', 'category': 'Fashion',
                'brand': 'Bexley', 'price': '79.99', 'compare_at_price': '110.00',
                'stock': 80, 'featured': False,
                'description': 'Luxuriously soft merino wool sweater for year-round comfort. Our merino sweater is knitted from extra-fine 18.5 micron wool, making it exceptionally soft against the skin - even for those with sensitivity to wool. The natural fibers regulate temperature beautifully, keeping you warm in winter and surprisingly comfortable on cool spring evenings. A classic crew neck with ribbed cuffs and hem ensures a clean, refined look that works with everything from jeans to chinos. Hand wash recommended to preserve the natural lustre.',
            },
            {
                'sku': 'BEX-003', 'name': 'Slim Fit Chino Trousers', 'category': 'Fashion',
                'brand': 'Bexley', 'price': '59.99', 'compare_at_price': None,
                'stock': 200, 'featured': False,
                'description': 'Versatile slim-fit chinos made from a stretch-cotton blend for all-day comfort. These chinos are engineered for movement - a subtle 2% elastane content means they move with you without losing their shape. The fabric has been garment-washed for a soft, lived-in feel straight out of the box. Features include a mid-rise waist, two side slash pockets, two rear button-through pockets, and a clean zip fly. Available in five seasonal colorways, these are the workhorse trouser in any wardrobe.',
            },

            # Home & Decor
            {
                'sku': 'AHM-001', 'name': 'Hand-Woven Jute Rug 5×8', 'category': 'Home & Decor',
                'brand': 'Alexander Handcraft Mills', 'price': '129.99', 'compare_at_price': '179.99',
                'stock': 40, 'featured': True,
                'description': 'Artisan hand-woven jute rug that brings natural warmth and texture to any room. Each rug is individually woven by skilled artisans using sustainably sourced jute fibers, meaning no two are exactly alike. The natural golden-beige tones complement a wide range of interior styles from coastal to contemporary farmhouse. The flat weave construction makes it easy to clean - simply vacuum regularly and spot clean with mild soap. Rug pad recommended for non-carpet surfaces. Dimensions: 5 feet × 8 feet. Weight: approximately 12 lbs.',
            },
            {
                'sku': 'AHM-002', 'name': 'Ceramic Pour-Over Coffee Set', 'category': 'Kitchen',
                'brand': 'Alexander Handcraft Mills', 'price': '54.99', 'compare_at_price': '74.99',
                'stock': 60, 'featured': True,
                'description': 'Handcrafted ceramic pour-over set for the discerning coffee enthusiast. This three-piece set includes a pour-over dripper, a 600ml carafe, and a matching ceramic mug - all made from high-fire stoneware with a speckled matte glaze. The dripper features an optimised cone shape and single large hole for full control over your extraction. The thick ceramic walls retain heat beautifully while the ergonomic handle stays cool to the touch. Dishwasher safe. Set makes one to two cups. A considered gift for anyone serious about their morning ritual.',
            },
            {
                'sku': 'AHM-003', 'name': 'Ceramic Non-Stick Pan Set (3pc)', 'category': 'Kitchen',
                'brand': 'Alexander Handcraft Mills', 'price': '89.99', 'compare_at_price': '119.99',
                'stock': 45, 'featured': False,
                'description': 'Professional-grade ceramic non-stick pan set for everyday cooking. This three-piece set includes 8", 10", and 12" frying pans coated with a PFOA-free ceramic surface that releases food effortlessly without excess oil. The heavy-gauge aluminium base ensures rapid, even heat distribution across the entire cooking surface. The pans are induction compatible and oven safe to 450°F. Soft-touch handles stay cool on the stovetop. The ceramic coating is exceptionally durable - resistant to scratching, chipping, and metallic utensils. Hand wash recommended to extend coating life.',
            },

            # Beauty & Cosmetics
            {
                'sku': 'VIT-001', 'name': 'Vitamin C Glow Serum 30ml', 'category': 'Beauty & Cosmetics',
                'brand': None, 'price': '34.99', 'compare_at_price': '44.99',
                'stock': 120, 'featured': True,
                'description': 'Brightening Vitamin C serum with 15% L-Ascorbic Acid for visible radiance in 4 weeks. Our stable Vitamin C formulation is buffered with hyaluronic acid and vitamin E for maximum efficacy and minimal irritation. The lightweight gel texture absorbs instantly without a greasy residue. Regular use visibly diminishes dark spots, evens skin tone, and boosts collagen production for firmer-looking skin. Suitable for all skin types including sensitive skin. Fragrance-free, paraben-free, tested by dermatologists. Apply 3-4 drops to clean skin each morning before SPF.',
            },
            {
                'sku': 'VIT-002', 'name': 'Hyaluronic Acid Moisturiser 50ml', 'category': 'Beauty & Cosmetics',
                'brand': None, 'price': '28.99', 'compare_at_price': None,
                'stock': 90, 'featured': False,
                'description': 'Deeply hydrating moisturiser with triple-weight hyaluronic acid for 72-hour moisture retention. This gel-cream hybrid uses three molecular weights of hyaluronic acid to hydrate at different skin depths - from the surface layer all the way to the dermis. The result is plumper, more supple skin that holds moisture throughout the day and overnight. The formula also includes niacinamide for pore-minimising benefits and panthenol to soothe any redness or irritation. Non-comedogenic and suitable for oily skin types. Can be used morning and evening.',
            },
            {
                'sku': 'VIT-003', 'name': 'SPF 50+ Daily Sunscreen 60ml', 'category': 'Beauty & Cosmetics',
                'brand': None, 'price': '22.99', 'compare_at_price': '29.99',
                'stock': 200, 'featured': False,
                'description': 'Lightweight broad-spectrum SPF 50+ sunscreen that wears like a moisturiser. This is the sunscreen that finally makes daily SPF a pleasure rather than a chore. The fluid formula absorbs in seconds with no white cast, no greasy film, and no flashback in photographs. Broad-spectrum protection covers UVA, UVB, and visible light. Water resistant for 80 minutes. Suitable for all skin tones and sensitive skin types. Fragrance-free and reef-safe. Apply generously as the last step of your morning skincare routine. Reapply every two hours when outdoors.',
            },

            # Pet Care
            {
                'sku': 'PET-001', 'name': 'Premium Grain-Free Dog Food 5kg', 'category': 'Pet Care',
                'brand': None, 'price': '42.99', 'compare_at_price': '54.99',
                'stock': 75, 'featured': False,
                'description': 'High-protein grain-free dog food formulated for optimal canine health and energy. Made with real deboned chicken as the first ingredient, this recipe is packed with 32% protein to support lean muscle mass and healthy weight maintenance. Completely free from corn, wheat, soy, and artificial preservatives. Enriched with omega fatty acids from salmon oil for a glossy coat, plus glucosamine and chondroitin to support joint health in active dogs. Suitable for adult dogs of all breeds. Highly digestible formula means less waste and fewer stomach upsets. 5kg bag.',
            },
            {
                'sku': 'PET-002', 'name': 'Orthopedic Dog Bed - Large', 'category': 'Pet Care',
                'brand': None, 'price': '69.99', 'compare_at_price': '89.99',
                'stock': 35, 'featured': False,
                'description': 'Veterinarian-recommended orthopedic dog bed with memory foam base for joint support. This premium dog bed features a 4-inch memory foam core that conforms to your dog\'s body, relieving pressure on joints and hips - especially beneficial for senior dogs or breeds prone to arthritis. The plush bolster sides provide a sense of security and a comfortable place to rest their head. The cover is crafted from a durable water-resistant canvas that zips off completely for machine washing. Non-slip base keeps the bed in place on hard floors. Large size fits dogs up to 70 lbs.',
            },

            # Medicine & Supplements
            {
                'sku': 'NB-001', 'name': "Omega-3 Fish Oil 1000mg (90 caps)", 'category': 'Medicine & Supplements',
                'brand': "Nature's Blend", 'price': '24.99', 'compare_at_price': '34.99',
                'stock': 180, 'featured': False,
                'description': "Pharmaceutical-grade Omega-3 fish oil with high EPA and DHA concentrations for heart and brain health. Nature's Blend sources its fish oil from sustainably caught wild Alaskan pollock, then purifies it through a molecular distillation process to remove heavy metals, PCBs, and other contaminants. Each softgel delivers 1000mg of fish oil containing 180mg EPA and 120mg DHA - the two essential fatty acids your body cannot produce on its own. Benefits include cardiovascular support, reduced inflammation, improved cognitive function, and joint mobility. No fishy burps thanks to our enteric-coated softgels. Third-party tested.",
            },
            {
                'sku': 'NB-002', 'name': 'Vitamin D3 + K2 Supplement (60 caps)', 'category': 'Medicine & Supplements',
                'brand': "Nature's Blend", 'price': '19.99', 'compare_at_price': None,
                'stock': 220, 'featured': False,
                'description': "Synergistic Vitamin D3 and K2 formula for optimal bone density and immune function. Most Vitamin D supplements miss a crucial partner: Vitamin K2 (MK-7 form). Without K2, calcium absorbed through Vitamin D can accumulate in arteries rather than bones. Our formula combines 5000 IU Vitamin D3 with 100mcg Vitamin K2 to direct calcium to where it belongs. This combination is particularly beneficial for those with limited sun exposure, vegans, and adults over 50. Each capsule is made from organic olive oil to improve absorption of these fat-soluble vitamins. No artificial colours, flavours, or preservatives.",
            },

            # Tools
            {
                'sku': 'LYX-001', 'name': '18V Cordless Drill Set', 'category': 'Tools',
                'brand': 'LYNX', 'price': '89.99', 'compare_at_price': '119.99',
                'stock': 55, 'featured': True,
                'description': 'Professional 18V cordless drill/driver set with two batteries and 30 accessories. The LYNX 18V platform delivers 500 in-lbs of torque across 20 adjustable clutch settings, making it suitable for everything from delicate furniture assembly to heavy-duty renovation work. The brushless motor extends battery life significantly over traditional motors. Includes two 2.0Ah lithium-ion batteries with remaining charge indicators, a fast 45-minute charger, and a 30-piece accessory kit covering drill bits, screwdriver bits, and sockets. The ergonomic grip reduces fatigue during extended use. LED work light illuminates the drill zone.',
            },
            {
                'sku': 'LYX-002', 'name': 'Precision Hand Tool Set (42pc)', 'category': 'Tools',
                'brand': 'LYNX', 'price': '49.99', 'compare_at_price': '64.99',
                'stock': 90, 'featured': False,
                'description': 'Comprehensive 42-piece precision hand tool set for home repairs and DIY projects. Built to last a lifetime, the LYNX Precision Set contains chrome-vanadium steel tools that resist corrosion and maintain their edge through years of use. The set includes: claw hammer, tape measure, spirit level, 6-piece screwdriver set (flat and Phillips), adjustable wrench, pliers set (needle-nose, slip-joint, locking), utility knife, hex key set, and a selection of sockets and wrenches. Everything organises into the included blow-moulded case with custom foam inserts so every piece has its place.',
            },
        ]

        created_count = 0
        for pd in products_data:
            cat = categories.get(pd['category'])
            if not cat:
                continue
            brand_obj = brands.get(pd['brand']) if pd.get('brand') else None

            _, created = Product.objects.get_or_create(
                sku=pd['sku'],
                defaults={
                    'name': pd['name'],
                    'slug': slugify(pd['name']),
                    'category': cat,
                    'brand': brand_obj,
                    'price': pd['price'],
                    'compare_at_price': pd.get('compare_at_price'),
                    'stock_quantity': pd['stock'],
                    'is_featured': pd.get('featured', False),
                    'is_active': True,
                    'description': pd['description'],
                }
            )
            if created:
                created_count += 1

        self.stdout.write(f'  Created {created_count} products.')

        # -- CMS Pages ----------------------------------------------─
        self.stdout.write('Creating CMS pages...')
        pages_data = [
            {
                'title': 'Privacy Policy',
                'slug': 'privacy-policy',
                'content': '''<h2>Privacy Policy</h2>
<p>Last updated: January 1, 2026</p>
<p>Palkay ("we", "us", or "our") is committed to protecting your personal information. This Privacy Policy explains how we collect, use, and safeguard your data when you use our website.</p>
<h3>Information We Collect</h3>
<p>We collect information you provide directly: name, email address, phone number, delivery address, and order details. We also collect anonymous browsing data to improve the site experience.</p>
<h3>How We Use It</h3>
<p>We use your information to process orders, send order confirmations, provide customer support, and occasionally inform you of new products or promotions (you may opt out at any time).</p>
<h3>Data Security</h3>
<p>We use industry-standard encryption and never store payment card data. All passwords are hashed with Argon2. We do not sell your personal data to third parties.</p>
<h3>Contact</h3>
<p>For privacy questions, email privacy@palkay.com.</p>''',
            },
            {
                'title': 'Terms of Service',
                'slug': 'terms-of-service',
                'content': '''<h2>Terms of Service</h2>
<p>Last updated: January 1, 2026</p>
<p>By using Palkay, you agree to these terms. Please read them carefully.</p>
<h3>Orders & Payment</h3>
<p>All orders are subject to product availability. We accept Cash on Delivery (COD) as the payment method. Orders are confirmed once our team processes them, typically within a few hours.</p>
<h3>Delivery</h3>
<p>We deliver within the Austin, TX metro area. Delivery windows are estimates and may vary. We are not liable for delays caused by circumstances outside our control.</p>
<h3>Returns</h3>
<p>You may return unused items in original packaging within 7 days of delivery. Contact support@palkay.com to initiate a return.</p>
<h3>Limitation of Liability</h3>
<p>Palkay shall not be liable for indirect, incidental, or consequential damages. Our liability is limited to the value of the order in question.</p>''',
            },
            {
                'title': 'Returns Policy',
                'slug': 'returns-policy',
                'content': '''<h2>Returns &amp; Refunds Policy</h2>
<p>We want you to love what you ordered. If something isn't right, we make it easy to return.</p>
<h3>7-Day Returns</h3>
<p>Return any item within 7 days of delivery - no questions asked. Items must be in original, unused condition with all packaging intact.</p>
<h3>How to Return</h3>
<ol>
<li>Email support@palkay.com with your order number and the items you'd like to return.</li>
<li>We'll arrange a pickup or provide a return label within 24 hours.</li>
<li>Once received and inspected, your refund will be processed within 3-5 business days.</li>
</ol>
<h3>Non-Returnable Items</h3>
<p>For hygiene reasons, opened beauty products, food items, and medicines cannot be returned unless they are defective.</p>''',
            },
            {
                'title': 'FAQ',
                'slug': 'faq',
                'content': '''<h2>Frequently Asked Questions</h2>
<h3>How does Cash on Delivery work?</h3>
<p>You pay in cash when your order is delivered to your door. No card or online payment is required. Please have the exact amount ready if possible.</p>
<h3>What areas do you deliver to?</h3>
<p>We currently deliver across the Austin, TX metro area. Enter your ZIP code at checkout to confirm availability.</p>
<h3>How long does delivery take?</h3>
<p>Most orders are dispatched within 24 hours and arrive within 2-4 business days.</p>
<h3>Can I change or cancel my order?</h3>
<p>You can cancel your order within 2 hours of placement from your account dashboard. After that window, please contact support.</p>
<h3>Are your products authentic?</h3>
<p>Every product on Palkay is sourced directly from manufacturers or authorised distributors. We do not list grey-market or counterfeit goods.</p>
<h3>How do I track my order?</h3>
<p>Log in to your account and visit "My Orders" to see real-time status updates for all your orders.</p>''',
            },
        ]

        for pd in pages_data:
            Page.objects.get_or_create(
                slug=pd['slug'],
                defaults={'title': pd['title'], 'content': pd['content']}
            )
            self.stdout.write(f'  Page: {pd["title"]}')

        # -- Employee Group ------------------------------------------─
        self.stdout.write('Setting up Employee group...')
        employee_group, _ = Group.objects.get_or_create(name='Employee')
        perms = Permission.objects.filter(
            codename__in=[
                'add_product', 'change_product', 'delete_product', 'view_product',
                'view_order',
            ]
        )
        employee_group.permissions.set(perms)
        self.stdout.write(f'  Employee group configured with {perms.count()} permissions.')

        # -- Summary ------------------------------------------------─
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('[OK] Seed data complete!'))
        self.stdout.write(self.style.SUCCESS(f'  Categories : {Category.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  Brands     : {Brand.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  Products   : {Product.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'  CMS Pages  : {Page.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(''))
        self.stdout.write(self.style.SUCCESS('Next steps:'))
        self.stdout.write('  python manage.py createsuperuser')
        self.stdout.write('  python manage.py runserver')
        self.stdout.write(self.style.SUCCESS('=' * 50))
