import json, os
from dotenv import load_dotenv
from utils.utils import * 

from flask import Flask, request, redirect, render_template, session, url_for, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
# import logging


app = Flask(__name__)
app.secret_key = '3d6f45a5fc12445dbac2f59c3b6c7cb1'
# Load environment variables from .env file
load_dotenv()

# # logging.basicConfig(level=logging.DEBUG)
# print('mangi url', os.getenv("MONGO_DB_URI"))
# client = MongoClient(os.getenv("MONGO_DB_URI"), server_api=ServerApi('1'))
# try:
#     client.admin.command('ping')
#     print("Pinged your deployment. You successfully connected to MongoDB!")
# except Exception as e:
#     print(e)

# db = client['trakss']

@app.route("/")
def home():
    # Reset the database by dropping all tables and recreating them
    return render_template("index.html",title='Transcribus')

@app.route('/set_api_key', methods=['POST'])
def set_api_key():
    data = request.get_json()
    session['api_key'] = data['apiKey']
    # logging.debug(f'API Key Saved')
    # print(data)
    return jsonify({"message": "API Key saved successfully"}), 200

videoUrl = ''
video_data = {
    'summary': '',
    'transct': dict(),
    'video_info': dict()
}

@app.route('/splashScreen', methods=['POST'])
def splash():
    global videoUrl
    videoUrl = request.form['videoUrl']
    return render_template('splashScreen.html',title='Transcribus', videoUrl=videoUrl)

@app.route('/process_video', methods=['POST'])
def process_video():
    global video_data
    try:
        print('qc check here:', videoUrl)
        # videoUrl = request.args.get('videoUrl')
        # logging.debug(f'Video URL is {videoUrl}')
        api_key = session.get('api_key', None)
        
        # Attempt to retrieve the long transcript and video info
        long_transct, video_info = get_llm_transcript(videoUrl)
        # logging.debug(f'Transcript and video info generated')
        if not long_transct or not video_info:
            raise ValueError("Failed to get transcript or video information")
        
        # Process transcript and summary
        transct = get_youtube_transcript(videoUrl)
        # logging.debug(f'Process transcript for summary')
        try:
            summary = openAI_summary(long_transct, api_key)
        except:
            summary = 'An error has occurred: This video is too long, please choose a shorter video. If you want to summarize a larger video, please contact the administrator through the "Contact Us" section.'
        # logging.debug(f'create summary using OPENAI')
        
        video_data = {
            'summary': summary,
            'transct': json.dumps(transct),
            'video_info': json.dumps(video_info)
        }

        # db.public.insert_one(video_data)
        return jsonify(success=True)
    except Exception as e:
        print(f"An error occurred in process_video: {e}")
        return jsonify(success=False, error=str(e))


@app.route('/summarize')
def output():
    # Retrieve data from the database
    print('till here')
    # video_data = db.public.find_one()
    print('summrize', video_data)
    if video_data:
        summaryv2 = video_data['summary']
        # highlightv2 = video_data['highlight']
        transct = json.loads(video_data['transct'])
        video_info = json.loads(video_data['video_info'])
    else:
        # Handle case where no data is found
        summaryv2 = ''
        # highlightv2 = ''
        transct = {}
        video_info = {}

    # db.public.delete_many(video_data)
    # print("check:",summaryv2[:40])
    return render_template('summarize.html', title='Transcribus', summaryv2=summaryv2, transct=transct, video_info=video_info)

if __name__ == "__main__":
    # app.run(host="0.0.0.0", port=8080, debug=True)
    app.run(host="0.0.0.0", port=8080)

