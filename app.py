from flask import Flask, request, redirect
from flask import render_template
import json
import configparser
import langchain
from langchain.document_loaders import YoutubeLoader
from langchain.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.cache import InMemoryCache
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from collections import defaultdict

app = Flask(__name__)

langchain.llm_cache = InMemoryCache()

# promat template
prompt_template1 = """Write a concise summary of the following:


{text}


CONCISE SUMMARY:"""

prompt_template2 = """highlights of the transcript in concise manner with emoji minimum 7 points:


{text}


CONCISE SUMMARY:"""

@app.route("/")
def home():
    return render_template("index.html",title='Transcribus')

# @app.route('/splashScreen', methods=['POST'])
# def splash():
#     value = request.form['value']
#     return render_template('splashScreen.html',title='Transcribus', value=value)


@app.route('/summarize', methods=['POST'])
def target_page():
    # value = request.args.get('videoid')
    value = request.form['value']
    print(value)
    long_trnasct, video_info = get_llm_transcript(value)
    transct = get_youtube_transcript(value)
    summary = openAI_summary(long_trnasct,get_api_key(), 'summary')
    highlight = openAI_summary(long_trnasct,get_api_key(), 'highlight')
    print(summary)
#     response =  json.dumps({'summary': summary, 'highlight': highlight, 'transct':json.dumps(transct), 'video_info':json.dumps(video_info)})
#     return response

# @app.route('/summarize')
# def output():
#     summary = request.args.get('summary')
#     highlight = request.args.get('highlight')
#     transct = json.loads(request.args.get('transct'))
#     video_info = json.loads(request.args.get('video_info'))
    return render_template('summarize.html', title='Transcribus', summary=summary, highlight=highlight, transct=transct,video_info=video_info)

def get_api_key():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['openaikey']['api']

def get_llm_transcript(youtube_url):
        loader = YoutubeLoader.from_youtube_channel(str(youtube_url))
        result = loader.load()
        try:
            vd= loader._get_video_info()
            vd['publish_date'] = vd['publish_date'].strftime('%M:%S')
        except:
            vd = 'No Info about Video available'
        return result, vd

def get_youtube_transcript(youtube_url):
    video_id = youtube_url.split("youtube.com/watch?v=")[-1]
    print(video_id)
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    try:
        transcript = transcript_list.find_transcript(['en-GB'])
    except NoTranscriptFound:
        transcript = transcript_list.find_transcript(["en"])
        error = 'not available in selected language'
    captions_dict = defaultdict(list)
    for caption in transcript.fetch():
        start_time = round(caption['start'] / 60) * 60
        caption_text = caption['text'].strip()
        captions_dict[start_time].append(caption_text)
    captions_final = {}
    for time, captions in captions_dict.items():
        minutes, seconds = divmod(time, 60)
        time_formatted = f"{minutes:02d}:{seconds:02d}"
        captions_formatted = "\n".join([caption for caption in captions])
        captions_final[time_formatted] = captions_formatted.strip()
    return captions_final

def openAI_summary(transct_text, api_key, type = 'summary'):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    llm = OpenAI(temperature=0, openai_api_key=api_key, max_tokens=512, streaming=False)
    texts = text_splitter.split_documents(transct_text)
    if type=='summary': prompt_template = prompt_template1
    elif type=='highlight': prompt_template = prompt_template2
    else: print(f'Specify the correct Type')
    try:
        print(prompt_template)
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
        chain = load_summarize_chain(llm, chain_type="map_reduce", verbose=False, map_prompt=PROMPT, combine_prompt=PROMPT)
        response = chain.run(texts)
        return response
    except:
        return 'Some error in API'


if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=8080, debug=True)
    app.run(host="0.0.0.0", port=8080, debug=False)

