from flask import Flask, request, redirect, render_template, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy

import json
from langchain_community.document_loaders import YoutubeLoader
from langchain_community.llms import OpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import PromptTemplate
from langchain.cache import InMemoryCache
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from collections import defaultdict

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class VideoData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    summary = db.Column(db.String(500))
    highlight = db.Column(db.String(500))
    transct = db.Column(db.String(5000))  # Adjust size as needed
    video_info = db.Column(db.String(500))

with app.app_context():
    db.create_all()

# promat template
prompt_template1 = """
Given the transcript of a YouTube video, your task is to distill the information into a succinct, engaging summary. This summary should encapsulate the core essence of the video, highlighting major points, key insights, and the overarching conclusions. The goal is to furnish a concise snapshot that conveys the video's value and primary messages, enabling viewers to grasp the content's significance without having to watch the entire video.

Ensure the summary is comprehensive, capturing the critical themes and insights. This is crucial for users who are looking for a quick understanding or are deciding on whether to invest time in the full video. Your summary should be at least 300 characters long to ensure it's detailed enough to stand on its own.

Please begin with a brief introduction to the topic discussed in the video, followed by the main body where key points and insights are outlined. Conclude with a closing statement that reflects on the video's implications or leaves the reader with a thought-provoking takeaway.

Transcript:

{text}

CONCISE SUMMARY:
"""
prompt_template2 = """
Transform the provided YouTube video transcript into an engaging series of bullet-pointed highlights. Each bullet point should represent a key insight, moment, or takeaway from the video, structured to offer users a quick, visually appealing overview of the content's main themes and interesting points.

Aim for at least 6-7 bullet points to ensure comprehensive coverage of the video's content. Incorporate contextual information where necessary to make each point clear and impactful. The use of emojis is encouraged to add a layer of visual interest and help emphasize the emotional tone or subject matter of each highlight.

Remember, the objective is to make the summary not only informative but also enjoyable and easy for users to skim through. Each point should be distinct, conveying a standalone insight or takeaway that collectively provides a rounded view of the video’s content.

output format:
- pointer1\n- pointer2

Transcript:

{text}

HIGHLIGHTS:
"""



@app.route("/")
def home():
    # Reset the database by dropping all tables and recreating them
    db.drop_all()
    db.create_all()
    return render_template("index.html",title='Transcribus')

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    data = request.get_json()
    session['api_key'] = data['apiKey']
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
    print(highlightv2)
    # Store data in the database
    video_data = VideoData(summary=summaryv2, highlight=highlightv2, transct=json.dumps(transct), video_info=json.dumps(video_info))
    db.session.add(video_data)
    db.session.commit()
    return jsonify(success=True)

@app.route('/summarize')
def output():
# Retrieve data from the database
    video_data = VideoData.query.first()  # Assuming there's only one row in the table
    if video_data:
        summaryv2 = video_data.summary
        highlightv2 = video_data.highlight
        transct = json.loads(video_data.transct)
        video_info = json.loads(video_data.video_info)
    else:
        # Handle case where no data is found
        summaryv2 = ''
        highlightv2 = ''
        transct = {}
        video_info = {}

    return render_template('summarize.html', title='Transcribus', summaryv2=summaryv2, highlightv2=highlightv2, transct=transct, video_info=video_info)


def get_llm_transcript(youtube_url):
        # print(youtube_url)
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
        response = chain.run(texts)
        # print('here5')
        return response
    except:
        return 'Some error in API'


if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=8080, debug=True)
    app.run(host="0.0.0.0", port=8080, debug=False)

