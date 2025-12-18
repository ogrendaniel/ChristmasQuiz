"""
Test script for answer validation
"""

from answer_validator import validate_answer, get_validation_rule

# Test cases for various questions
test_cases = [
    # Lucka 1: Cloetta
    (1, "Cloetta", True, "Exact match"),
    (1, "cloetta", True, "Case insensitive"),
    (1, "Cloeta", True, "1 character typo allowed"),
    (1, "Cloeta", True, "Missing one t"),
    (1, "Clotta", True, "1 edit distance (substitute)"),
    (1, "Clotta", True, "Actually only 1 typo away"),
    (1, "Fazer", False, "Wrong answer"),
    
    # Lucka 12: Route 66 - should be STRICT
    (12, "Route 66", True, "Exact match"),
    (12, "route 66", True, "Case insensitive"),
    (12, "Route 67", False, "Wrong number - must reject"),
    (12, "Route 65", False, "Wrong number - must reject"),
    
    # Lucka 13: Lux - should be VERY STRICT
    (13, "Lux", True, "Exact match"),
    (13, "lux", True, "Case insensitive"),
    (13, "Luxi", False, "Extra character - must reject"),
    (13, "Luz", False, "Wrong letter - must reject"),
    
    # Lucka 5: Three stars (any order)
    (5, "Polstjärnan, Sirius, Dödsstjärnan", True, "Correct order"),
    (5, "Sirius, Dödsstjärnan, Polstjärnan", True, "Different order"),
    (5, "Dödsstjärnan och Sirius och Polstjärnan", True, "Using 'och'"),
    (5, "Death Star, Sirius, North Star", True, "English names"),
    (5, "Dodsstjarnan, Sirius, Polstjarnan", True, "Without Swedish characters"),
    (5, "Sirius, Polstjärnan", False, "Missing one star"),
    
    # Lucka 6: Any of the last 6 years
    (6, "Unisexdoft", True, "2024 answer"),
    (6, "Sällskapsspel", True, "2023 answer"),
    (6, "Mobillåda", True, "2019 answer"),
    (6, "Stormköket", True, "2020 answer"),
    (6, "Robotdammsugare", False, "Not in the list"),
    
    # Lucka 8: For and While
    (8, "for och while", True, "Swedish conjunction"),
    (8, "while, for", True, "Different order"),
    (8, "for-loop and while-loop", True, "With 'loop' suffix"),
    (8, "for", False, "Only one loop type"),
    
    # Lucka 9: Numeric with tolerance
    (9, "110 km/h", True, "Exact with unit"),
    (9, "110", True, "Exact without unit"),
    (9, "115 km/h", True, "Within tolerance"),
    (9, "105", True, "Within tolerance lower"),
    (9, "130", False, "Outside tolerance"),
    (9, "90", False, "Too low"),
    
    # Lucka 10: Nobel prizes - must be exact
    (10, "6", True, "Correct number"),
    (10, "sex", True, "Swedish word for six"),
    (10, "six", True, "English word"),
    (10, "5", False, "Wrong number - must reject"),
    (10, "7", False, "Wrong number - must reject"),
    
    # Lucka 16: Two bridges
    (16, "Golden Gate och Tower Bridge", True, "Both bridges"),
    (16, "Tower Bridge, Golden Gate Bridge", True, "Reverse order with full name"),
    (16, "Golden Gate", False, "Only one bridge"),
    
    # Lucka 18: Three gifts (any order)
    (18, "guld, rökelse, myrra", True, "Swedish, correct order"),
    (18, "myrrh, gold, frankincense", True, "English, different order"),
    (18, "myrra och guld och rökelse", True, "Swedish with 'och'"),
    (18, "gold, incense, myrrh", True, "Alternative English"),
    (18, "guld, rökelse", False, "Only two gifts"),
    
    # Lucka 20: Share screen
    (20, "Share screen", True, "Exact"),
    (20, "share", True, "Just share"),
    (20, "screen sharing", True, "Alternative wording"),
    (20, "camera", False, "Wrong button"),
    
    # Lucka 23: Five colors
    (23, "röd, lila, grön, gul, blå", True, "All five in Swedish"),
    (23, "red, purple, green, yellow, blue", True, "All five in English"),
    (23, "blå, gul, röd, grön, lila", True, "Different order"),
    (23, "rod, lila, gron, gul, bla", True, "Without Swedish characters"),
    (23, "röd, lila, grön, gul", False, "Only four colors"),
    (23, "röd, röd, grön, grön, lila", False, "Duplicates - must reject"),
    (23, "röd, lila, grön, gul, rosa", False, "Rosa is not a valid color"),
]

def run_tests():
    """Run all test cases and report results"""
    passed = 0
    failed = 0
    
    print("=" * 80)
    print("RUNNING ANSWER VALIDATION TESTS")
    print("=" * 80)
    
    for day, answer, expected_correct, description in test_cases:
        rule = get_validation_rule(day)
        if not rule:
            print(f"⚠️  Day {day}: No rule found!")
            failed += 1
            continue
        
        result = validate_answer(answer, rule)
        is_correct = result["is_correct"]
        
        if is_correct == expected_correct:
            print(f"✓ Day {day:2d}: {description:40s} | '{answer}' → {result['reasoning']}")
            passed += 1
        else:
            print(f"✗ Day {day:2d}: {description:40s} | '{answer}'")
            print(f"         Expected: {expected_correct}, Got: {is_correct}")
            print(f"         Reasoning: {result['reasoning']}")
            failed += 1
    
    print("=" * 80)
    print(f"RESULTS: {passed} passed, {failed} failed out of {passed + failed} tests")
    print("=" * 80)
    
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
