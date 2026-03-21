#!/usr/bin/env python3
"""
MySQL Installation Checker
Verifies existing MySQL installation before setting up Django project
"""

import subprocess
import sys
import socket

def check_mysql_service():
    """Check if MySQL service is running on Windows"""
    try:
        # Check MySQL service status
        result = subprocess.run(['sc', 'query', 'type=service'], 
                              capture_output=True, text=True)
        mysql_services = [line for line in result.stdout.split('\n') 
                         if 'mysql' in line.lower()]
        
        if mysql_services:
            print("✅ Found MySQL services:")
            for service in mysql_services:
                print(f"   {service.strip()}")
            return True
        else:
            print("❌ No MySQL services found")
            return False
    except Exception as e:
        print(f"❌ Error checking services: {e}")
        return False

def check_mysql_port():
    """Check if MySQL is listening on port 3306"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('127.0.0.1', 3306))
        sock.close()
        
        if result == 0:
            print("✅ MySQL is listening on port 3306")
            return True
        else:
            print("❌ MySQL is not responding on port 3306")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False

def check_mysql_command():
    """Check if mysql command is available"""
    try:
        result = subprocess.run(['mysql', '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ MySQL command available: {result.stdout.strip()}")
            return True
        else:
            print("❌ MySQL command not found in PATH")
            return False
    except FileNotFoundError:
        print("❌ MySQL command not found in PATH")
        return False
    except Exception as e:
        print(f"❌ Error checking MySQL command: {e}")
        return False

def test_mysql_connection():
    """Test actual MySQL connection"""
    try:
        # Try to connect using mysql command
        result = subprocess.run(['mysql', '-u', 'root', '-e', 'SELECT 1;'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ MySQL connection successful (passwordless root)")
            return True
        elif 'Access denied' in result.stderr:
            print("⚠️  MySQL is running but requires password for root user")
            print("   This is normal - you'll need to provide password when connecting")
            return True
        else:
            print(f"❌ MySQL connection failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ MySQL connection timed out")
        return False
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        return False

def get_mysql_info():
    """Get detailed MySQL installation information"""
    try:
        # Check MySQL installation path
        result = subprocess.run(['where', 'mysql'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"📍 MySQL installed at: {result.stdout.strip()}")
        
        # Check running MySQL processes
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        mysql_processes = [line for line in result.stdout.split('\n') 
                          if 'mysql' in line.lower()]
        
        if mysql_processes:
            print("🔄 Running MySQL processes:")
            for process in mysql_processes:
                print(f"   {process.strip()}")
        
    except Exception as e:
        print(f"ℹ️  Could not get detailed info: {e}")

def main():
    print("🔍 Checking Existing MySQL Installation...")
    print("=" * 50)
    
    checks_passed = 0
    total_checks = 4
    
    # Run all checks
    if check_mysql_service():
        checks_passed += 1
    
    if check_mysql_port():
        checks_passed += 1
    
    if check_mysql_command():
        checks_passed += 1
    
    if test_mysql_connection():
        checks_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {checks_passed}/{total_checks} checks passed")
    
    # Get additional info
    print("\n📋 Additional Information:")
    get_mysql_info()
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    if checks_passed >= 3:
        print("✅ Your MySQL installation looks good!")
        print("   → Use existing MySQL with conda for Python packages")
        print("   → Run: conda create -n book_project python=3.9")
        print("   → Run: conda install django mysqlclient")
    elif checks_passed >= 1:
        print("⚠️  MySQL is partially working")
        print("   → Check if MySQL service needs to be started")
        print("   → Verify MySQL configuration")
        print("   → Consider restarting MySQL service")
    else:
        print("❌ MySQL installation issues detected")
        print("   → MySQL may not be properly installed")
        print("   → Consider reinstalling MySQL")
        print("   → Or install MySQL fresh")
    
    print(f"\n🎯 Next Steps:")
    print("1. Fix any MySQL issues shown above")
    print("2. Create conda environment: conda create -n book_project python=3.9")
    print("3. Install Python packages: conda install django mysqlclient")
    print("4. Import database: mysql -u root -p db_book < db_book.sql")
    print("5. Configure Django settings.py with your MySQL credentials")
    
    return 0 if checks_passed >= 3 else 1

if __name__ == "__main__":
    sys.exit(main())
