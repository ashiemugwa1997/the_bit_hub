import subprocess
import sys

def install_dependencies():
    """Install required dependencies for API functionality"""
    print("Installing API dependencies...")
    
    # List of required packages
    packages = [
        "djangorestframework>=3.14.0",
        "django-cors-headers>=3.13.0",
        "drf-yasg>=1.21.4",
        "djangorestframework-simplejwt>=5.2.2"
    ]
    
    try:
        # Install packages using pip
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("Successfully installed API dependencies!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        sys.exit(1)

if __name__ == "__main__":
    install_dependencies()
    print("\nYou can now run the server with 'python manage.py runserver'")
