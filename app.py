from flask import Flask, render_template, url_for, redirect, request, jsonify
import os
import markdown
import threading
import json
import re
from utils import extract_cells, read_from_json, convert_to_template, generate_suggestion, code_runner
from openai import OpenAI
import time

app = Flask(__name__)
api_key = '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'
client = OpenAI(api_key=api_key)
generated_content = None
questions = {}
solutions = read_from_json('solutions.json')
test_cases_all_q = read_from_json('test_cases.json')

# questions_cache = read_from_json('cache/questions_cache.json')
questions_cache = {}

@app.route('/')
def home():
    return redirect(url_for('code_helper'))

def create_gpt_response(messages,client,q, a, error, q_key):
    global generated_content, questions_cache
    print("Inside GPT response")
    suggestion = markdown.markdown(generate_suggestion(messages, client))
    questions_cache[q_key] = {"question":q, "code":a, "suggestion": suggestion, 'error':error}
    generated_content = suggestion


@app.route('/get-content')
def get_content():
    global generated_content
    
    if generated_content is not None:
        return jsonify({'status': 'ready', 'content': generated_content})
    else:
        return jsonify({'status': 'generating'})

@app.route('/code_helper.html')
def code_helper():
    global generated_content, questions, questions_cache
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
            generated_content = cached_suggestion
        else:
            # invoke gpt response
            test_cases = test_cases_all_q[q_key]
            error_num, error = code_runner(code=code, q_key=q_key)
            print(error_num)
            print(error)
            # error_num, error = 1, "Name Error"
            
            solution = solutions[q_key]
            if error=="All tests Passed!":
                model_resp = "Great Job! You get full points for this problem"
                questions_cache[q_key] = {"question":question_str, "code":code, "suggestion": model_resp, 'error':None}
                generated_content = model_resp
                time.sleep(1)
            print("Not all tests passed!")
            messages = convert_to_template(question_str, code,solution, error_num, error)
            threading.Thread(target=create_gpt_response, args=(messages,client,question_str, code,error, q_key)).start()
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions, error=error)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
