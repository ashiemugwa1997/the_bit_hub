import os
import django
import sys

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "the_bit_hub_project.settings")
django.setup()

# Create the migrations
from django.core.management import call_command

print("Creating migrations for News model...")
call_command('makemigrations', 'trading_hub')
print("Applying migrations...")
call_command('migrate')
print("Migrations applied successfully.")

# Exit script
sys.exit(0)
