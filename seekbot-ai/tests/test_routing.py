import os
import sys

# Add the parent directory to sys.path so app can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.intent_service import detect_intent

def test_intent_application_strategy():
    queries = [
        "What jobs should I apply for first?",
        "Which opportunities should I prioritize?",
        "Am I ready to apply?",
        "Create an application strategy for me.",
        "What should I focus on before applying?",
        "What jobs should I apply to this week?",
        "Which opportunities are realistic for me?",
        "What should I learn before applying?"
    ]
    for q in queries:
        intent = detect_intent(q)
        assert intent == "application_strategy", f"Failed for query '{q}', got {intent}"

def test_intent_job_recommendation():
    queries = [
        "Recommend jobs for me",
        "Show backend jobs",
        "What are some good jobs for me?"
    ]
    for q in queries:
        intent = detect_intent(q)
        # "Show backend jobs" might go to "job_search" or "job_recommendation", depending on rules.
        # "Recommend jobs for me" -> job_recommendation.
        # Let's check specifically for the ones the prompt requires.
        pass

def run_tests():
    test_intent_application_strategy()
    
    assert detect_intent("Recommend jobs for me") == "job_recommendation"
    
    # Check if 'Show backend jobs' goes to job_recommendation
    # If not, the test will fail and I can see the result.
    assert detect_intent("Show backend jobs") == "job_recommendation", "Expected 'Show backend jobs' to map to job_recommendation"
    
    print("All routing tests passed successfully!")

if __name__ == "__main__":
    run_tests()
