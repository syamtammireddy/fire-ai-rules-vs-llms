"""
Pytest suite for Task 3: Plain-Language NLP Parser.
Validates extraction from English and Hinglish text, and verifies that incomplete
or ambiguous text generates clarifying questions instead of guessing.
"""

import json
import pytest
from project_a.nlp_parser import parse_plain_language


@pytest.fixture(scope="module")
def nlp_cases():
    with open("project_a/tests/test_nlp_cases.json", "r") as f:
        return json.load(f)


def test_nlp_formal_english_complete(nlp_cases):
    """Verifies that clear, complete formal English parses without clarifying questions."""
    case = nlp_cases[0]  # NLP_01
    res = parse_plain_language(case["text"])
    assert res.is_complete is True
    assert res.parsed_input is not None
    assert res.parsed_input.gross_salary == 1200000
    assert res.parsed_input.investment_80c == 150000


def test_nlp_hinglish_complete(nlp_cases):
    """Verifies that complete Hinglish text parses accurately."""
    case = nlp_cases[20]  # NLP_21 (Hinglish 12 lakh Mumbai)
    res = parse_plain_language(case["text"])
    assert res.is_complete is True
    assert res.parsed_input is not None
    assert res.parsed_input.gross_salary == 1200000
    assert res.parsed_input.city.value == "metro"


def test_nlp_incomplete_triggers_questions(nlp_cases):
    """Verifies that incomplete descriptions trigger questions instead of guessing."""
    case = nlp_cases[30]  # NLP_31 ("I earn 8 lakhs")
    res = parse_plain_language(case["text"])
    # Should flag missing deductions/details or generate questions
    assert len(res.questions) > 0 or res.is_complete is False


def test_nlp_missing_gross_salary_triggers_question(nlp_cases):
    """Verifies that text without gross salary asks for salary."""
    case = nlp_cases[32]  # NLP_33 ("I pay 30,000 rent in Mumbai...")
    res = parse_plain_language(case["text"])
    assert res.is_complete is False
    assert any("salary" in q.question.lower() or "salary" in q.field.lower() for q in res.questions)
