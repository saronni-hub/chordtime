#!/usr/bin/env python3
"""
ChordTime V2 Test Script for OpenCode
Tests the critical issues identified
"""

import requests
import json
import time

BASE_URL = "http://localhost:8193"

def test_server_availability():
    """Test 1: Is the server running?"""
    print("Test 1: Server availability")
    try:
        response = requests.get(f"{BASE_URL}/chordtimev2.html", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running")
            # Check for "Método" field in HTML
            if "statSource" in response.text:
                print("✅ HTML has 'Método' field")
            else:
                print("❌ HTML missing 'Método' field")
            return True
        else:
            print(f"❌ Server returned {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server not reachable: {e}")
        return False

def test_preview_vs_download_logic():
    """Test 2: Check server code for 90-second bug fix"""
    print("\nTest 2: Checking server logic for 90-second bug")
    
    # Read server code
    try:
        with open("/Volumes/DiscoExterno/ai-studio/chordtimev2/chordtime_server.py", "r") as f:
            content = f.read()
        
        # Check for the fix
        if "Always detect chords from FULL audio when downloading" in content:
            print("✅ Server has 90-second bug fix comment")
        else:
            print("❌ Server missing 90-second bug fix comment")
            
        # Check if preview chords are ignored
        if "pre_chords = body.get('chords')" in content:
            print("⚠️  Server still reads pre_chords - may be using preview chords")
        else:
            print("✅ Server doesn't read pre_chords - good")
            
        # Check download endpoint logic
        if "if detect:" in content and "# Always detect chords from FULL audio" in content:
            print("✅ Download endpoint has detect logic")
        else:
            print("❌ Download endpoint logic may be broken")
            
    except Exception as e:
        print(f"❌ Error reading server code: {e}")

def test_bpm_in_responses():
    """Test 3: Check if BPM is included in responses"""
    print("\nTest 3: Checking BPM in response logic")
    
    try:
        with open("/Volumes/DiscoExterno/ai-studio/chordtimev2/chordtime_server.py", "r") as f:
            content = f.read()
        
        # Check for BPM in responses
        bpm_count = content.count("'bpm':")
        print(f"Found {bpm_count} occurrences of 'bpm' in server code")
        
        # Check specific endpoints
        if "'bpm': round(bpm, 1)" in content:
            print("✅ BPM rounding present")
        else:
            print("❌ BPM rounding missing")
            
        # Check preview endpoint
        if "'source': 'preview'" in content and "'bpm': round(bpm, 1)" in content:
            print("✅ Preview endpoint includes BPM")
        else:
            print("❌ Preview endpoint may not include BPM")
            
    except Exception as e:
        print(f"❌ Error checking BPM logic: {e}")

def test_frontend_js():
    """Test 4: Check frontend JavaScript fixes"""
    print("\nTest 4: Checking frontend JavaScript")
    
    try:
        with open("/Volumes/DiscoExterno/ai-studio/chordtimev2/chordtime.html", "r") as f:
            content = f.read()
        
        # Check for beat calculation
        if "beat = m.time * data.bpm / 60.0" in content:
            print("✅ Frontend has beat calculation")
        else:
            print("❌ Frontend missing beat calculation")
            
        # Check for download button fix
        if "const downloadData = {" in content and "bpm: lastData.bpm" in content:
            print("✅ Download button includes BPM")
        else:
            print("❌ Download button may not include BPM")
            
        # Check for source text mapping
        if "sourceText = 'Vista previa'" in content:
            print("✅ Source text mapping present")
        else:
            print("❌ Source text mapping missing")
            
    except Exception as e:
        print(f"❌ Error checking frontend: {e}")

def check_server_logs():
    """Test 5: Check server logs for issues"""
    print("\nTest 5: Checking server logs")
    
    log_files = [
        "/tmp/chordtime_final.log",
        "/tmp/chordtime_new.log",
        "/tmp/chordtime_debug.log"
    ]
    
    for log_file in log_files:
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
                if lines:
                    print(f"\n{log_file} (last 5 lines):")
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
                    # Check for errors
                    errors = [l for l in lines if "error" in l.lower() or "exception" in l.lower() or "traceback" in l.lower()]
                    if errors:
                        print(f"  ⚠️  Found {len(errors)} error(s) in log")
                else:
                    print(f"{log_file}: Empty or doesn't exist")
        except FileNotFoundError:
            print(f"{log_file}: Not found")
        except Exception as e:
            print(f"{log_file}: Error reading: {e}")

def main():
    print("=" * 60)
    print("CHORDTIME V2 DIAGNOSTIC TESTS")
    print("=" * 60)
    
    test_server_availability()
    test_preview_vs_download_logic()
    test_bpm_in_responses()
    test_frontend_js()
    check_server_logs()
    
    print("\n" + "=" * 60)
    print("RECOMMENDED ACTIONS FOR OPENCODE:")
    print("1. Add debug logging to verify full audio analysis")
    print("2. Implement cache-busting for frontend")
    print("3. Test with actual YouTube download + chord detection")
    print("4. Verify JSON output includes BPM and full song chords")
    print("=" * 60)

if __name__ == "__main__":
    main()