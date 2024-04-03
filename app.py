from flask import Flask, render_template, url_for, redirect, request, jsonify
import os
import markdown
import threading
import json
import re
from openai import OpenAI

app = Flask(__name__)

@app.route('/')
def home():
    return redirect(url_for('code_helper'))

with open('questions.json', 'r') as file:
    questions = json.load(file)

api_key = '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'
client = OpenAI(api_key=api_key)
generated_content = None

def convert_to_template(question_str, code):
    input_str = f"Question:{question_str}\nStudent Answer:\n{code}\nGiven above is a programming question in python and the corresponding wrong answer from a student. Please give a helpful and polite explanation as to the next steps the student can take to improve their answer. Do not include code or the actual answer in your response" 
    return [{"role": "system", "content": "You are a polite and helpful assistant to help students learn programming"},
    {"role": "user", "content": input_str}]

def create_gpt_response(messages):
    global generated_content
    completion = client.chat.completions.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    generated_content = markdown.markdown(completion.choices[0].message.content)
    print(generated_content)

@app.route('/get-content')
def get_content():
    if generated_content is not None:
        return jsonify({'status': 'ready', 'content': generated_content})
    else:
        return jsonify({'status': 'generating'})

@app.route('/code_helper.html')
def code_helper():
    global generated_content
    generated_content = None  # Reset the content each time the page is loaded
    question_num = request.args.get("question")
    num=None
    code = None
    question_str=None
    suggestion=None
    if question_num:
        m = re.search("Q(.*)", question_num)
        num = int(m.group(1))
        selected_question = questions[num-1]
        question_str, code, suggestion = selected_question['question'], selected_question['answer'].strip(), selected_question['suggestion'].strip()
        messages = convert_to_template(question_str, code)
        # suggestion = create_gpt_response(messages)
        threading.Thread(target=create_gpt_response, args=(messages,)).start()
        # suggestion = markdown.markdown(suggestion)
        # print(f"Question:\n{question_str}\nCode:\n{code}\nThe above code seems to be wrong for solving the question. Can you give me some suggestions for improvement?")
        
    # Path to your markdown file
    # md_file_path = 'templates/model_op.md'
    # code_file_path = 'templates/code.txt'

    # # Check if the file exists
    # if os.path.exists(code_file_path):
    #     with open(code_file_path, 'r') as md_file:
    #         code = md_file.read()
    # else:
    #     code = ''
    #     print(f"Code file {code_file_path} not found")

    # Check if the file exists
    # if os.path.exists(md_file_path):
    #     with open(md_file_path, 'r') as md_file:
    #         md_content = md_file.read()
    #         md_content = markdown.markdown(md_content)
    # else:
    #     md_content = ''
    #     print(f"Markdown file {md_file_path} not found")
    return render_template('index.html', student_code=code, question_num=num, question_str=question_str)

if __name__ == '__main__':
    app.run(debug=True, port=5001)
