#!/usr/bin/env python
import os
import subprocess
import sys

def setup_environment():
    """Set up the BitHub development environment"""
    print("Setting up BitHub development environment...")
    
    # Check if virtualenv is activated
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("ERROR: Please activate your virtual environment first!")
        print("Example:")
        print("  On Windows: env\\Scripts\\activate")
        print("  On Linux/Mac: source env/bin/activate")
        sys.exit(1)
    
    # Install requirements
    print("\nInstalling dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Create necessary directories
    print("\nCreating necessary directories...")
    os.makedirs('media/tax_reports', exist_ok=True)
    os.makedirs('media/kyc_documents', exist_ok=True)
    os.makedirs('media/profile_pics', exist_ok=True)
    os.makedirs('media/crypto_icons', exist_ok=True)
    
    # Run migrations
    print("\nRunning database migrations...")
    subprocess.check_call([sys.executable, "manage.py", "makemigrations"])
    subprocess.check_call([sys.executable, "manage.py", "migrate"])
    
    # Create a superuser if needed
    create_superuser = input("\nDo you want to create a superuser? (y/n): ")
    if create_superuser.lower() == 'y':
        subprocess.check_call([sys.executable, "manage.py", "createsuperuser"])
    
    print("\nSetup complete! You can now run the development server:")
    print("  python manage.py runserver")

if __name__ == "__main__":
    setup_environment()
