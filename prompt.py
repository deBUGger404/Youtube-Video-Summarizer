
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