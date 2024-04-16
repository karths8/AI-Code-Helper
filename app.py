

from flask import Flask, render_template, url_for, redirect, request, jsonify, Response
import os
import markdown
import threading
import json
import re
from utils import extract_code, read_from_json, convert_to_template, generate_suggestion,code_runner_java, code_runner_python, write_to_json, make_directory, copy_contents, remove_ml_comments
from openai import OpenAI
import time
import argparse

parser = argparse.ArgumentParser(description="None")
parser.add_argument('--nollm',  action='store_true',help='Pass this argument for nollm mode')
parser.add_argument('--big',  action='store_true',help='Pass this argument for big screen mode')

args = parser.parse_args()

if args.big:
    design_dict = {'container_width':'1000px', 'container_height':'900px', 'image_margin_left':'400px'}
else:
    design_dict = {'container_width':'1000px', 'container_height':'900px', 'image_margin_left':'400px'}



app = Flask(__name__)
api_key = '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'
client_openai = OpenAI(api_key=api_key)
generated_content = None
questions = {}
solutions = read_from_json('testing/solutions.json')
test_cases_all_q = read_from_json('testing/test_cases.json')
model = "gpt-4-turbo-preview"
vendor = 'openai'
# messages = None
start_time = None
gpt_calls = {}
results = {}
questions_cache = {}
student_details = {}
question_button_clicks = {}
execution_times = {}
code_path = ''

def get_student_results():
    global results
    for q_key in questions_cache:
        err = questions_cache[q_key]['error']
        score = 1 if err=="All tests Passed!" else 0
        results[q_key] = {"error":err, "score":score}


@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/start', methods=['POST'])
def start():
    global student_details, code_path
    student_name = request.form.get('student_name')
    unique_id = request.form.get('unique_id')
    programming_language = request.form.get('programming_language')
    student_details = {'student_name':student_name, 'unique_id':unique_id, 'programming_language':programming_language}
    code_path = os.path.join('code', programming_language, unique_id)
    lang_path = os.path.join('code', programming_language, 'base')
    copy_contents(lang_path, code_path)
    return redirect(url_for('welcome_page'))

@app.route('/welcome_page')
def welcome_page():
    global start_time
    start_time = time.time()
    return render_template('welcome_page.html')

@app.route('/submit', methods=['POST'])
def submit():
    global results, student_details, question_button_clicks, questions_cache, questions, solutions, test_cases_all_q, start_time, gpt_calls
    elapsed_time = time.time() - start_time
    dir_path = "student_results"
    make_directory(dir_path)
    filename = os.path.join(dir_path, student_details['unique_id']+'.json')
    total_score = 0
    for q_key in results:
        total_score+=results[q_key]['score']
    combined_results = {"results":results, "total_score":total_score, "student_details":student_details,"questions_cache":questions_cache, "model":model, "time_taken":elapsed_time, "gpt_calls":gpt_calls, 'No-LLM': args.nollm}
    write_to_json(filename, combined_results)
    return render_template('submitted.html')
        

@app.route('/')
def home():
    return redirect(url_for('login'))

def create_gpt_response(messages,client,q, a, error,example, q_key):
    global generated_content, questions_cache, model, gpt_calls
    
    if args.nollm:
        msg, exec_time = None, 0
        suggestion = ''
    else:
        msg, exec_time = generate_suggestion(messages, client, model)
        suggestion = markdown.markdown(msg)
        if q_key not in gpt_calls:
            gpt_calls[q_key] = 0
        gpt_calls[q_key]+=1
        print("Inside GPT response")
        if q_key not in execution_times:
            execution_times[q_key] = []
        execution_times[q_key].append(exec_time)
    
    questions_cache[q_key] = {"question":q, "code":a, "suggestion": suggestion, 'error':error, 'example':example}
    generated_content = suggestion


@app.route('/get-content')
def get_content():
    global generated_content
    if generated_content is not None:
        return jsonify({'status': 'ready', 'content': generated_content})
    else:
        return jsonify({'status': 'generating'})

@app.route('/code_helper')
def code_helper():
    global generated_content, questions, questions_cache, messages, results, question_button_clicks, student_details, code_path, design_dict
    lang = student_details['programming_language']
    if lang=='Python':
        path = {'Python': os.path.join(code_path, 'test_notebook.ipynb'), "Java": None}
    else:
        path = {'Python': 'code/Python/base/test_notebook.ipynb', "Java": code_path}
    generated_content = None  # Reset the content each time the page is loaded
    question_num = request.args.get("question")
    
    num=None
    code = None
    question_str=None
    suggestion=None
    questions = extract_code(path, lang)
    num_of_questions = len(questions)
    for i in range (1, num_of_questions+1):
        q_num_str = f"Q{i}"
        if q_num_str not in question_button_clicks:
            question_button_clicks[q_num_str] = 0
        if q_num_str not in results:
            results[q_num_str] = {"error":"You have not checked the output for this question yet. Please click the appropriately numbered question button below to see correctness output.", "score":0}
    
    error=None
    total_score=None
    if question_num=='finish':
        get_student_results()
        total_score = sum([results[i]['score'] for i in results])
        return render_template('index.html', results=results, student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions, error=error, total_score=total_score, nollm=args.nollm, design_dict=design_dict)
    
    
    if question_num:
        m = re.search("Q(\d*)", question_num)
        num = int(m.group(1))
        q_key = f'Q{num}'
        question_button_clicks[q_key]+=1
        selected_question = questions[q_key]
        question_str, code, example = selected_question['question'], selected_question['code'].strip(), selected_question['example']
        
        if lang=='Java':
            java_pattern = r"public static void main\(String args\[\]\) \{[\s\S]*?\}"
            code = re.sub(java_pattern, '', code)
            code = remove_ml_comments(code).strip()
        if q_key in questions_cache:
            cached_question = questions_cache[q_key]
            cached_question_str, cached_code, cached_suggestion, cached_error, cached_example = cached_question['question'], cached_question['code'].strip(), cached_question['suggestion'], cached_question['error'],cached_question['example']
        if q_key in questions_cache and cached_code==code:
            # dont invoke gpt response, we dont want to calculate new response everytime help is needed for a particular question
            error = cached_error
            generated_content = cached_suggestion
        else:
            # invoke gpt response
            test_cases = test_cases_all_q[q_key]
            if lang=='Python':
                error_num, error = code_runner_python(code, q_key)
            else:
                error_num, error = code_runner_java(q_key, code_path)
            
            solution = solutions[lang][q_key]
            if error=="All tests Passed!":
                model_resp = "Great Job! You get full points for this problem"
                questions_cache[q_key] = {"question":question_str, "code":code, "suggestion": model_resp, 'error':error, 'example': example}
                generated_content = model_resp
                # time.sleep(1)
            else:
                client = client_openai if vendor=='openai' else client_anthropic
                messages = convert_to_template(question_str, code, solution, error_num, error, example)
                threading.Thread(target=create_gpt_response, args=(messages,client,question_str, code,error,example, q_key)).start()
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions, error=error, total_score=total_score, results=None, nollm=args.nollm, design_dict=design_dict)

if __name__ == '__main__':
    app.run(debug=True, port=5001)