"""
System Health Check

Validates that all dependencies are properly installed and configured.
"""

import sys
import importlib


def check_import(module_name: str, package_name: str = None) -> bool:
    """Check if a module can be imported"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {package_name or module_name}")
        return True
    except ImportError:
        print(f"❌ {package_name or module_name} (pip install {package_name or module_name})")
        return False


def check_ollama() -> bool:
    """Check Ollama server connection"""
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server (running)")
            
            # List models
            data = response.json()
            models = [model["name"] for model in data.get("models", [])]
            if models:
                print(f"   Available models: {', '.join(models)}")
            else:
                print("   ⚠️  No models found. Run: ollama pull qwen2.5:7b")
            return True
        else:
            print("❌ Ollama server (not responding)")
            return False
    except Exception as e:
        print(f"❌ Ollama server (not running - start with: ollama serve)")
        return False


def check_playwright() -> bool:
    """Check if Playwright browsers are installed"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Try to get browser
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✅ Playwright Chromium")
                return True
            except Exception as e:
                print("❌ Playwright Chromium (run: playwright install chromium)")
                return False
    except ImportError:
        print("❌ Playwright (pip install playwright)")
        return False


def main():
    """Run all health checks"""
    print("=" * 60)
    print("🔍 AGENTIC SYSTEM HEALTH CHECK")
    print("=" * 60)
    print()
    
    print("Core Dependencies:")
    print("-" * 60)
    all_ok = True
    
    # Core dependencies
    all_ok &= check_import("yaml", "pyyaml")
    all_ok &= check_import("pydantic")
    all_ok &= check_import("loguru")
    all_ok &= check_import("requests")
    
    print()
    print("Desktop Automation:")
    print("-" * 60)
    all_ok &= check_import("pyautogui")
    all_ok &= check_import("keyboard")
    all_ok &= check_import("mouse")
    all_ok &= check_import("PIL", "pillow")
    
    print()
    print("Browser Automation:")
    print("-" * 60)
    all_ok &= check_import("playwright")
    all_ok &= check_playwright()
    
    print()
    print("OCR (Optional):")
    print("-" * 60)
    ocr_ok = check_import("easyocr")
    if ocr_ok:
        check_import("cv2", "opencv-python")
    else:
        print("   (OCR is optional - can be enabled in config)")
    
    print()
    print("LLM Backend:")
    print("-" * 60)
    ollama_ok = check_ollama()
    
    print()
    print("=" * 60)
    
    if all_ok and ollama_ok:
        print("✅ ALL SYSTEMS READY")
        print()
        print("You can now run: python main.py")
    else:
        print("❌ SOME COMPONENTS MISSING")
        print()
        print("Fix the issues above and run this check again.")
    
    print("=" * 60)
    
    return all_ok and ollama_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
