"""
Generate a new SECRET_KEY for Django production deployment

Run this script to generate a secure SECRET_KEY for your production environment.
Copy the output and paste it into your .env.production file.

Usage:
    python generate_secret_key.py
"""

from django.core.management.utils import get_random_secret_key

if __name__ == "__main__":
    print("\n" + "="*70)
    print("Django SECRET_KEY Generator")
    print("="*70)
    
    secret_key = get_random_secret_key()
    
    print("\n✅ New SECRET_KEY generated successfully!")
    print("\n📋 Copy this SECRET_KEY to your .env.production file:\n")
    print(f"SECRET_KEY={secret_key}")
    
    print("\n" + "="*70)
    print("⚠️  IMPORTANT SECURITY NOTES:")
    print("="*70)
    print("1. Never share this key publicly")
    print("2. Never commit this key to version control")
    print("3. Each environment should have a unique SECRET_KEY")
    print("4. Store this securely (password manager recommended)")
    print("5. If compromised, generate a new one immediately")
    print("="*70 + "\n")
