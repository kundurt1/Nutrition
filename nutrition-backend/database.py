# Fix database.py
from supabase import create_client, Client
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Debug prints to help diagnose issues
print(f"Supabase URL loaded: {'Yes' if SUPABASE_URL else 'No'}")
print(f"Supabase Key loaded: {'Yes' if SUPABASE_KEY else 'No'}")

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing Supabase: {e}")
        supabase = None
else:
    print("⚠️ Supabase credentials missing - database features disabled")
    supabase = None