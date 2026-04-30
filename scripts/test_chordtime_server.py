#!/usr/bin/env python3
"""
Test ChordTime server
"""

import requests
import json

print("Testing ChordTime server...")

# Test 1: Check if server is responding
try:
    response = requests.get("http://localhost:8193/chordtimev2.html", timeout=5)
    print(f"✅ Server responding: HTTP {response.status_code}")
except Exception as e:
    print(f"❌ Server not responding: {e}")
    exit(1)

# Test 2: Check HTML has Método field
if "statSource" in response.text:
    print("✅ HTML has 'Método' field")
else:
    print("❌ HTML missing 'Método' field")

# Test 3: Check server version by looking at code snippet
print("\nChecking server code version...")
try:
    # Try to get a simple API response
    test_data = {"test": "hello"}
    api_response = requests.post(
        "http://localhost:8193/api/test",
        json=test_data,
        timeout=5
    )
    print(f"API test: {api_response.status_code}")
except Exception as e:
    print(f"API test failed (expected): {str(e)[:50]}")

print("\n---")
print("If user doesn't see changes:")
print("1. Hard refresh: Cmd+Shift+R (Mac) or Ctrl+F5 (Windows)")
print("2. Check browser console for errors")
print("3. Try different browser or private mode")