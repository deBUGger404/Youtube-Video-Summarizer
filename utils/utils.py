from collections import defaultdict
from langchain_community.document_loaders import YoutubeLoader
from openai import OpenAI
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.chains.summarize import load_summarize_chain
# from langchain.prompts import PromptTemplate
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

# promat template
prompt_template1 = """## Video Content Distillation

As a specialist in distilling video content, your task is to extract and present the essence of a YouTube video transcript in two formats:

1. **Concise Summary**: 
    Craft a succinct, engaging summary that encapsulates the video's major points, key insights, and overarching conclusions. Your summary should provide a comprehensive snapshot, allowing readers to grasp the content's significance quickly.

2. **Bullet-Pointed Highlights**: 
    Create a series of 6-7 bullet points, each highlighting a key insight, moment, or takeaway from the video. Incorporate emojis for added visual interest and ensure each point is clear and impactful.

**Output Format:** Use Markdown to format your work. Begin with the concise summary, followed by the bullet-pointed highlights. This structured approach will ensure clarity and ease of reading."""


def get_llm_transcript(youtube_url):
    try:
        print('youtube url', youtube_url)
        loader = YoutubeLoader.from_youtube_url(str(youtube_url), add_video_info=True)
        result = loader.load()
        # Check if result has at least one item to avoid IndexError
        if result and len(result) > 0:
            text, details = result[0].page_content, result[0].metadata
            return text, details
        else:
            return "No results found", {}
    except Exception as e:
        # Handle general exceptions
        print(f"An error occurred: {e}")
        return "Error loading transcript", {}

def get_youtube_transcript(youtube_url):
    video_id = youtube_url.split("youtube.com/watch?v=")[-1]
    print(video_id)
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

    # Attempt to directly select the preferred or fallback language
    try:
        transcript = transcript_list.find_transcript(['en-GB', 'en'])
    except Exception as e:  # Catch more specific exceptions if possible
        print(f"Error finding transcript: {e}")
        return {}
    
    print('here1')
    captions_dict = defaultdict(str)  # Use string directly to concatenate

    for caption in transcript.fetch():
        start_time = round(caption['start'] / 60) * 60
        caption_text = caption['text'].strip()
        # Append directly to the string for each key, reducing list overhead
        captions_dict[start_time] += caption_text + "\n"
    
    captions_final = {}
    for time, captions in captions_dict.items():
        minutes, seconds = divmod(time, 60)
        time_formatted = f"{minutes:02d}:{seconds:02d}"
        # Trim the trailing newline when finalizing the string
        captions_final[time_formatted] = captions[:-1]  # Remove the last newline
    
    return captions_final

def openAI_summary(input_text, api_key):
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
    model="gpt-3.5-turbo-0125",
    messages=[
        {
        "role": "system",
        "content": prompt_template1
        },
        {
        "role": "user",
        "content": f"**Transcript:** '''{input_text}'''"
        },
    ],
    temperature=1,
    max_tokens=256,
    top_p=1,
    frequency_penalty=0,
    presence_penalty=0
    )
    return response.choices[0].message.content

# def openAI_summary(transct_text, api_key, type = 'summary'):
#     # print('open api', api_key)
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=9000, chunk_overlap=100)
#     llm = ChatOpenAI(temperature=0, model ='gpt-3.5-turbo-0125', openai_api_key=api_key, max_tokens=300, streaming=False)
#     texts = text_splitter.split_documents(transct_text)
#     # print('here4')
#     prompt_template = prompt_template1
#     try:
#         PROMPT = PromptTemplate(template=prompt_template, input_variables=["text"])
#         # print(PROMPT)
#         chain = load_summarize_chain(llm, chain_type="map_reduce", verbose=False, map_prompt=PROMPT, combine_prompt=PROMPT)
#         print('here45')
#         # print(chain)
#         response = chain.invoke(texts)
#         print('here5')
#         return response
#     except:
#         return 'Some error in API'

