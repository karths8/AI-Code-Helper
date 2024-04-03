import nbformat
import re
import json

def remove_comments(code):
    # Pattern to match single-line comments
    pattern = re.compile(r'#.*?$|\'\'\'.*?\'\'\'|""".*?"""', re.DOTALL | re.MULTILINE)
    return re.sub(pattern, lambda m: "" if m.group(0).startswith('#') else m.group(0), code)

def extract_cells(notebook_path):
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
    qs = []
    cells = nb.cells
    for c in cells:
        if c['cell_type']=='code':
            src = c['source']
            num = re.search("#q(.*)", src)
            m = re.search("#Q:(.*)", src)
            code = remove_comments(src).strip()
            question = m.group(1)
            qs.append({'num':num,"question":question, "answer":code})
    return qs

def write_to_json(filename, data):
    with open(filename, 'w') as file:
        json.dump(data, file, indent=4)

def read_from_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data

def convert_to_template(question_str, code):
    input_str = f"Question:{question_str}\nStudent Answer:\n{code}\nGiven above is a programming question in python and the corresponding wrong answer from a student. Please give a helpful and polite explanation as to the next steps the student can take to improve their answer. Do not include code or the actual answer in your response" 
    return [{"role": "system", "content": "You are a polite and helpful assistant to help students learn programming"},
    {"role": "user", "content": input_str}]