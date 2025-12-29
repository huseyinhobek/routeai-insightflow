#!/usr/bin/env python3
"""
Test script for intent classification service
"""
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_intent_classification():
    """Test intent classification service"""
    try:
        from services.intent_classification_service import intent_classification_service
        
        # Test questions
        test_questions = [
            # Decision intent (should be detected)
            ("hangisini seçmeli", True),
            ("which option is best", True),
            ("en iyi seçenek hangisi", True),
            ("should I choose plan A or B", True),
            ("hangi planı seçmeliyim", True),
            ("what is the most logical choice", True),
            
            # Structured intent (should NOT be detected as decision)
            ("what is the distribution", False),
            ("how many people chose option A", False),
            ("dağılım nedir", False),
            
            # RAG intent (should NOT be detected as decision)
            ("why did they choose", False),
            ("neden seçtiler", False),
        ]
        
        print("=" * 80)
        print("Testing Intent Classification Service")
        print("=" * 80)
        print()
        
        results = []
        for question, expected_decision in test_questions:
            try:
                result = intent_classification_service.detect_decision_intent(
                    question_text=question,
                    threshold=0.65
                )
                
                has_decision = result.get("has_decision_intent", False)
                similarity = result.get("similarity_score", 0.0)
                method = result.get("method", "unknown")
                matched_keywords = result.get("matched_keywords", [])
                
                status = "✅" if has_decision == expected_decision else "❌"
                
                print(f"{status} Question: '{question}'")
                print(f"   Expected decision: {expected_decision}, Got: {has_decision}")
                print(f"   Similarity: {similarity:.3f}, Method: {method}")
                if matched_keywords:
                    print(f"   Keywords: {matched_keywords}")
                print()
                
                results.append({
                    "question": question,
                    "expected": expected_decision,
                    "got": has_decision,
                    "similarity": similarity,
                    "method": method,
                    "correct": has_decision == expected_decision
                })
                
            except Exception as e:
                print(f"❌ Error testing '{question}': {e}")
                logger.exception(e)
                results.append({
                    "question": question,
                    "expected": expected_decision,
                    "got": None,
                    "error": str(e),
                    "correct": False
                })
        
        # Summary
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        correct = sum(1 for r in results if r.get("correct", False))
        total = len(results)
        print(f"Correct: {correct}/{total} ({correct/total*100:.1f}%)")
        print()
        
        # Show incorrect results
        incorrect = [r for r in results if not r.get("correct", False)]
        if incorrect:
            print("Incorrect results:")
            for r in incorrect:
                print(f"  - '{r['question']}': Expected {r['expected']}, Got {r.get('got')}")
        
        return correct == total
        
    except Exception as e:
        print(f"❌ Error importing or running intent classification service: {e}")
        logger.exception(e)
        return False


if __name__ == "__main__":
    success = test_intent_classification()
    sys.exit(0 if success else 1)

