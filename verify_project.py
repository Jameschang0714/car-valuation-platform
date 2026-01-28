
import sys
import importlib

def check_import(module_name):
    try:
        importlib.import_module(module_name)
        print(f"[OK] {module_name}")
    except ImportError as e:
        print(f"[FAIL] {module_name}: {e}")
        return False
    return True

print("Verifying environment...")
modules = ['streamlit', 'pandas', 'requests', 'bs4', 'fake_useragent', 'curl_cffi']
all_pass = True
for m in modules:
    if not check_import(m):
        all_pass = False

if all_pass:
    print("\nAll dependencies installed correctly!")
    try:
        from app import run_scraper
        print("Successfully imported app.py logic")
    except ImportError:
        print("Could not import app.py (might be expected if it has script-level code)")
else:
    print("\nSome dependencies are missing.")
    sys.exit(1)
