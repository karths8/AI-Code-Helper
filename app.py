from flask import Flask, render_template, url_for, redirect, request, jsonify, Response
import os
import markdown
import threading
import json
import re
from utils import extract_cells, read_from_json, convert_to_template, generate_suggestion, code_runner
from openai import OpenAI
import time
import anthropic

app = Flask(__name__)
api_key = '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'
client_openai = OpenAI(api_key=api_key)
client_anthropic = anthropic.Anthropic(api_key="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")
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

# questions_cache = read_from_json('cache/questions_cache.json')
questions_cache = {}
student_details = {}

# @app.route('/login')
# def home():
#     return redirect(url_for('code_helper'))

@app.route('/login', methods=['GET'])
def login():
    return render_template('login.html')

@app.route('/start', methods=['POST'])
def start():
    global student_details
    student_name = request.form.get('student_name')
    student_id = request.form.get('student_id')
    programming_language = request.form.get('programming_language')
    student_details = {'student_name':student_name, 'student_id':student_id, 'programming_language':programming_language}
    return redirect(url_for('welcome_page'))

@app.route('/welcome_page')
def welcome_page():
    return render_template('welcome_page.html')


# @app.route('/progress')
# def progress():
#     # Example: simulate a task taking some time
#     for i in range(1, 101):
#         time.sleep(0.1)  # simulate delay
#         # You would replace this with actual task progress
#     return jsonify({"status": "Done"})

@app.route('/')
def home():
    return redirect(url_for('login'))

def create_gpt_response(messages,client,q, a, error, q_key):
    global generated_content, questions_cache, model
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
    global generated_content, questions, questions_cache, messages
    generated_content = None  # Reset the content each time the page is loaded
    question_num = request.args.get("question")
    num=None
    code = None
    question_str=None
    suggestion=None
    num_of_questions=None
    error=None
    questions = extract_cells('code/test_notebook.ipynb')
    num_of_questions = len(questions)
    if question_num:
        m = re.search("Q(\d*)", question_num)
        num = int(m.group(1))
        q_key = f'Q{num}'
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
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions, error=error)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
