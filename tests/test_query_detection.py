import json
from src.modules.oracle import Oracle
from src.modules.types import QueryType

def test_query_detection_accuracy():
    oracle = Oracle()
    
    with open("tests/data/query_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    total = len(dataset)
    correct = 0
    failures = []
    
    for item in dataset:
        detected = oracle.detect_query_type(item["query"])
        expected = QueryType(item["expected_type"])
        
        if detected == expected:
            correct += 1
        else:
            failures.append({
                "query": item["query"],
                "expected": expected.value,
                "detected": detected.value
            })
            
    accuracy = (correct / total) * 100
    print(f"\nDetection Accuracy: {accuracy:.2f}% ({correct}/{total})")
    
    if failures:
        print("\nFailures:")
        for f in failures:
            print(f"  Q: {f['query']} | E: {f['expected']} | D: {f['detected']}")
            
    assert accuracy >= 80.0  # We want at least 80% accuracy with simple heuristics

if __name__ == "__main__":
    test_query_detection_accuracy()
