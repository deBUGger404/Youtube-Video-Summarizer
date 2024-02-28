import json, os
from prompt import *
from dotenv import load_dotenv
from collections import defaultdict

from langchain_community.document_loaders import YoutubeLoader
from langchain_openai import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound


from flask import Flask, request, redirect, render_template, session, url_for, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi



app = Flask(__name__)
app.secret_key = '3d6f45a5fc12445dbac2f59c3b6c7cb1'
# Load environment variables from .env file
load_dotenv()

# print('mangi url', os.getenv("MONGO_DB_URI"))
client = MongoClient(os.getenv("MONGO_DB_URI"), server_api=ServerApi('1'))
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
db = client['trakss']

@app.route("/")
def home():
    # Reset the database by dropping all tables and recreating them
    return render_template("index.html",title='Transcribus')

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    data = request.get_json()
    session['api_key'] = data['apiKey']
    # print(data)
    return jsonify({"message": "API Key saved successfully"}), 200

@app.route('/splashScreen', methods=['POST'])
def splash():
    videoUrl = request.form['videoUrl']
    return render_template('splashScreen.html',title='Transcribus', videoUrl=videoUrl)

@app.route('/process_video', methods=['POST'])
def process_video():
    videoUrl = request.args.get('videoUrl')
    api_key = session.get('api_key', None)
    long_trnasct, video_info = get_llm_transcript(videoUrl)
    transct = get_youtube_transcript(videoUrl)
    summaryv2 = openAI_summary(long_trnasct, api_key, 'summary')
    highlightv2 = openAI_summary(long_trnasct, api_key, 'highlight')
    print('process-data:', highlightv2)
    # Store data in the database
    video_data = {
        'summary': summaryv2['output_text'] if 'output_text' in summaryv2 else None,
        'highlight': highlightv2['output_text'] if 'output_text' in highlightv2 else None,
        'transct': json.dumps(transct),
        'video_info': json.dumps(video_info)
    }
    db.public.insert_one(video_data)
    return jsonify(success=True)

@app.route('/summarize')
def output():
    # Retrieve data from the database
    video_data = db.public.find_one()
    # print('summrize', video_data)
    if video_data:
        summaryv2 = video_data['summary']
        highlightv2 = video_data['highlight']
        transct = json.loads(video_data['transct'])
        video_info = json.loads(video_data['video_info'])
    else:
        # Handle case where no data is found
        summaryv2 = ''
        highlightv2 = ''
        transct = {}
        video_info = {}

    db.public.delete_many(video_data)
    return render_template('summarize.html', title='Transcribus', summaryv2=summaryv2, highlightv2=highlightv2, transct=transct, video_info=video_info)


def get_llm_transcript(youtube_url):
        print('uyoutube url', youtube_url)
        loader = YoutubeLoader.from_youtube_url(str(youtube_url),  add_video_info=True)
        result = loader.load()
        try:
            vd= loader._get_video_info()
            vd['publish_date'] = vd['publish_date'].strftime('%M:%S')
        except:
            vd = 'No Info about Video available'
        return result, vd

def get_youtube_transcript(youtube_url):
    video_id = youtube_url.split("youtube.com/watch?v=")[-1]
    # print(video_id)
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    try:
        transcript = transcript_list.find_transcript(['en-GB'])
    except NoTranscriptFound:
        transcript = transcript_list.find_transcript(["en"])
        error = 'not available in selected language'
    # print('here1')
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
    # print('open api', api_key)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    llm = OpenAI(temperature=0, openai_api_key=api_key, max_tokens=256, streaming=False)
    texts = text_splitter.split_documents(transct_text)
    # print('here4')
    if type=='summary': prompt_template = prompt_template1
    elif type=='highlight': prompt_template = prompt_template2
    else: print(f'Specify the correct Type')
    try:
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
        # print(PROMPT)
        chain = load_summarize_chain(llm, chain_type="map_reduce", verbose=False, map_prompt=PROMPT, combine_prompt=PROMPT)
        # print('here45')
        # print(chain)
        response = chain.invoke(texts)
        # print('here5')
        return response
    except:
        return 'Some error in API'


if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=8080, debug=True)
    app.run(host="0.0.0.0", port=8080, debug=False)

