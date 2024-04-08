import nbformat
import re
import json


def generate_suggestion(messages, client):
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    print("GPT Called!")
    return completion.choices[0].message.content

import multiprocessing
import traceback

def run_code(code):
    try:
        # Try to compile the code first to catch syntax errors
        compiled_code = compile(code, '<string>', 'exec')
    except Exception as e:
        return 1,e

    try:
        # Execute the compiled code
        exec(compiled_code)
    except Exception as e:
        # Catch any execution errors
        return 2,e

    return 0,None

def code_runner(code, timeout=10):
    # Define a process to run the code
    process = multiprocessing.Process(target=run_code, args=(code,))
    process.start()
    process.join(timeout)

    # If the process is still active after the timeout, we assume it's an infinite loop
    if process.is_alive():
        process.terminate()
        process.join()
        return 3,None
    
    # Otherwise, run the code normally and return the result
    return run_code(code)


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

def add_test_cases(test_case_path, num):
    test_cases = read_from_json(test_case_path)

def get_program_output(n, f):
    # Capture the output of print_pattern
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    f(n)
    sys.stdout = old_stdout
    return redirected_output.getvalue()
    

def convert_to_template(question_str, code, solution, error_num, error):
    # INPUT_PROMPT = f"Question:\n{question_str}\n\nStudent Answer:\n{code}\n\n{error_m}{first_line}.You are encouraged to ask questions to the student and show simple related examples to lead the student in the right direction to figure out the answer on their own.  Be concise in your response. DO NOT INCLUDE CODE OR THE ACTUAL ANSWER IN YOUR RESPONSE." 
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