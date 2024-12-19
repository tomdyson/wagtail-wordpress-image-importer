# Wagtail WordPress Image Importer

A Django management command to import images from a WordPress XML export into Wagtail.

## Installation

```bash
pip install wagtail-wordpress-image-importer
```

## Configuration

Add to your INSTALLED_APPS in Django settings:

```python
INSTALLED_APPS = [
    ...
    'wagtail_wordpress_image_importer',
    ...
]
```

## Usage

Export your WordPress content as XML from WordPress admin (Tools > Export).

Then run:

```bash
python manage.py import_wordpress_images /path/to/your/wordpress-export.xml
```

### Options

- `--delete-existing`: Delete all existing Wagtail images before importing
- `--debug`: Show detailed debug information during import

## License

MIT License