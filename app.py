from flask import Flask, render_template, url_for, redirect, request, jsonify
import os
import markdown
import threading
import json
import re
from utils import extract_cells, read_from_json, convert_to_template
from openai import OpenAI

app = Flask(__name__)
api_key = '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'
client = OpenAI(api_key=api_key)
generated_content = None
questions = []

questions_cache = read_from_json('cache/questions_cache.json')

@app.route('/')
def home():
    return redirect(url_for('code_helper'))



def create_gpt_response(messages, q, a, num):
    global generated_content, questions_cache
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    print("GPT Called!")
    suggestion = markdown.markdown(completion.choices[0].message.content)
    questions_cache[num-1] = {"question":q, "answer":a, "suggestion": suggestion}
    generated_content = suggestion


@app.route('/get-content')
def get_content():
    if generated_content is not None:
        return jsonify({'status': 'ready', 'content': generated_content})
    else:
        return jsonify({'status': 'generating'})

@app.route('/code_helper.html')
def code_helper():
    global generated_content, questions
    generated_content = None  # Reset the content each time the page is loaded
    question_num = request.args.get("question")
    num=None
    code = None
    question_str=None
    suggestion=None
    if question_num:
        m = re.search("Q(.*)", question_num)
        num = int(m.group(1))
        questions = extract_cells('code/test_notebook.ipynb')
        selected_question = questions[num-1]
        question_str, code= selected_question['question'], selected_question['answer'].strip()
        cached_question = questions_cache[num-1]
        cached_question_str, cached_code, cached_suggestion = cached_question['question'], cached_question['answer'].strip(), cached_question['suggestion']
        if cached_code==code:
            # dont invoke gpt response
            generated_content = cached_suggestion
        else:
            # invoke gpt response
            messages = convert_to_template(question_str, code)
            threading.Thread(target=create_gpt_response, args=(messages,question_str, code, num)).start()
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
