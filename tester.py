import io
import sys
import os
import json



# DO NOT MODIFY
<FUNCTION>

def run_tests(question, f):
    with open("test_cases.json", 'r') as file:
        test_cases = json.load(file)
    original_stdout = sys.stdout
    tcs = test_cases[question]
    for n, expected in tcs.items():
        n = int(n)
        sys.stdout = io.StringIO()  # Redirect stdout to capture print output
        f(n)
        output = sys.stdout.getvalue()
        sys.stdout = original_stdout  # Reset stdout back to original
        assert output.strip() == expected.strip(), f"Test failed for n={n}. \n\nExpected:\\n{expected}\\nActual:\\n{output}"
    print("All tests passed!")

question = <QUESTION>
run_tests(question, <FUNCTION_NAME>)