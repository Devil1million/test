"""
🧪 Advanced Auto Caption Bot - Test Suite
Run comprehensive tests on video parser and caption formatter
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.video_parser import video_parser, caption_formatter
from utils.anime_api import anime_api
from config.settings import config


class TestColors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print section header"""
    print(f"\n{TestColors.HEADER}{TestColors.BOLD}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{TestColors.ENDC}\n")


def print_test(name, passed, details=""):
    """Print test result"""
    if passed:
        print(f"{TestColors.OKGREEN}✅ {name}{TestColors.ENDC}")
    else:
        print(f"{TestColors.FAIL}❌ {name}{TestColors.ENDC}")
    
    if details:
        print(f"   {details}\n")


async def test_video_parser():
    """Test video information extraction"""
    print_header("🎬 Testing Video Parser")
    
    test_cases = [
        {
            "name": "Standard Format (S01E07)",
            "filename": "Fairy_Tail_S01E07_720p.mkv",
            "caption": "",
            "expected": {
                "anime_name": "Fairy Tail",
                "season": 1,
                "episode": 7,
                "quality": "720p"
            }
        },
        {
            "name": "SubsPlease Format",
            "filename": "[SubsPlease] Demon Slayer - 01 [1080p].mkv",
            "caption": "",
            "expected": {
                "anime_name": "Demon Slayer",
                "episode": 1,
                "quality": "1080p"
            }
        },
        {
            "name": "Dot Notation",
            "filename": "Naruto.Shippuden.S01.E175.1080p.WEB-DL.mkv",
            "caption": "",
            "expected": {
                "anime_name": "Naruto Shippuden",
                "season": 1,
                "episode": 175,
                "quality": "1080p"
            }
        },
        {
            "name": "Simple Episode Number",
            "filename": "One Piece 1000 [720p].mp4",
            "caption": "",
            "expected": {
                "anime_name": "One Piece",
                "episode": 1000,
                "quality": "720p"
            }
        },
        {
            "name": "Caption Cross-Verification",
            "filename": "Attack_on_Titan_E15.mkv",
            "caption": "Attack on Titan - Episode 15 - 1080p",
            "expected": {
                "anime_name": "Attack On Titan",
                "episode": 15
            }
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test in test_cases:
        try:
            result = await video_parser.extract_anime_info(
                test["filename"],
                test["caption"]
            )
            
            # Validate results
            all_match = True
            details = []
            
            for key, expected_value in test["expected"].items():
                actual_value = result.get(key)
                
                if isinstance(expected_value, str):
                    # Case-insensitive comparison for strings
                    match = expected_value.lower() == actual_value.lower() if actual_value else False
                else:
                    match = expected_value == actual_value
                
                if not match:
                    all_match = False
                    details.append(f"{key}: expected '{expected_value}', got '{actual_value}'")
            
            if all_match:
                passed_tests += 1
                print_test(
                    test["name"],
                    True,
                    f"Extracted: {result['anime_name']} S{result.get('season', 1):02d}E{result['episode']:02d} - {result.get('quality', 'N/A')}"
                )
            else:
                print_test(
                    test["name"],
                    False,
                    "\n   ".join(details)
                )
        
        except Exception as e:
            print_test(test["name"], False, f"Error: {str(e)}")
    
    print(f"\n{TestColors.BOLD}Results: {passed_tests}/{total_tests} tests passed{TestColors.ENDC}")
    return passed_tests == total_tests


async def test_caption_formatter():
    """Test caption formatting"""
    print_header("🎨 Testing Caption Formatter")
    
    test_cases = [
        {
            "name": "Basic Variables",
            "format": "➥ {a} - S{s}E{e} - {q}",
            "data": {
                "anime_name": "Naruto",
                "season": 1,
                "episode": 5,
                "quality": "1080p"
            },
            "expected_contains": ["Naruto", "S01E05", "1080p"]
        },
        {
            "name": "Bold Formatting",
            "format": "Anime: {a}\n[B]Quality: {q}",
            "data": {
                "anime_name": "One Piece",
                "season": 1,
                "episode": 100,
                "quality": "720p"
            },
            "expected_contains": ["One Piece", "**Quality: 720p**"]
        },
        {
            "name": "Complex Format",
            "format": config.DEFAULT_CAPTION,
            "data": {
                "anime_name": "Demon Slayer",
                "season": 2,
                "episode": 7,
                "quality": "4K"
            },
            "expected_contains": ["Demon Slayer", "02", "07", "4K"]
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test in test_cases:
        try:
            result = caption_formatter.apply_caption(test["data"], test["format"])
            
            all_found = True
            missing = []
            
            for expected in test["expected_contains"]:
                if expected not in result:
                    all_found = False
                    missing.append(expected)
            
            if all_found:
                passed_tests += 1
                print_test(test["name"], True, f"Caption:\n{result}")
            else:
                print_test(
                    test["name"],
                    False,
                    f"Missing: {', '.join(missing)}\nGot:\n{result}"
                )
        
        except Exception as e:
            print_test(test["name"], False, f"Error: {str(e)}")
    
    print(f"\n{TestColors.BOLD}Results: {passed_tests}/{total_tests} tests passed{TestColors.ENDC}")
    return passed_tests == total_tests


async def test_caption_validation():
    """Test caption format validation"""
    print_header("✅ Testing Caption Validation")
    
    test_cases = [
        {
            "name": "Valid Format",
            "format": "➥ {a} [{s}]\n Episode - {e}\n Quality : {q}",
            "should_pass": True
        },
        {
            "name": "Missing Anime Name",
            "format": "Episode {e} - {q}",
            "should_pass": False
        },
        {
            "name": "With Bold Formatting",
            "format": "{a} - {s}x{e}\n[B]Powered by Bot",
            "should_pass": True
        },
        {
            "name": "Minimal Valid",
            "format": "{a}",
            "should_pass": True
        }
    ]
    
    passed_tests = 0
    total_tests = len(test_cases)
    
    for test in test_cases:
        is_valid, msg = caption_formatter.validate_format(test["format"])
        
        if is_valid == test["should_pass"]:
            passed_tests += 1
            print_test(test["name"], True, msg)
        else:
            print_test(test["name"], False, f"Expected: {test['should_pass']}, Got: {is_valid} - {msg}")
    
    print(f"\n{TestColors.BOLD}Results: {passed_tests}/{total_tests} tests passed{TestColors.ENDC}")
    return passed_tests == total_tests


async def test_api_integration():
    """Test anime API integration"""
    print_header("🔍 Testing API Integration")
    
    print(f"{TestColors.WARNING}Note: This test requires internet connection{TestColors.ENDC}\n")
    
    test_anime = ["Naruto", "One Piece", "Demon Slayer"]
    
    passed_tests = 0
    total_tests = len(test_anime)
    
    async with anime_api:
        for anime_name in test_anime:
            try:
                result = await anime_api.verify_anime_name(anime_name)
                
                if result and result.get("verified_name"):
                    passed_tests += 1
                    print_test(
                        f"Verify: {anime_name}",
                        True,
                        f"Verified as: {result['verified_name']} (Confidence: {result['confidence']:.1%})"
                    )
                else:
                    print_test(f"Verify: {anime_name}", False, "No verification data")
                
                # Rate limit
                await asyncio.sleep(1)
            
            except Exception as e:
                print_test(f"Verify: {anime_name}", False, f"Error: {str(e)}")
    
    print(f"\n{TestColors.BOLD}Results: {passed_tests}/{total_tests} tests passed{TestColors.ENDC}")
    return passed_tests == total_tests


async def main():
    """Run all tests"""
    print(f"\n{TestColors.HEADER}{TestColors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║     🧪 ADVANCED AUTO CAPTION BOT - TEST SUITE            ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(TestColors.ENDC)
    
    results = []
    
    # Run all test suites
    results.append(("Video Parser", await test_video_parser()))
    results.append(("Caption Formatter", await test_caption_formatter()))
    results.append(("Caption Validation", await test_caption_validation()))
    
    # Optional: API tests (can be slow)
    print(f"\n{TestColors.WARNING}Run API integration tests? (requires internet) [y/N]: {TestColors.ENDC}", end="")
    if input().lower() == 'y':
        results.append(("API Integration", await test_api_integration()))
    
    # Summary
    print_header("📊 Test Summary")
    
    all_passed = True
    for name, passed in results:
        status = f"{TestColors.OKGREEN}✅ PASSED" if passed else f"{TestColors.FAIL}❌ FAILED"
        print(f"{name}: {status}{TestColors.ENDC}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print(f"{TestColors.OKGREEN}{TestColors.BOLD}🎉 ALL TESTS PASSED!{TestColors.ENDC}")
    else:
        print(f"{TestColors.FAIL}{TestColors.BOLD}⚠️  SOME TESTS FAILED{TestColors.ENDC}")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
