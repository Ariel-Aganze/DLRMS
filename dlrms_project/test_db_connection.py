# test_db_connection.py
# Simple script to test database connection
# Place this file in the same directory as manage.py

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dlrms.settings')

try:
    django.setup()
    from django.db import connection
    
    def test_database_connection():
        print("Testing database connection...")
        
        try:
            with connection.cursor() as cursor:
                # Test 1: Basic connection
                cursor.execute("SELECT version();")
                version = cursor.fetchone()
                print(f"✅ PostgreSQL Version: {version[0][:50]}...")
                
                # Test 2: PostGIS version
                cursor.execute("SELECT PostGIS_version();")
                postgis_version = cursor.fetchone()
                print(f"✅ PostGIS Version: {postgis_version[0]}")
                
                # Test 3: List available extensions
                cursor.execute("SELECT name FROM pg_available_extensions WHERE name LIKE 'postgis%' AND installed_version IS NOT NULL;")
                extensions = cursor.fetchall()
                print("✅ Installed PostGIS Extensions:")
                for ext in extensions:
                    print(f"   - {ext[0]}")
                
                print("\n🎉 Database connection successful!")
                print("You can proceed with migrations!")
                return True
                
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print("\n💡 Check your .env file and database credentials")
            return False

    if __name__ == "__main__":
        test_database_connection()
        
except Exception as e:
    print(f"❌ Django setup failed: {e}")
    print("Make sure you're in the project directory and your settings are correct")