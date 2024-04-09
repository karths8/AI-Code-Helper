from flask import Flask, render_template, url_for, redirect, request, jsonify, Response
import os
import markdown
import threading
import json
import re
from utils import extract_cells, read_from_json, convert_to_template, generate_suggestion, code_runner, write_to_json, make_directory
from openai import OpenAI
import time

app = Flask(__name__)
api_key = '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'
client_openai = OpenAI(api_key=api_key)
# client_anthropic = anthropic.Anthropic(api_key="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")
generated_content = None
questions = {}
solutions = read_from_json('solutions.json')
test_cases_all_q = read_from_json('test_cases.json')
# model = "claude-3-opus-20240229"
# model = "claude-3-sonnet-20240229"
# model = "claude-3-haiku-20240307"
model = "gpt-4-turbo-preview"
# model = "gpt-3.5-turbo"
vendor = 'anthropic' if 'claude' in model else 'openai'
# messages = None
start_time = None
gpt_calls = 0
results = {}

# questions_cache = read_from_json('cache/questions_cache.json')
questions_cache = {}
student_details = {}
question_button_clicks = {}

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
    global student_details
    student_name = request.form.get('student_name')
    unique_id = request.form.get('unique_id')
    programming_language = request.form.get('programming_language')
    student_details = {'student_name':student_name, 'unique_id':unique_id, 'programming_language':programming_language}
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
    combined_results = {"results":results, "total_score":total_score, "student_details":student_details,"questions_cache":questions_cache, "model":model, "time_taken":elapsed_time, "gpt_calls":gpt_calls}
    write_to_json(filename, combined_results)
    return render_template('submitted.html')
        

@app.route('/')
def home():
    return redirect(url_for('login'))

def create_gpt_response(messages,client,q, a, error, q_key):
    global generated_content, questions_cache, model, gpt_calls
    gpt_calls+=1
    print("Inside GPT response")
    suggestion = markdown.markdown(generate_suggestion(messages, client, model))
    questions_cache[q_key] = {"question":q, "code":a, "suggestion": suggestion, 'error':error}
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
    global generated_content, questions, questions_cache, messages, results, question_button_clicks
    generated_content = None  # Reset the content each time the page is loaded
    question_num = request.args.get("question")
    
    num=None
    code = None
    question_str=None
    suggestion=None
    questions = extract_cells('code/test_notebook.ipynb')
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
        return render_template('index.html', results=results, student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions, error=error, total_score=total_score)
    
    
    if question_num:
        m = re.search("Q(\d*)", question_num)
        num = int(m.group(1))
        q_key = f'Q{num}'
        question_button_clicks[q_key]+=1
        selected_question = questions[q_key]
        question_str, code = selected_question['question'], selected_question['code'].strip()
        if q_key in questions_cache:
            cached_question = questions_cache[q_key]
            cached_question_str, cached_code, cached_suggestion, cached_error = cached_question['question'], cached_question['code'].strip(), cached_question['suggestion'], cached_question['error']
        if q_key in questions_cache and cached_code==code:
            # dont invoke gpt response, we dont want to calculate new response everytime help is needed for a particular question
            error = cached_error
            generated_content = cached_suggestion
        else:
            # invoke gpt response
            test_cases = test_cases_all_q[q_key]
            error_num, error = code_runner(code=code, q_key=q_key)
            print(error_num)
            print(error)
            
            solution = solutions[q_key]
            if error=="All tests Passed!":
                model_resp = "Great Job! You get full points for this problem"
                questions_cache[q_key] = {"question":question_str, "code":code, "suggestion": model_resp, 'error':error}
                generated_content = model_resp
                # time.sleep(1)
            else:
                client = client_openai if vendor=='openai' else client_anthropic
                messages = convert_to_template(question_str, code,solution, error_num, error)
                threading.Thread(target=create_gpt_response, args=(messages,client,question_str, code,error, q_key)).start()
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions, error=error, total_score=total_score, results=None)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
