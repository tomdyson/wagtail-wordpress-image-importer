import codecs
import hashlib
import os
import re
import xml.etree.ElementTree as ET
from io import BytesIO
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image as PILImage
from tqdm import tqdm
from wagtail.images.models import Image


class Command(BaseCommand):
    help = 'Import images from WordPress XML export'

    def add_arguments(self, parser):
        parser.add_argument('xml_file', type=str, help='Path to WordPress XML export file')
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete all existing images before importing'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show detailed debug information for each image'
        )

    def handle(self, *args, **options):
        xml_file = options['xml_file']
        debug = options['debug']
        
        # Delete existing images if flag is set
        if options['delete_existing']:
            image_count = Image.objects.count()
            Image.objects.all().delete()
            self.stdout.write(f"Deleted {image_count} existing images")
        
        try:
            # Read the file with UTF-8 encoding and handle encoding errors
            with codecs.open(xml_file, 'r', encoding='utf-8', errors='replace') as file:
                xml_content = file.read()
            
            # Remove any invalid XML characters
            xml_content = re.sub(u'[^\u0020-\uD7FF\u0009\u000A\u000D\uE000-\uFFFD\U00010000-\U0010FFFF]+', '', xml_content)
            
            # Parse the cleaned XML content
            root = ET.fromstring(xml_content)
            
            # WordPress XML uses namespaces
            namespaces = {
                'wp': 'http://wordpress.org/export/1.2/',
                'content': 'http://purl.org/rss/1.0/modules/content/',
                'excerpt': 'http://wordpress.org/export/1.2/excerpt/'
            }

            # Find all attachment items
            attachments = root.findall(".//item[wp:post_type='attachment']", namespaces)
            
            # Create progress bar
            with tqdm(total=len(attachments), desc="Importing images") as pbar:
                for attachment in attachments:
                    url_elem = attachment.find('wp:attachment_url', namespaces)
                    if url_elem is None:
                        pbar.update(1)
                        continue
                        
                    url = url_elem.text
                    if not url or not self._is_image_url(url):
                        pbar.update(1)
                        continue
                    
                    if debug:
                        # Print all available metadata
                        self.stdout.write("\nImage Metadata:")
                        self.stdout.write(f"URL: {url}")
                        
                        # Basic elements
                        for elem in attachment:
                            if not elem.tag.startswith('{'):  # Direct children without namespace
                                if elem.text and elem.text.strip():
                                    self.stdout.write(f"{elem.tag}: {elem.text.strip()}")
                        
                        # WordPress specific elements
                        for elem in attachment.findall('wp:*', namespaces):
                            if elem.text and elem.text.strip():
                                self.stdout.write(f"wp:{elem.tag.split('}')[1]}: {elem.text.strip()}")
                        
                        # Post meta elements
                        for meta in attachment.findall('wp:postmeta', namespaces):
                            meta_key = meta.find('wp:meta_key', namespaces)
                            meta_value = meta.find('wp:meta_value', namespaces)
                            if meta_key is not None and meta_value is not None and meta_key.text and meta_value.text:
                                self.stdout.write(f"meta - {meta_key.text}: {meta_value.text.strip()}")
                        
                        # Content
                        content = attachment.find('content:encoded', namespaces)
                        if content is not None and content.text and content.text.strip():
                            self.stdout.write(f"content: {content.text.strip()}")
                        
                        # Excerpt
                        excerpt = attachment.find('excerpt:encoded', namespaces)
                        if excerpt is not None and excerpt.text and excerpt.text.strip():
                            self.stdout.write(f"excerpt: {excerpt.text.strip()}")
                        
                        self.stdout.write("-" * 80)
                    
                    # Create a unique ID based on the URL
                    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
                    
                    # Get the WordPress title and clean it up
                    title_elem = attachment.find('title')
                    if title_elem is not None and title_elem.text:
                        # Clean up the title - replace hyphens with spaces and title case it
                        title = title_elem.text.replace('-', ' ').title().strip()
                    else:
                        # Fall back to hash if no title
                        title = f"wp-{url_hash}"
                    
                    # Skip if image already exists (now checking by cleaned title)
                    if Image.objects.filter(title=title).exists():
                        if debug:
                            self.stdout.write(f"Skipping existing image: {url}")
                        pbar.update(1)
                        continue
                    
                    # Get alt text from WordPress metadata
                    alt_text = ''  # Default to empty string instead of None
                    for meta in attachment.findall('wp:postmeta', namespaces):
                        meta_key = meta.find('wp:meta_key', namespaces)
                        if meta_key is not None and meta_key.text == '_wp_attachment_image_alt':
                            meta_value = meta.find('wp:meta_value', namespaces)
                            if meta_value is not None and meta_value.text:
                                alt_text = meta_value.text.strip()
                                break
                    
                    try:
                        # Download image
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(url, headers=headers)
                        response.raise_for_status()
                        
                        # Get filename from URL
                        filename = os.path.basename(urlparse(url).path)
                        
                        # Open image with PIL to get dimensions
                        image_bytes = BytesIO(response.content)
                        with PILImage.open(image_bytes) as pil_image:
                            width, height = pil_image.size
                        
                        # Create Wagtail image with cleaned title and description
                        image = Image(
                            title=title,
                            description=alt_text
                        )
                        
                        # Save the file
                        image.file.save(filename, ContentFile(response.content), save=False)
                        
                        # Set dimensions after file is saved but before image is saved
                        image.width = width
                        image.height = height
                        
                        # Now save the image
                        image.save()
                        
                        if debug:
                            self.stdout.write(f"Successfully imported: {url}")
                        
                    except Exception as e:
                        self.stdout.write(f"Failed to import {url}: {str(e)}")
                    
                    pbar.update(1)
                    
        except UnicodeDecodeError as e:
            self.stdout.write(f"Encoding error: {e}")
        except ET.ParseError as e:
            self.stdout.write(f"Error parsing XML file: {e}")
        except FileNotFoundError:
            self.stdout.write(f"File not found: {xml_file}")
        except Exception as e:
            self.stdout.write(f"An unexpected error occurred: {e}")
            raise

    def _is_image_url(self, url):
        """Check if URL points to an image based on extension"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        return any(url.lower().endswith(ext) for ext in image_extensions)