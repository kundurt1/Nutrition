from supabase import create_client, Client
from config import settings

def get_supabase_client() -> Client:
    return create_client(settings.supabase_url, settings.supabase_service_key)

supabase = get_supabase_client()
