import nbformat
import re
import json
import traceback
import multiprocessing
import sys
import io
import subprocess
import time
import os

def make_directory(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        print(f"Directory created at {dir_path}")
    else:
        print(f"Directory already exists at {dir_path}")

def generate_suggestion(messages, client, model):
    start_time = time.time()
    completion = client.chat.completions.create(
      model=model,
      messages=messages
    )
    # temp_var = completion.choices[0].message.content
    completion = convert_python(completion.choices[0].message.content)
    end_time = time.time()
    execution_time = end_time - start_time
    execution_time = round(execution_time, 3)
    print(f"Time For LLM Call: {execution_time} seconds")
    print("LLM Called!")
    return completion, execution_time

def modify_tester(code, q_key):
    # Read the original file
    with open('testing/tester.py', 'r') as file:
        content = file.read()
    
    m = re.search("^def (.*)\(", code, re.MULTILINE)
    f_name = m.group(1)
    
    # Replace the placeholder with the replacement string
    content = content.replace('<FUNCTION>', code).replace("<QUESTION>", f"'{q_key}'").replace("<FUNCTION_NAME>", f_name)
    return content

def run_code_python(q_key, code):
    try:
        # Try to compile the code first to catch syntax errors
        compiled_code = compile(code, '<string>', 'exec')
    except Exception as e:
        error_traceback = traceback.format_exc()
        return 1,error_traceback

    content = modify_tester(code, q_key)
    try:
        print(content)
        exec(content)
    except Exception as e:
        if isinstance(e, AssertionError):
            error_traceback = str(e).replace("\\n", "\n")
        else:
            error_traceback = traceback.format_exc()
        # Catch any execution errors and assertion errors for the test cases
        return 2,error_traceback
    
    return 0,"All tests Passed!"

def check_test_cases_java(output, q_key):
    q_dict = {1:1, 2:2, 3:5, 4:7}
    test_cases = read_from_json('testing/test_cases.json')[q_key]
    outputs = re.findall("<TC(\d)>([\s\S]*?)<\/TC\d>", output)
    outputs = {q_dict[int(k)]:v.strip() for k,v in outputs}
    for i in test_cases:
        print(test_cases[i])
        print(outputs)
        if test_cases[i].strip()!=outputs[int(i)]:
            return f"Test failed for n={str(i)}. \n\nExpected:\n{test_cases[i].strip()}\nActual:\n{outputs[int(i)]}"
    return None


def run_code_java(q_key):
    print(f"Running java program {q_key}")
    result = subprocess.run(['java', f'code/Java/{q_key}.java'], capture_output=True, text=True)
    err = result.stderr
    if err:
        return 1, err
    tc_err = check_test_cases_java(result.stdout, q_key)
    if tc_err:
        return 2,tc_err
    
    return 0,"All tests Passed!"

# def append_test_cases(test_cases, code):
def code_runner_java(q_key,timeout=10):
    # Define a process to run the code
    # process = multiprocessing.Process(target=run_code_java, args=(q_key,))
    # process.start()
    # process.join(timeout)

    # # If the process is still active after the timeout, we assume it's an infinite loop
    # if process.is_alive():
    #     process.terminate()
    #     process.join()
    #     return 3,"Possible Infinite Loop"
    
    # Otherwise, run the code normally and return the result
    return run_code_java(q_key)
    

def code_runner_python(code, q_key,timeout=10):
    # Define a process to run the code
    process = multiprocessing.Process(target=run_code_python, args=(q_key,code,))
    process.start()
    process.join(timeout)

    # If the process is still active after the timeout, we assume it's an infinite loop
    if process.is_alive():
        process.terminate()
        process.join()
        return 3,"Possible Infinite Loop"
    
    # Otherwise, run the code normally and return the result
    return run_code_python(q_key, code)


def remove_comments(code):
    # Pattern to match single-line comments
    pattern = re.compile(r'#.*?$|\'\'\'.*?\'\'\'|""".*?"""', re.DOTALL | re.MULTILINE)
    return re.sub(pattern, lambda m: "" if m.group(0).startswith('#') else m.group(0), code)

def extract_java_code(path):
    qs = {}
    for f in os.listdir(path):
        t = re.search('(Q\d).java', f)
        if t:
            f_path = os.path.join(path, f)
            with open(f_path, 'r') as file:
                contents = file.read()
            qs[t.group(1)] = {'code':contents}
    return qs
            
            

def extract_code(path, lang):
    py_qs = extract_cells(path['Python'])
    print(py_qs)
    if lang=='Python':
        return py_qs
    else:
        java_qs = extract_java_code(path['Java'])
        for i in java_qs:
            for j in py_qs:
                if i==j:
                    java_qs[i]['example'] = py_qs[j]['example']
                    java_qs[i]['question'] = py_qs[j]['question']
        return java_qs
    


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
        if c['cell_type']=='raw':
            q_match = re.search("Q(\d*)", src)
            if q_match:
                q_num = q_match.group(1)
                q_str = f"Q{q_num}"
                t = {k:v for k,v in c.items() if k=='source'}
                content = None if 'source' not in t else t['source']
                if content:
                    qs[q_str]['example'] = content
    return qs

def write_to_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def read_from_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data

def convert_python(markdown_text):
    # Pattern to find Markdown code blocks
    pattern = r'```python(.*?)```'
    replacement = r'<code class="python medium-text"><pre>\1<pre></code>'
    html_text = re.sub(pattern, replacement, markdown_text, flags=re.DOTALL)
    return html_text

def convert_to_template(question_str, code, solution, error_num, error, example):
    question_str_modified = f"{question_str}\n\n{example}"
    
    first_line = "Given below is a programming question, the Instructors solution and the corresponding wrong answer from a student. Please give a helpful and polite explanation as to the next steps the student can take to improve their answer"
    if error_num==1:
        # Compilation Error
        first_line = "Given below is a programming question, the Instructors solution, the error message from running or compiling the code, and the corresponding wrong answer from a student"
        
    elif error_num==2 or error_num==3:
        first_line = "Given below is a programming question, the Instructors solution, the error message from executing the code against test cases, and the corresponding wrong answer from a student"
    error_m=''
    if error:
        error_m = f"Error:\n{error}\n\n"
    input_str = f"Question:\n{question_str_modified}\n\nStudent Answer:\n{code}\n\n{error_m}Instructors Solution:\n{solution}\n\n Suggestion:"
    system_str = f"You are a polite and helpful assistant to help students learn programming. You will be deployed in an application where you must display suggestions to the student under the heading \"Suggestion:\". You will directly be addressing students and helping them make corrections in their code so that they can get it right. Do not speak about the student in the third person. {first_line}.You are encouraged to ask questions to the student and show simple related examples to lead the student in the right direction to figure out the answer on their own. DO NOT INCLUDE CODE OR THE ACTUAL ANSWER IN YOUR RESPONSE. Start the response with something that encourages the student and commends the student on his/her progress towards the task. Be concise in your response and do not overwhelm the student with information. Do not make any mention about the Instructors solution as the students will not have access to that."
    messages = [{"role": "system", "content": system_str},
    {"role": "user", "content": input_str}]

    # print(json.dumps(messages, indent=4))
    for i in messages:
        print(i['role'])
        print(i['content'])
    
    return messages