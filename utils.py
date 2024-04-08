import nbformat
import re
import json
import traceback
import multiprocessing
import sys
import io
import subprocess

test_code = """
import io
import sys

def run_tests():
    original_stdout = sys.stdout
    for n, expected in tcs.items():
        n = int(n)
        sys.stdout = io.StringIO()  # Redirect stdout to capture print output
        square_pattern(n)
        output = sys.stdout.getvalue()
        sys.stdout = original_stdout  # Reset stdout back to original
        assert output.strip() == expected.strip(), f"Test failed for n={n}. Expected:\\n{expected}\\nGot:\\n{output}"
    print("All tests passed.")
"""


def generate_suggestion(messages, client):
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    print("GPT Called!")
    return completion.choices[0].message.content

def modify_tester(code, q_key):
    # Read the original file
    with open('tester.py', 'r') as file:
        content = file.read()
    
    m = re.search("^def (.*)\(", code, re.MULTILINE)
    f_name = m.group(1)
    
    # Replace the placeholder with the replacement string
    content = content.replace('<FUNCTION>', code).replace("<QUESTION>", f"'{q_key}'").replace("<FUNCTION_NAME>", f_name)
    return content
    
    # Write the modified content back to the file (or a new file)
    # with open('temp/tester_temp.py', 'w') as file:
    #     file.write(content)

def run_code(q_key, code):
    try:
        # Try to compile the code first to catch syntax errors
        compiled_code = compile(code, '<string>', 'exec')
    except Exception as e:
        error_traceback = traceback.format_exc()
        return 1,error_traceback

    content = modify_tester(code, q_key)
    try:
        # scope = {}
        print(content)
        exec(content)
        
        # result = subprocess.run(['python3','temp/tester_temp.py',q_key], capture_output=True, text=True)
    except Exception as e:
        if isinstance(e, AssertionError):
            error_traceback = str(e).replace("\\n", "\n")
        else:
            error_traceback = traceback.format_exc()
        # Catch any execution errors and assertion errors for the test cases
        return 2,error_traceback

    # if result.stderr:
    #     assert_pattern = "AssertionError:(.*)"
    #     formatted_stderr = result.stderr.replace("\\n", "\n")
    #     match = re.search(assert_pattern, formatted_stderr, re.DOTALL)
    #     error_string = match.group(1).strip()
    #     return 2, error_string
    
    return 0,"All tests Passed!"

# def append_test_cases(test_cases, code):
    

def code_runner(code, q_key, timeout=10):
    # Define a process to run the code
    process = multiprocessing.Process(target=run_code, args=(q_key,code,))
    process.start()
    process.join(timeout)

    # If the process is still active after the timeout, we assume it's an infinite loop
    if process.is_alive():
        process.terminate()
        process.join()
        return 3,"Possible Infinite Loop"
    
    # Otherwise, run the code normally and return the result
    return run_code(q_key, code)


def remove_comments(code):
    # Pattern to match single-line comments
    pattern = re.compile(r'#.*?$|\'\'\'.*?\'\'\'|""".*?"""', re.DOTALL | re.MULTILINE)
    return re.sub(pattern, lambda m: "" if m.group(0).startswith('#') else m.group(0), code)

def extract_cells(notebook_path):
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    qs = {}
    cells = nb.cells
    for c in cells:
        src = c['source']
        if c['cell_type']=='markdown':
            q_match = re.search("\# Q(\d*)(.*)", src, re.DOTALL)
            if q_match:
                q_num = q_match.group(1)
                ques = q_match.group(2).strip()
                q_str = f"Q{q_num}"
                if q_str not in qs:
                    qs[q_str] = {}
                qs[q_str]['question'] = ques
        if c['cell_type']=='code':
            q_num = re.search("#q(.*)", src)
            if q_num:
                q_str = f"Q{q_num.group(1)}"
                code = remove_comments(src).strip()
                if q_str not in qs:
                    qs[q_str] = {}
                qs[q_str]['code'] = code
    return qs

def write_to_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def read_from_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data
    

def convert_to_template(question_str, code, solution, error_num, error):
    
    first_line = "Given above is a programming question, a canonical solution and the corresponding wrong answer from a student. Please give a helpful and polite explanation as to the next steps the student can take to improve their answer"
    if error_num==1:
        # Compilation Error
        first_line = "Given above is a programming question,a canonical solution, the error message from compiling the code, and the corresponding wrong answer from a student"
        
    elif error_num==2 or error_num==3:
        first_line = "Given above is a programming question, a canonical solution, the error message from executing the code against test cases, and the corresponding wrong answer from a student"
    error_m=''
    if error:
        error_m = f"Error:\n{error}\n\n"

    input_str = f"Question:\n{question_str}\n\nStudent Answer:\n{code}\n\nCanonical Solution:\n{solution}\n\n{error_m}{first_line}.You are encouraged to ask questions to the student and show simple related examples to lead the student in the right direction to figure out the answer on their own.  Be concise in your response. DO NOT INCLUDE CODE OR THE ACTUAL ANSWER IN YOUR RESPONSE. Start the response with something that encourages the student and commends the student on his/her progress towards the task. Do not make any mention about the canonical solution as the students will not have access to that."
    print(input_str)
    
    return [{"role": "system", "content": "You are a polite and helpful assistant to help students learn programming. You will be deployed in an application where you must display suggestions to the student. You will directly be addressing students and helping them make corrections in their code so that they can get it right. Do not speak about the student in the third person."},
    {"role": "user", "content": input_str}]