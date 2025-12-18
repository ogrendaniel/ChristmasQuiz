"""
Demo script to show how the validation system works
"""

from answer_validator import validate_answer, get_validation_rule

def demo_validation():
    """Demonstrate validation for various questions"""
    
    print("=" * 80)
    print("CHRISTMAS QUIZ ANSWER VALIDATION DEMO")
    print("=" * 80)
    print()
    
    # Demo examples
    examples = [
        (1, "Cloetta", "✅ Exact match for company name"),
        (1, "cloeta", "✅ Typo tolerance (missing 't')"),
        (5, "Sirius, Death Star, Polstjärnan", "✅ Three stars in any order"),
        (5, "Sirius och Dödsstjärnan", "❌ Only 2 stars (need 3)"),
        (8, "for, while", "✅ Both loop types"),
        (9, "115 km/h", "✅ Within 10 km/h tolerance"),
        (9, "130", "❌ Outside tolerance range"),
        (18, "gold, myrrh, frankincense", "✅ Three gifts in any order"),
        (18, "guld och rökelse", "❌ Only 2 gifts (need 3)"),
        (23, "röd, lila, grön, gul, blå", "✅ All 5 colors"),
    ]
    
    for day, answer, expected in examples:
        rule = get_validation_rule(day)
        if not rule:
            print(f"Day {day}: No rule configured")
            continue
        
        result = validate_answer(answer, rule)
        status = "✅ CORRECT" if result["is_correct"] else "❌ INCORRECT"
        
        print(f"Day {day:2d}: '{answer}'")
        print(f"       {status}")
        print(f"       Reason: {result['reasoning']}")
        print(f"       Expected: {expected}")
        print()
    
    print("=" * 80)
    print("KEY BENEFITS:")
    print("=" * 80)
    print("✓ Fast rule-based validation (no AI needed for most answers)")
    print("✓ Handles lists in any order (Sirius, Death Star OR Death Star, Sirius)")
    print("✓ Typo tolerance (Cloeta → Cloetta)")
    print("✓ Multiple language support (guld/gold, rökelse/frankincense)")
    print("✓ Numeric ranges (110 ±10 km/h)")
    print("✓ AI only used as fallback for truly ambiguous answers")
    print("=" * 80)

if __name__ == "__main__":
    demo_validation()
