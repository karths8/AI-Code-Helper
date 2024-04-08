from utils import extract_cells, write_to_json, convert_to_template, read_from_json, generate_suggestion
from openai import OpenAI
import markdown
import os

def fill_cache():
    api_key = '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'
    client = OpenAI(api_key=api_key)
    print("Filling Questions Cache")
    if os.path.exists('cache/questions_cache.json'):
        questions_file = read_from_json('cache/questions_cache.json')
    else:
        questions_file = [{'question':'','answer':'','suggestion':''} for _ in range(5)]
    questions_cache = []
    for idx,i in enumerate(extract_cells('code/test_notebook.ipynb')):
        print(f"Getting Response for {idx}")
        q, a = i['question'], i['answer']
        if questions_file[idx]['answer']!=a:
            messages = convert_to_template(q, a)
            err = check_python_code(a)
            suggestion = markdown.markdown(generate_suggestion(messages,err, client))
        else:
            suggestion = questions_file[idx]['suggestion']
        questions_cache.append({'question':q, 'answer':a, 'suggestion': suggestion})
    return questions_cache

if __name__ == '__main__':
    questions_cache = fill_cache()
    write_to_json('cache/questions_cache.json', questions_cache)
    