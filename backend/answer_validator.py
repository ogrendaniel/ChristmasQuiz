"""
Answer validation system for quiz questions.
Uses rule-based validation first, with AI as fallback for complex cases.
"""

import re
from typing import Dict, List, Tuple, Optional
from enum import Enum


class ValidationType(Enum):
    """Types of validation strategies"""
    EXACT = "exact"           # Exact string match
    CONTAINS = "contains"     # Answer contains key terms
    LIST = "list"             # Multiple items in any order
    NUMERIC = "numeric"       # Numeric value with tolerance
    ANY_OF = "any_of"         # Any one of multiple correct answers
    AI = "ai"                 # AI validation only


class ValidationRule:
    """Defines how to validate an answer"""
    
    def __init__(
        self,
        validation_type: ValidationType,
        correct_answers: List[str],
        tolerance: float = 0,
        case_sensitive: bool = False,
        min_items: int = 0,
        max_items: int = 999,
        description: str = ""
    ):
        self.validation_type = validation_type
        self.correct_answers = correct_answers
        self.tolerance = tolerance
        self.case_sensitive = case_sensitive
        self.min_items = min_items  # For LIST type: minimum required items
        self.max_items = max_items  # For LIST type: maximum allowed items
        self.description = description


def levenshtein_distance(s1: str, s2: str) -> int:
    """
    Calculate Levenshtein distance between two strings.
    Used for typo tolerance.
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def normalize_text(text: str, case_sensitive: bool = False) -> str:
    """Normalize text for comparison"""
    text = text.strip()
    if not case_sensitive:
        text = text.lower()
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text


def split_list_answer(text: str) -> List[str]:
    """
    Split answer into list items.
    Handles various separators: comma, semicolon, "och", "and", etc.
    """
    # Split by common separators
    items = re.split(r'[,;]|\s+och\s+|\s+and\s+|\s+&\s+', text, flags=re.IGNORECASE)
    # Clean and filter empty items
    items = [item.strip() for item in items]
    items = [item for item in items if len(item) > 0]
    return items


def strings_match_fuzzy(s1: str, s2: str, max_distance: int = 2, allow_contains: bool = True) -> bool:
    """
    Check if two strings match allowing for small typos.
    Returns True if strings are similar enough.
    """
    # Exact match
    if s1 == s2:
        return True
    
    # Check if one contains the other (for partial matches) - only if allowed
    if allow_contains and (s1 in s2 or s2 in s1):
        return True
    
    # Check Levenshtein distance for typos
    distance = levenshtein_distance(s1, s2)
    return distance <= max_distance


def validate_exact(user_answer: str, rule: ValidationRule) -> Tuple[bool, str]:
    """Validate exact match - STRICT, NO typo tolerance unless tolerance is explicitly set"""
    normalized = normalize_text(user_answer, rule.case_sensitive)
    
    for correct in rule.correct_answers:
        correct_normalized = normalize_text(correct, rule.case_sensitive)
        if normalized == correct_normalized:
            return True, "Exact match"
        
        # Only allow typos if tolerance is explicitly set (for longer words like "Cloetta")
        # Default tolerance is 0, meaning NO typos allowed
        if rule.tolerance > 0:
            distance = levenshtein_distance(normalized, correct_normalized)
            if distance <= rule.tolerance:
                return True, f"Match with minor spelling difference (within tolerance {rule.tolerance})"
    
    return False, "Does not match expected answer"


def validate_contains(user_answer: str, rule: ValidationRule) -> Tuple[bool, str]:
    """Validate that answer contains key terms"""
    normalized = normalize_text(user_answer, rule.case_sensitive)
    
    matched_terms = []
    for term in rule.correct_answers:
        term_normalized = normalize_text(term, rule.case_sensitive)
        if term_normalized in normalized or normalized in term_normalized:
            matched_terms.append(term)
            continue
        
        # Check with fuzzy matching
        for word in normalized.split():
            if strings_match_fuzzy(word, term_normalized):
                matched_terms.append(term)
                break
    
    if matched_terms:
        return True, f"Contains key term(s): {', '.join(matched_terms)}"
    
    return False, "Missing required terms"


def validate_list(user_answer: str, rule: ValidationRule) -> Tuple[bool, str]:
    """
    Validate list of items (order doesn't matter).
    The rule.correct_answers contains ALL acceptable variations.
    We match each user item against the acceptable list.
    IMPORTANT: Checks for duplicates - each item should be unique.
    """
    user_items = split_list_answer(user_answer)
    user_items_normalized = [normalize_text(item, rule.case_sensitive) for item in user_items]
    
    if not user_items:
        return False, "No items provided"
    
    # Check for duplicates in user's answer
    unique_items = set(user_items_normalized)
    if len(unique_items) < len(user_items_normalized):
        duplicates = [item for item in user_items_normalized if user_items_normalized.count(item) > 1]
        return False, f"Duplicate items found: {', '.join(set(duplicates))}"
    
    # Check count requirements (must match unique items)
    if rule.min_items > 0 and len(unique_items) < rule.min_items:
        return False, f"Need at least {rule.min_items} unique items, provided {len(unique_items)}"
    
    if rule.max_items < 999 and len(unique_items) > rule.max_items:
        return False, f"Too many items: maximum {rule.max_items}, provided {len(unique_items)}"
    
    # Normalize all correct answers
    correct_answers_normalized = [normalize_text(item, rule.case_sensitive) for item in rule.correct_answers]
    
    # Check if all user items are valid (match something in the correct list)
    # Track which correct answers have been matched to prevent matching same concept twice
    matched_correct_items = set()
    matched_user_items = []
    invalid_items = []
    
    for user_item in user_items_normalized:
        found_match = False
        for correct_item in correct_answers_normalized:
            # For lists, be stricter: only allow 1 character typo or exact match
            # Don't allow partial "contains" matching
            if user_item == correct_item:
                # Exact match
                matched_correct_items.add(correct_item)
                matched_user_items.append(user_item)
                found_match = True
                break
            elif levenshtein_distance(user_item, correct_item) <= 1:
                # Very close typo (only 1 character off)
                matched_correct_items.add(correct_item)
                matched_user_items.append(user_item)
                found_match = True
                break
        
        if not found_match:
            invalid_items.append(user_item)
    
    # If user provided any invalid items, it's wrong
    if invalid_items:
        return False, f"Invalid item(s): {', '.join(invalid_items)}"
    
    # All user items are valid - success!
    return True, f"All {len(matched_user_items)} items matched (order independent)"


def validate_numeric(user_answer: str, rule: ValidationRule) -> Tuple[bool, str]:
    """Validate numeric answer with tolerance"""
    # Extract number from user answer
    numbers = re.findall(r'-?\d+\.?\d*', user_answer)
    
    if not numbers:
        return False, "No numeric value found in answer"
    
    try:
        user_value = float(numbers[0])
        target_value = float(rule.correct_answers[0])
        
        difference = abs(user_value - target_value)
        
        if difference <= rule.tolerance:
            if difference == 0:
                return True, f"Exact numeric match: {user_value}"
            else:
                return True, f"Within tolerance: {user_value} (±{rule.tolerance})"
        
        return False, f"Outside acceptable range: {user_value} vs {target_value} (±{rule.tolerance})"
    
    except ValueError:
        return False, "Invalid numeric format"


def validate_any_of(user_answer: str, rule: ValidationRule) -> Tuple[bool, str]:
    """Validate that answer matches any one of the acceptable answers"""
    normalized = normalize_text(user_answer, rule.case_sensitive)
    
    for correct in rule.correct_answers:
        correct_normalized = normalize_text(correct, rule.case_sensitive)
        
        # Check if user answer contains this option
        if correct_normalized in normalized or strings_match_fuzzy(normalized, correct_normalized):
            return True, f"Matched acceptable answer: {correct}"
    
    return False, "Does not match any acceptable answer"


def validate_answer(user_answer: str, rule: ValidationRule) -> Dict:
    """
    Main validation function.
    Returns dict with: is_correct, confidence, reasoning, method
    """
    # Handle empty answers
    if not user_answer or not user_answer.strip():
        return {
            "is_correct": False,
            "confidence": 100,
            "reasoning": "Empty answer",
            "method": "rule_based"
        }
    
    # Route to appropriate validation method
    if rule.validation_type == ValidationType.EXACT:
        is_correct, reasoning = validate_exact(user_answer, rule)
    elif rule.validation_type == ValidationType.CONTAINS:
        is_correct, reasoning = validate_contains(user_answer, rule)
    elif rule.validation_type == ValidationType.LIST:
        is_correct, reasoning = validate_list(user_answer, rule)
    elif rule.validation_type == ValidationType.NUMERIC:
        is_correct, reasoning = validate_numeric(user_answer, rule)
    elif rule.validation_type == ValidationType.ANY_OF:
        is_correct, reasoning = validate_any_of(user_answer, rule)
    elif rule.validation_type == ValidationType.AI:
        # Return None to signal that AI validation should be used
        return None
    else:
        return {
            "is_correct": False,
            "confidence": 0,
            "reasoning": f"Unknown validation type: {rule.validation_type}",
            "method": "error"
        }
    
    return {
        "is_correct": is_correct,
        "confidence": 100 if is_correct else 0,
        "reasoning": reasoning,
        "method": "rule_based"
    }


# ============================================================================
# QUESTION-SPECIFIC VALIDATION RULES
# ============================================================================

QUESTION_RULES: Dict[int, ValidationRule] = {
    # Lucka 1: Cloetta (exact match with 1 typo tolerance for longer word)
    1: ValidationRule(
        ValidationType.EXACT,
        ["Cloetta"],
        tolerance=1,  # Allow 1 typo for longer brand names
        description="Company that sells juleskum"
    ),
    
    # Lucka 2: Swedish translations of Finnish and French words (list)
    # Answer should be the SWEDISH words: docka, leksaksbil, tv-spel, fotbollströja
    2: ValidationRule(
        ValidationType.LIST,
        ["docka", "doll", "leksaksbil", "leksaksbilbil", "toy car", 
         "tv-spel", "tvspel", "tv spel", "videospel", "video game", "video games",
         "fotbollströja", "fotbollstroja", "football shirt", "soccer jersey"],
        min_items=4,
        max_items=4,
        description="Swedish translations of toy items"
    ),
    
    # Lucka 3: January 6 / Trettondedag jul
    3: ValidationRule(
        ValidationType.CONTAINS,
        ["6 januari", "januari 6", "trettondedag", "día de los reyes", "dia de los reyes"],
        description="Date when Spanish children get presents"
    ),
    
    # Lucka 4: Menora
    4: ValidationRule(
        ValidationType.EXACT,
        ["Menora", "Menorah"],
        description="Jewish candlestick"
    ),
    
    # Lucka 5: Three stars (list) - needs exactly 3 stars
    5: ValidationRule(
        ValidationType.LIST,
        # Group synonyms: Polstjärnan|North Star, Sirius, Dödsstjärnan|Death Star
        ["polstjärnan", "polstjarnan", "north star", "sirius", "dödsstjärnan", 
         "dodsstjarnan", "death star"],
        min_items=3,
        max_items=3,
        description="Navigation star, brightest star, and Star Wars station"
    ),
    
    # Lucka 6: Any recent "Årets julklapp" (any_of)
    6: ValidationRule(
        ValidationType.ANY_OF,
        ["Unisexdoft", "Unisexdoften", "Sällskapsspel", "Sallskapsspel", 
         "Sällskapsspelet", "hemstickade", "hemstickade plagget", 
         "Evenemangsbiljett", "Evenemangsbiljetten", "Stormkök", "Stormkok", 
         "Stormköket", "Mobillåda", "Mobilladan", "Mobillådan"],
        description="Any of the last 6 years' Christmas gift trends"
    ),
    
    # Lucka 7: Cheopspyramiden
    7: ValidationRule(
        ValidationType.EXACT,
        ["Cheopspyramiden", "Keopspyramiden", "Great Pyramid", "Giza pyramid", 
         "Pyramid of Giza", "Pyramid of Cheops", "Pyramid of Khufu"],
        description="Only remaining ancient wonder"
    ),
    
    # Lucka 8: For and While loops
    8: ValidationRule(
        ValidationType.LIST,
        ["for", "while", "for-loop", "while-loop", "for loop", "while loop"],
        min_items=2,
        max_items=2,
        description="Two main types of programming loops"
    ),
    
    # Lucka 9: Cheetah speed ~110 km/h (numeric with tolerance)
    9: ValidationRule(
        ValidationType.NUMERIC,
        ["110"],
        tolerance=5,
        description="Cheetah top speed in km/h"
    ),
    
    # Lucka 10: Six Nobel prizes - must be exact
    10: ValidationRule(
        ValidationType.EXACT,
        ["6", "sex", "six", "6 stycken", "sex stycken"],
        tolerance=0,  # No typos for numbers
        description="Number of Nobel prizes"
    ),
    
    # Lucka 11: Eva
    11: ValidationRule(
        ValidationType.EXACT,
        ["Eva"],
        description="Name day on Christmas Eve"
    ),
    
    # Lucka 12: Route 66
    12: ValidationRule(
        ValidationType.EXACT,
        ["Route 66", "Route66", "Highway 66"],
        description="Famous US highway"
    ),
    
    # Lucka 13: Lux
    13: ValidationRule(
        ValidationType.EXACT,
        ["Lux"],
        description="Latin word for light"
    ),
    
    # Lucka 14: Iran
    14: ValidationRule(
        ValidationType.EXACT,
        ["Iran"],
        description="Country producing 90% of saffron"
    ),
    
    # Lucka 15: I jultomtens verkstad
    15: ValidationRule(
        ValidationType.CONTAINS,
        ["i jultomtens verkstad","jultomtens verkstad", "Santa's Workshop", "Santas Workshop"],
        description="First segment in Kalle Anka"
    ),
    
    # Lucka 16: Golden Gate and Tower Bridge
    16: ValidationRule(
        ValidationType.LIST,
        ["Golden Gate", "Golden Gate Bridge", "Tower Bridge"],
        min_items=2,
        max_items=2,
        description="Two famous bridges"
    ),
    
    # Lucka 17: Atlanta
    17: ValidationRule(
        ValidationType.EXACT,
        ["Atlanta"],
        description="City with world's busiest airport"
    ),
    
    # Lucka 18: Gold, frankincense, myrrh
    18: ValidationRule(
        ValidationType.LIST,
        ["guld", "gold", "rökelse", "rokelse", "frankincense", "incense", 
         "myrra", "myrrh"],
        min_items=3,
        max_items=3,
        description="Three gifts to baby Jesus"
    ),
    
    # Lucka 19: Wuhan
    19: ValidationRule(
        ValidationType.EXACT,
        ["Wuhan"],
        description="City where COVID-19 was first reported"
    ),
    
    # Lucka 20: Share screen
    20: ValidationRule(
        ValidationType.CONTAINS,
        ["share screen", "share", "screen","dela skärm", "dela skarm","skärmdelning"],
        description="Green button in Zoom"
    ),
    
    # Lucka 21: Winter solstice / shortest day
    21: ValidationRule(
        ValidationType.CONTAINS,
        ["vintersolstånd", "vintersolstand", "solstice", "kortaste dag", 
         "kortaste dagen", "shortest day"],
        description="Special about December 21"
    ),
    
    # Lucka 22: Moment 22 / Catch-22
    22: ValidationRule(
        ValidationType.EXACT,
        ["Moment 22", "Catch-22", "Catch 22"],
        description="Paradoxical situation name"
    ),
    
    # Lucka 23: Five colors in Bingolotto (list)
    23: ValidationRule(
        ValidationType.LIST,
        ["röd", "rod", "red", "lila", "purple", "grön", "gron", "green", 
         "gul", "yellow", "blå", "bla", "blue"],
        min_items=5,
        max_items=5,
        description="Five colors in Färgfemman"
    ),
    
    # Lucka 24: Japan
    24: ValidationRule(
        ValidationType.EXACT,
        ["Japan"],
        description="Country with world's most-sold newspaper"
    ),
}


def get_validation_rule(day_number: int) -> Optional[ValidationRule]:
    """Get the validation rule for a specific day"""
    return QUESTION_RULES.get(day_number)
