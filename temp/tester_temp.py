import io
import sys
import os
import json

with open("test_cases.json", 'r') as file:
    test_cases = json.load(file)

# DO NOT MODIFY
def square_pattern(n:int):
    for i in range(n):
        print("*"*n)

def run_tests(question):
    original_stdout = sys.stdout
    tcs = test_cases[question]
    for n, expected in tcs.items():
        n = int(n)
        sys.stdout = io.StringIO()  # Redirect stdout to capture print output
        square_pattern(n)
        output = sys.stdout.getvalue()
        sys.stdout = original_stdout  # Reset stdout back to original
        assert output.strip() == expected.strip(), f"Test failed for n={n}. \n\nExpected:\\n{expected}\\nActual:\\n{output}"
    print("All tests passed!")

if __name__=="__main__":
    question = sys.argv[1]
    # try:
    print("RUNNING TESTS")
    run_tests(question)
    # except AssertionError as e:
    #     # tester_json = read_from_json('tester_output.json')
    #     print(str(e).replace("\\n", "\n"))