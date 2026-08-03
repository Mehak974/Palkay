import csv
import os
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils.text import slugify
from catalog.models import Product, Category, ProductImage
from urllib.parse import urlparse

class Command(BaseCommand):
    help = 'Import products from WooCommerce CSV export'

    def handle(self, *args, **kwargs):
        csv_file_path = 'wc-product-export-4-8-2026-1785784611851.csv'
        
        if not os.path.exists(csv_file_path):
            self.stdout.write(self.style.ERROR(f'File {csv_file_path} not found.'))
            return

        # Fetch all existing categories for mapping
        existing_categories = {c.name.lower(): c for c in Category.objects.all()}
        fallback_category = Category.objects.first()

        if not fallback_category:
            self.stdout.write(self.style.ERROR('No categories exist in the database! Please create at least one category first.'))
            return

        with open(csv_file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            created_count = 0
            
            for row in reader:
                prod_type = row.get('Type', '').lower()
                
                # We mainly want simple products or parent variable products
                if prod_type not in ['simple', 'variable']:
                    continue
                
                name = row.get('Name', '').strip()
                if not name:
                    continue
                    
                sku = row.get('SKU', '').strip()
                if not sku:
                    sku = slugify(name)[:50]
                
                # Check if product already exists
                if Product.objects.filter(sku=sku).exists():
                    self.stdout.write(self.style.WARNING(f'Skipping {name}, SKU {sku} already exists.'))
                    continue
                
                # Price parsing
                raw_price = row.get('Regular price', '')
                raw_sale = row.get('Sale price', '')
                
                try:
                    price = float(raw_sale) if raw_sale else float(raw_price) if raw_price else 0.0
                except ValueError:
                    price = 0.0
                
                try:
                    compare_price = float(raw_price) if raw_sale and raw_price else None
                except ValueError:
                    compare_price = None

                # Stock
                raw_stock = row.get('Stock', '')
                try:
                    stock_quantity = int(raw_stock) if raw_stock else 10
                except ValueError:
                    stock_quantity = 10
                
                # Category Mapping
                cat_string = row.get('Categories', '')
                assigned_category = fallback_category
                
                if cat_string:
                    cat_names = [c.strip() for c in cat_string.replace('>', ',').split(',')]
                    for cat_name in cat_names:
                        if cat_name.lower() in existing_categories:
                            assigned_category = existing_categories[cat_name.lower()]
                            break

                description = row.get('Description', '')

                # Create Product
                product = Product.objects.create(
                    name=name,
                    sku=sku,
                    description=description,
                    category=assigned_category,
                    price=price,
                    compare_at_price=compare_price,
                    stock_quantity=stock_quantity,
                    is_active=row.get('Published') == '1'
                )
                
                # Handle Images
                images_string = row.get('Images', '')
                if images_string:
                    image_urls = [url.strip() for url in images_string.split(',')]
                    for idx, image_url in enumerate(image_urls):
                        try:
                            self.stdout.write(f'  Downloading image {idx+1} for {name}...')
                            response = requests.get(image_url, timeout=10)
                            if response.status_code == 200:
                                file_name = os.path.basename(urlparse(image_url).path)
                                if not file_name:
                                    file_name = f"{product.slug}-{idx}.jpg"
                                
                                ProductImage.objects.create(
                                    product=product,
                                    image=ContentFile(response.content, name=file_name),
                                    alt_text=name,
                                    is_primary=(idx == 0)
                                )
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f'  Failed to download image from {image_url}: {e}'))

                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created product: {name}'))
                
        self.stdout.write(self.style.SUCCESS(f'Successfully imported {created_count} products!'))
