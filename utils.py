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
    if 'claude' in model:
        completion = client.messages.create(
            model=model,
            max_tokens = 500,
            system=messages[0]['content'],
            messages=messages[1:]
        )

        completion = convert_python(completion.content[0].text)

    else:
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
    return completion

def modify_tester(code, q_key):
    # Read the original file
    with open('testing/tester.py', 'r') as file:
        content = file.read()
    
    m = re.search("^def (.*)\(", code, re.MULTILINE)
    f_name = m.group(1)
    
    # Replace the placeholder with the replacement string
    content = content.replace('<FUNCTION>', code).replace("<QUESTION>", f"'{q_key}'").replace("<FUNCTION_NAME>", f_name)
    return content

def run_code(q_key, code):
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

def convert_python(markdown_text):
    # Pattern to find Markdown code blocks
    pattern = r'```python(.*?)```'
    replacement = r'<code class="python medium-text"><pre>\1<pre></code>'
    html_text = re.sub(pattern, replacement, markdown_text, flags=re.DOTALL)
    return html_text

def convert_to_template(question_str, code, solution, error_num, error):
    
    first_line = "Given below is a programming question, the Instructors solution and the corresponding wrong answer from a student. Please give a helpful and polite explanation as to the next steps the student can take to improve their answer"
    if error_num==1:
        # Compilation Error
        first_line = "Given below is a programming question, the Instructors solution, the error message from compiling the code, and the corresponding wrong answer from a student"
        
    elif error_num==2 or error_num==3:
        first_line = "Given below is a programming question, the Instructors solution, the error message from executing the code against test cases, and the corresponding wrong answer from a student"
    error_m=''
    if error:
        error_m = f"Error:\n{error}\n\n"
    input_str = f"Question:\n{question_str}\n\nStudent Answer:\n{code}\n\n{error_m}Instructors Solution:\n{solution}\n\n Suggestion:"
    system_str = f"You are a polite and helpful assistant to help students learn programming. You will be deployed in an application where you must display suggestions to the student under the heading \"Suggestion:\". You will directly be addressing students and helping them make corrections in their code so that they can get it right. Do not speak about the student in the third person. {first_line}.You are encouraged to ask questions to the student and show simple related examples to lead the student in the right direction to figure out the answer on their own. DO NOT INCLUDE CODE OR THE ACTUAL ANSWER IN YOUR RESPONSE. Start the response with something that encourages the student and commends the student on his/her progress towards the task. Be concise in your response and do not overwhelm the student with information. Do not make any mention about the Instructors solution as the students will not have access to that."
    messages = [{"role": "system", "content": system_str},
    {"role": "user", "content": input_str}]

    print(json.dumps(messages, indent=4))
    
    return messages