from flask import Flask, render_template, url_for, redirect, request, jsonify
import os
import markdown
import threading
import json
import re
from utils import extract_cells, read_from_json, convert_to_template, generate_suggestion, code_runner
from openai import OpenAI

app = Flask(__name__)
api_key = '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'
client = OpenAI(api_key=api_key)
generated_content = None
questions = {}
solutions = read_from_json('solutions.json')
test_cases = read_from_json('test_cases.json')

# questions_cache = read_from_json('cache/questions_cache.json')
questions_cache = {}

@app.route('/')
def home():
    return redirect(url_for('code_helper'))

def create_gpt_response(messages,client,q, a, q_key):
    global generated_content, questions_cache
    suggestion = markdown.markdown(generate_suggestion(messages, client))
    questions_cache[q_key] = {"question":q, "code":a, "suggestion": suggestion}
    generated_content = suggestion


@app.route('/get-content')
def get_content():
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
            cached_question_str, cached_code, cached_suggestion = cached_question['question'], cached_question['code'].strip(), cached_question['suggestion']
        if q_key in questions_cache and cached_code==code:
            # dont invoke gpt response, we dont want to calculate new response everytime help is needed for a particular question
            generated_content = cached_suggestion
        else:
            # invoke gpt response
            error_num, error = code_runner(code)
            solution = solutions[q_key]
            messages = convert_to_template(question_str, code,solution, error_num, error)
            threading.Thread(target=create_gpt_response, args=(messages,client,question_str, code, q_key)).start()
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str, num_of_questions=num_of_questions)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
