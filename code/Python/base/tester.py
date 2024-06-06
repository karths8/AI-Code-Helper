import io
import sys
import os
import json

def run_tests(question, f):
    with open("/home/karthiksuresh/CS839-HCI-project/testing/test_cases.json", 'r') as file:
        test_cases = json.load(file)
    original_stdout = sys.stdout
    tcs = test_cases[question]
    for n, expected in tcs.items():
        n = int(n)
        sys.stdout = io.StringIO()  # Redirect stdout to capture print output
        f(n)
        output = sys.stdout.getvalue()
        sys.stdout = original_stdout  # Reset stdout back to original
        try:
            assert output.strip() == expected.strip()
        except Exception as e:
            print(f"Test failed for n={n}. \n\nExpected:\n{expected}\nActual:\n{output}")
            return
    print("All tests passed!")