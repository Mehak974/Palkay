# -*- coding: utf-8 -*-
import csv
import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.db import transaction
from catalog.models import Category, Brand, Product, ProductImage

CATEGORY_MAPPING = {
    'Home & Decor': 'Home & Decor',
    'Tools': 'Tools',
    'Supplements': 'Medicine & Supplements',
    'Pet Care': 'Pet Care',
    'Beauty & Cosmetic': 'Beauty & Cosmetics',
    'Fashion': 'Fashion',
}

class Command(BaseCommand):
    help = 'Import products from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_file_path}'))
            return

        self.stdout.write(f'Reading products from {csv_file_path}...')

        with open(csv_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            created_count = 0
            updated_count = 0

            for row in reader:
                sku = row.get('SKU', '').strip()
                name = row.get('Name', '').strip()
                
                if not name:
                    continue
                
                # If SKU is empty, generate one based on name
                if not sku:
                    sku = f"GEN-{slugify(name)[:20].upper()}"

                description = row.get('Description', '').strip()
                if not description:
                    description = row.get('Short description', '').strip() or 'No description available.'

                # Determine Category
                category_raw = row.get('Categories', '')
                category_names = [c.strip() for c in category_raw.split(',') if c.strip()]
                
                category_obj = None
                for cat_name in category_names:
                    mapped_name = CATEGORY_MAPPING.get(cat_name)
                    if mapped_name:
                        category_obj = Category.objects.filter(name=mapped_name).first()
                        if category_obj:
                            break

                if not category_obj:
                    # Fallback to Uncategorized
                    category_obj, _ = Category.objects.get_or_create(
                        slug='uncategorized',
                        defaults={
                            'name': 'Uncategorized',
                            'description': 'Uncategorized products',
                            'sort_order': 99
                        }
                    )

                # Determine Brand
                brand_name = row.get('Brands', '').strip()
                brand_obj = None
                if brand_name:
                    brand_obj, _ = Brand.objects.get_or_create(
                        slug=slugify(brand_name),
                        defaults={'name': brand_name, 'description': f'Products by {brand_name}'}
                    )

                # Determine Price
                regular_price_str = row.get('Regular price', '').strip()
                sale_price_str = row.get('Sale price', '').strip()

                try:
                    regular_price = float(regular_price_str) if regular_price_str else 0.0
                except ValueError:
                    regular_price = 0.0

                try:
                    sale_price = float(sale_price_str) if sale_price_str else None
                except ValueError:
                    sale_price = None

                if sale_price is not None:
                    price = sale_price
                    compare_at_price = regular_price if regular_price > sale_price else None
                else:
                    price = regular_price
                    compare_at_price = None

                # Default positive price if both are 0
                if price <= 0.0:
                    price = 9.99

                # Determine Stock
                stock_str = row.get('Stock', '').strip()
                try:
                    stock_quantity = int(stock_str) if stock_str else 100
                except ValueError:
                    stock_quantity = 100

                is_featured = str(row.get('Is featured?', '0')).strip() in ('1', 'true', 'True')
                is_active = str(row.get('Published', '1')).strip() in ('1', 'true', 'True')

                # Get or create product
                product_slug = slugify(name)
                # Ensure slug uniqueness if same name exists
                base_slug = product_slug
                counter = 1
                while Product.objects.filter(slug=product_slug).exclude(sku=sku).exists():
                    product_slug = f"{base_slug}-{counter}"
                    counter += 1

                defaults = {
                    'name': name,
                    'slug': product_slug,
                    'category': category_obj,
                    'brand': brand_obj,
                    'price': price,
                    'compare_at_price': compare_at_price,
                    'stock_quantity': stock_quantity,
                    'is_featured': is_featured,
                    'is_active': is_active,
                    'description': description,
                }

                with transaction.atomic():
                    product, created = Product.objects.update_or_create(
                        sku=sku,
                        defaults=defaults
                    )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

                # Handle images
                image_urls_raw = row.get('Images', '')
                image_urls = [u.strip() for u in image_urls_raw.split(',') if u.strip()]
                
                for idx, img_url in enumerate(image_urls):
                    # Check if this image already exists for the product to prevent duplicate downloads
                    filename = os.path.basename(img_url.split('?')[0])
                    # If we already have an image with this alt_text or file name, we can skip downloading it
                    if product.images.filter(alt_text=f'{name} - Image {idx+1}').exists() or product.images.filter(image__contains=filename).exists():
                        continue

                    try:
                        self.stdout.write(f'  Downloading image for {name}: {img_url}')
                        res = requests.get(img_url, timeout=10)
                        if res.status_code == 200:
                            img_file = ContentFile(res.content)
                            img_obj = ProductImage(
                                product=product,
                                alt_text=f'{name} - Image {idx+1}',
                                is_primary=(idx == 0),
                                sort_order=idx
                            )
                            img_obj.image.save(filename, img_file, save=True)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f'  Failed to download image from {img_url}: {e}'))

            self.stdout.write(self.style.SUCCESS(f'Successfully processed CSV: {created_count} created, {updated_count} updated.'))
