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

## Development

### Local development

```bash
# Clone the repository
git clone git@github.com:tomdyson/wagtail-wordpress-image-importer.git
cd wagtail-wordpress-image-importer

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install dependencies
pip install -e .
```

### Releasing a new version

1. Update the version number in `pyproject.toml`
2. Commit your changes
3. Create and push a new tag:
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
4. Create a new release on GitHub using this tag
5. The GitHub Action will automatically build and publish to PyPI