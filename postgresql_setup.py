#!/usr/bin/env python3
"""
PostgreSQL Setup and Migration Script
Helps migrate from MySQL to PostgreSQL
"""

import subprocess
import sys
import os
import json

def check_postgresql_installation():
    """Check if PostgreSQL is installed and running"""
    try:
        result = subprocess.run(['psql', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ PostgreSQL installed: {result.stdout.strip()}")
            return True
        else:
            print("❌ PostgreSQL command not found")
            return False
    except FileNotFoundError:
        print("❌ PostgreSQL not found in PATH")
        return False

def check_postgresql_service():
    """Check if PostgreSQL service is running"""
    try:
        # Windows service check
        result = subprocess.run(['sc', 'query', 'postgresql-x64-15'], 
                              capture_output=True, text=True)
        if 'RUNNING' in result.stdout:
            print("✅ PostgreSQL service is running")
            return True
        else:
            print("❌ PostgreSQL service not running")
            return False
    except Exception as e:
        print(f"⚠️  Could not check service status: {e}")
        return False

def create_database_and_user():
    """Create PostgreSQL database and user"""
    commands = [
        # Connect as postgres superuser and create database/user
        "CREATE DATABASE db_book;",
        "CREATE USER bookuser WITH PASSWORD 'BookProject123!';",
        "GRANT ALL PRIVILEGES ON DATABASE db_book TO bookuser;",
        "ALTER USER bookuser CREATEDB;",  # Allow user to create test databases
    ]
    
    print("📝 Creating PostgreSQL database and user...")
    
    try:
        for cmd in commands:
            result = subprocess.run([
                'psql', '-U', 'postgres', '-c', cmd
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Executed: {cmd[:50]}...")
            else:
                if "already exists" in result.stderr:
                    print(f"ℹ️  Already exists: {cmd[:30]}...")
                else:
                    print(f"❌ Failed: {cmd[:30]}... - {result.stderr}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def export_mysql_data():
    """Export data from MySQL to JSON format"""
    print("📤 Exporting data from MySQL...")
    
    try:
        # Use Django's dumpdata command to export from MySQL
        result = subprocess.run([
            'python', 'manage.py', 'dumpdata', 
            'manager.Manager', 'manager.Publisher', 'manager.Book', 'manager.Author',
            '--format=json', '--indent=2'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            with open('mysql_data_export.json', 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            print("✅ MySQL data exported to mysql_data_export.json")
            return True
        else:
            print(f"❌ Export failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error exporting data: {e}")
        return False

def import_data_to_postgresql():
    """Import data into PostgreSQL"""
    print("📥 Importing data to PostgreSQL...")
    
    try:
        # Run migrations first
        subprocess.run(['python', 'manage.py', 'migrate'], check=True)
        print("✅ Database migrations completed")
        
        # Import data
        if os.path.exists('mysql_data_export.json'):
            result = subprocess.run([
                'python', 'manage.py', 'loaddata', 'mysql_data_export.json'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Data imported successfully")
                return True
            else:
                print(f"❌ Import failed: {result.stderr}")
                return False
        else:
            print("⚠️  No export file found. Skipping data import.")
            return True
    except Exception as e:
        print(f"❌ Error importing data: {e}")
        return False

def main():
    print("🐘 PostgreSQL Migration Setup")
    print("=" * 50)
    
    steps_passed = 0
    total_steps = 5
    
    # Step 1: Check PostgreSQL installation
    if check_postgresql_installation():
        steps_passed += 1
    
    # Step 2: Check PostgreSQL service
    if check_postgresql_service():
        steps_passed += 1
    
    # Step 3: Create database and user
    if create_database_and_user():
        steps_passed += 1
    
    # Step 4: Export MySQL data (optional)
    print("\n📋 Data Migration:")
    export_success = export_mysql_data()
    if export_success:
        steps_passed += 1
    
    # Step 5: Import data to PostgreSQL
    if import_data_to_postgresql():
        steps_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Migration Progress: {steps_passed}/{total_steps} steps completed")
    
    if steps_passed >= 4:
        print("\n🎉 PostgreSQL setup completed successfully!")
        print("\n🎯 Next Steps:")
        print("1. Update your settings.py to use PostgreSQL")
        print("2. Install psycopg2: pip install psycopg2-binary")
        print("3. Run: python manage.py runserver")
        print("4. Test the application")
    else:
        print("\n⚠️  Migration incomplete. Please address the issues above.")
        print("\n🛠️  Troubleshooting:")
        print("1. Install PostgreSQL: https://www.postgresql.org/download/")
        print("2. Start PostgreSQL service")
        print("3. Ensure postgres user has access")
    
    return 0 if steps_passed >= 4 else 1

if __name__ == "__main__":
    sys.exit(main())
