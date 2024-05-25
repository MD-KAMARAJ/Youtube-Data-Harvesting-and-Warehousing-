import pymysql
import pandas as pd
import googleapiclient.discovery
from googleapiclient.discovery import build
from datetime import datetime
import isodate
import streamlit as st
from streamlit_option_menu import option_menu
import time
import base64
import plotly.express as px


def set_bg_hack(main_bg):
    '''
    A function to unpack an image from root folder and set as bg.
    Returns
    -------
    The background.
    '''
    # set bg name
    main_bg_ext = "jpg"

    st.markdown(
         f"""
         <style>
         .stApp {{
             background: url(data:image/{main_bg_ext};base64,{main_bg});
             background-size: cover
         }}
         </style>
         """,
         unsafe_allow_html=True
     )

# Load your image
with open(r"C:\Users\HP USER\Desktop\youtube_logo_4k_1.jpg", "rb") as image_file:
    image_bytes = image_file.read()
    encoded_image = base64.b64encode(image_bytes).decode()

# Set the background image
set_bg_hack(encoded_image)

st.title(":red[YouTube] Data Harvesting and Warehousing")
   
with st.sidebar:
    st.header("Inputs here")


tab1, tab2, tab3 = st.tabs(["API Key", "Channel_id","Queries"])


with tab1:
    api_service_name = "youtube"
    api_version = "v3"
    api_key = st.text_input("API Key", placeholder="Enter your API key")
    if api_key:
        st.success("api_key is verified!, Go to next tab")
        
youtube = googleapiclient.discovery.build(api_service_name, api_version, developerKey=api_key)
 
def channel_data(channel_id):
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()

    data = {
        'channel_id': channel_id,
        'channel_name': response['items'][0]['snippet']['title'],
        'channel_descr': response['items'][0]['snippet']['description'],
        'channel_Subs_count': response['items'][0]['statistics']['subscriberCount'],
        'channel_video_count': response['items'][0]['statistics']['videoCount'],
        'channel_views_count': response['items'][0]['statistics']['viewCount'],
        'channel_playlist_id': response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    }

    return data

def format_datetime_for_mysql(dt_str):
    dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_iso8601_duration(duration):
    duration_td = isodate.parse_duration(duration)
    return int(duration_td.total_seconds())

def get_playlist_id(channel_id):
    playlist_id = channel_data(channel_id)['channel_playlist_id']
    return playlist_id

def video_data(channel_id):
    playlist_id_value = get_playlist_id(channel_id)
    video_data_list = []

    next_page_token = None
    while True:
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id_value,
            maxResults=50,
            pageToken=next_page_token
        )
        response = request.execute()

        for item in response['items']:
            video_id = item['snippet']['resourceId']['videoId']

            video_request = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id,
                maxResults=1
            )
            video_response = video_request.execute()

            if 'items' in video_response and video_response['items']:
                video_item = video_response['items'][0]
                data = {
                    'video_id': video_id,
                    'playlist_id': playlist_id_value,
                    'video_published_date': video_item['snippet']['publishedAt'],
                    'video_thumbnail': video_item['snippet']['thumbnails']['default']['url'],
                    'video_caption_status': "Available" if video_item['contentDetails']['caption'] == 'true' else "Not Available",
                    'video_duration': parse_iso8601_duration(video_item['contentDetails']['duration']),
                    'video_name': video_item['snippet']['title'],
                    'video_description': video_item['snippet']['description'],
                    'video_likesCount': video_item['statistics'].get('likeCount', 0),
                    'video_viewCount': video_item['statistics'].get('viewCount', 0),
                    'video_dislikesCount': video_item['statistics'].get('dislikeCount', 0),
                    'video_commentCount': video_item['statistics'].get('commentCount', 0),
                    'video_favoriteCount': video_item['statistics'].get('favoriteCount', 0)
                }
                video_data_list.append(data)

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    return video_data_list

def check_comments_enabled(video_id):
    request = youtube.videos().list(
        part="statistics",
        id=video_id)
    response = request.execute()
    if response['items']:
        comment_count = response['items'][0]['statistics'].get('commentCount', '0')
        if comment_count == '0':
            return False
        return True
    return False

def fetch_comments(video_id):
    if not check_comments_enabled(video_id):
        print(f"Comments are disabled for video {video_id}")
        return []

    request = youtube.commentThreads().list(
        part="snippet,replies",
        videoId=video_id,
        maxResults=100
    )
    response = request.execute()

    comments = []
    for item in response['items']:
        top_comment_snippet = item['snippet']['topLevelComment']['snippet']
        comment_id = item['id']

        comment_channel_id = top_comment_snippet.get('authorChannelId', {}).get('value', None)
        comment_video_id = item['snippet']['videoId']
        comment_text = top_comment_snippet['textDisplay']
        like_count = top_comment_snippet['likeCount']
        author = top_comment_snippet['authorDisplayName']
        published_date = format_datetime_for_mysql(top_comment_snippet['publishedAt'])

        top_comment = {
            "comment_id": comment_id,
            "comment_channel_id": comment_channel_id,
            "video_id": comment_video_id,
            "comment_text": comment_text,
            "comment_like_count": like_count,
            "comment_author": author,
            "comment_published_date": published_date
        }
        comments.append(top_comment)
    return comments

with tab2:
    st.write("Enter your Channel ID here.")
    channel_id = st.text_input("Channel ID", placeholder="Enter your Channel ID")
    if st.button("Submit Channel ID"):
        st.write(f"Channel ID submitted: {channel_data(channel_id)['channel_name']}")

    if st.button("Fetch and Save Data"):
        myconnection = pymysql.connect(host='127.0.0.1', user='root', passwd='Kamaraj@2000', database='youtube_streamlit')
        cursor = myconnection.cursor()
        # Ensure tables exist before inserting data
        progress_text = "Operation in progress. Please wait."
        my_bar = st.progress(0, text=progress_text)

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS channel_data (
            channel_id VARCHAR(255) PRIMARY KEY,
            channel_name VARCHAR(255),
            channel_descr TEXT,
            channel_Subs_count BIGINT,
            channel_video_count BIGINT,
            channel_views_count BIGINT,
            channel_playlist_id VARCHAR(255))''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_data (
            video_id VARCHAR(255) PRIMARY KEY,
            playlist_id VARCHAR(255),
            video_name VARCHAR(255),
            video_description TEXT,
            video_published_date DATETIME,
            video_viewCount BIGINT,
            video_likesCount BIGINT,
            video_dislikesCount BIGINT,
            video_commentCount BIGINT,
            video_favoriteCount BIGINT,
            video_duration INT,
            video_thumbnail VARCHAR(255),
            video_caption_status VARCHAR(255))''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_data (
            comment_id VARCHAR(255) PRIMARY KEY,
            comment_channel_id VARCHAR(255),
            video_id VARCHAR(255),
            comment_text TEXT,
            comment_like_count BIGINT,
            comment_author TEXT,
            comment_published_date DATETIME,
            FOREIGN KEY (video_id) REFERENCES video_data(video_id))''')

    # Fetch channel data and insert/update
        channels = channel_data(channel_id)

        insert_query = '''
            INSERT INTO channel_data (
                channel_id, channel_name, channel_descr, channel_Subs_count, channel_video_count, 
                channel_views_count, channel_playlist_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                channel_name=VALUES(channel_name), 
                channel_descr=VALUES(channel_descr), 
                channel_Subs_count=VALUES(channel_Subs_count), 
                channel_video_count=VALUES(channel_video_count), 
                channel_views_count=VALUES(channel_views_count), 
                channel_playlist_id=VALUES(channel_playlist_id)'''

        cursor.execute(insert_query, (
            channels['channel_id'], channels['channel_name'], channels['channel_descr'], 
            channels['channel_Subs_count'], channels['channel_video_count'], 
            channels['channel_views_count'], channels['channel_playlist_id']))
        myconnection.commit()

        # Fetch video data and insert/update
        videos = video_data(channel_id)
        insert_query_video_data = '''
            INSERT INTO video_data (
                video_id, playlist_id, video_name, video_description, video_published_date, 
                video_viewCount, video_likesCount, video_dislikesCount, video_commentCount, 
                video_favoriteCount, video_duration, video_thumbnail, video_caption_status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                video_name=VALUES(video_name), 
                video_description=VALUES(video_description), 
                video_published_date=VALUES(video_published_date), 
                video_viewCount=VALUES(video_viewCount), 
                video_likesCount=VALUES(video_likesCount), 
                video_dislikesCount=VALUES(video_dislikesCount), 
                video_commentCount=VALUES(video_commentCount), 
                video_favoriteCount=VALUES(video_favoriteCount), 
                video_duration=VALUES(video_duration), 
                video_thumbnail=VALUES(video_thumbnail), 
                video_caption_status=VALUES(video_caption_status)'''

        for video in videos:
            cursor.execute(insert_query_video_data, (
                video['video_id'], video['playlist_id'], video['video_name'], video['video_description'], 
                format_datetime_for_mysql(video['video_published_date']), video['video_viewCount'], 
                video['video_likesCount'], video['video_dislikesCount'], video['video_commentCount'], 
                video['video_favoriteCount'], video['video_duration'], video['video_thumbnail'], 
                video['video_caption_status']))
            myconnection.commit()

        # Fetch comment data and insert/update
        insert_query_comment_data = '''
            INSERT INTO comment_data (
                comment_id, comment_channel_id, video_id, comment_text, comment_like_count, 
                comment_author, comment_published_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                comment_text=VALUES(comment_text), 
                comment_like_count=VALUES(comment_like_count), 
                comment_author=VALUES(comment_author), 
                comment_published_date=VALUES(comment_published_date)'''

        for video in videos:
            video_id = video['video_id']
            comments = fetch_comments(video_id)
            for comment in comments:
                cursor.execute(insert_query_comment_data, (
                    comment['comment_id'], comment['comment_channel_id'], comment['video_id'], 
                    comment['comment_text'], comment['comment_like_count'], comment['comment_author'], 
                    comment['comment_published_date']))
            myconnection.commit()

        for percent_complete in range(100):
            time.sleep(0.00)
            my_bar.progress(percent_complete + 1, text=progress_text)
            time.sleep(0.06)
            my_bar.empty()
        st.success("Data fetched and saved successfully!")
    else:
        st.error("Please enter a valid YouTube Channel ID.")


channel_query = "SELECT * FROM channel_data WHERE channel_name = %s"
video_query = "SELECT * FROM video_data WHERE playlist_id = %s"
comment_query = "SELECT * FROM comment_data WHERE video_id IN (SELECT video_id FROM video_data WHERE playlist_id = %s)"

myconnection = pymysql.connect(host='127.0.0.1', user='root', passwd='Kamaraj@2000', database='youtube_streamlit')

st.sidebar.title("Specific channel data")    

# Get the list of channel names from the database
channel_names = pd.read_sql_query("SELECT channel_name FROM channel_data", myconnection)['channel_name'].tolist()
selected_channel = tab2.selectbox("Channel List", channel_names)
# Query and display data based on the selected channel
if selected_channel:
    channel_data = pd.read_sql_query(channel_query, myconnection, params=[selected_channel])
    tab2.subheader("Channel Data")
    tab2.write(channel_data)
# Execute the SQL query for video data
    video_data = pd.read_sql_query(video_query, myconnection, params=[channel_data['channel_playlist_id'].iloc[0]])
    tab2.subheader("Video Data")
    tab2.write(video_data)
# Execute the SQL query for comment data
    comment_data = pd.read_sql_query(comment_query, myconnection, params=[channel_data['channel_playlist_id'].iloc[0]])
    tab2.subheader("Comment Data")
    tab2.write(comment_data)

st.sidebar.header("Queries")

with tab3:
    tab3.header("Queries you may have")
    
    queries = {
        "What are the names of all the videos and their corresponding channels?": '''SELECT video_data.video_name, channel_data.channel_name 
                                                                    FROM video_data
                                                                    INNER JOIN channel_data
                                                                    ON channel_data.channel_playlist_id = video_data.playlist_id;''',
        "Which channels have the most number of videos, and how many videos do they have?": '''SELECT channel_name, channel_video_count FROM channel_data
                                                    WHERE channel_video_count = (SELECT MAX(channel_video_count) FROM channel_data);''',
        "What are the top 10 most viewed videos and their respective channels?": '''SELECT channel_data.channel_name, video_data.video_name, video_data.video_viewCount 
                                                                    FROM video_data
                                                                    INNER JOIN channel_data 
                                                                    ON channel_data.channel_playlist_id = video_data.playlist_id
                                                                    ORDER BY video_data.video_viewCount DESC
                                                                    LIMIT 10;''',
        " How many comments were made on each video, and what are their corresponding video names?": '''SELECT channel_data.channel_name,video_data.video_name, video_data.video_commentCount
                                                                                FROM video_data
                                                                                INNER JOIN channel_data 
                                                                    ON channel_data.channel_playlist_id = video_data.playlist_id;''',
        "Which videos have the highest number of likes, and what are their corresponding channel names?": """ select channel_data.channel_name,video_data.video_name, video_data.video_likesCount
                                                                                    from video_data inner join
                                                                                    channel_data
                                                                                    on channel_data.channel_playlist_id = video_data.playlist_id
                                                                                    group by channel_data.channel_name, video_data.video_name, video_data.video_likesCount
                                                                                    order by video_likesCount desc
                                                                                    limit 10;""",
        "What is the total number of likes and dislikes for each video, and what are their corresponding video names?": '''SELECT video_data.video_name, video_data.video_likesCount, video_data.video_dislikesCount
                                                                FROM video_data;''',
        "What is the total number of views for each channel, and what are their corresponding channel names?": '''SELECT channel_data.channel_name, channel_data.channel_views_count FROM channel_data;''',
        "What are the names of all the channels that have published videos in the year 2022?": '''SELECT channel_data.channel_name FROM channel_data
                                                                INNER JOIN video_data
                                                                ON channel_data.channel_playlist_id = video_data.playlist_id
                                                                WHERE YEAR(video_data.video_published_date) = 2022;''',
        "What is the average duration of all videos in each channel, and what are their corresponding channel names?": '''SELECT channel_data.channel_name, AVG(video_data.video_duration) AS avg_duration
                                                            FROM video_data
                                                            INNER JOIN channel_data
                                                            ON channel_data.channel_playlist_id = video_data.playlist_id
                                                            GROUP BY channel_data.channel_id;''',
        "Which videos have the highest number of comments, and what are their corresponding channel names?": '''SELECT channel_data.channel_name, video_data.video_name, video_data.video_commentCount
                                                                                                FROM video_data
                                                                                                INNER JOIN channel_data
                                                                                                ON channel_data.channel_playlist_id = video_data.playlist_id
                                                                                                ORDER BY video_data.video_commentCount DESC
                                                                                                limit 10;''' }

    query_option = tab3.selectbox("Select a query to run", list(queries.keys()))

    if tab3.button("Run Query"):
        query = queries[query_option]
        myconnection = pymysql.connect(host='127.0.0.1', user='root', passwd='Kamaraj@2000', database='youtube_streamlit')
        cursor = myconnection.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        myconnection.close()
        df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
        print("DataFrame:")
        print(df)  # Print the DataFrame to inspect its contents
        tab3.table(df)

    # Store the dataframe in session state for later use
        st.session_state['df'] = df 
        st.session_state['query_option'] = query_option

# Check if a DataFrame exists in the session state
if 'df' in st.session_state and not st.session_state['df'].empty:
    if tab3.button("Pictorial representation"):
        df = st.session_state['df']
        query_option = st.session_state['query_option']
        
        # Create the appropriate plot based on the query option
        if query_option == "Which channels have the most number of videos, and how many videos do they have?":
            fig = px.bar(df, x="channel_name", y="channel_video_count", hover_data= "channel_video_count", title="Channels having most number of videos")
            tab3.plotly_chart(fig)
        elif query_option == "What are the top 10 most viewed videos and their respective channels?":
            fig = px.bar(df, x="video_name", y="video_viewCount", color="channel_name", title="Top 10 most viewed videos")
            tab3.plotly_chart(fig)
        elif query_option == "Which videos have the highest number of likes, and what are their corresponding channel names?":
            fig = px.bar(df, x="video_name", y="video_likesCount", color="channel_name", hover_data= "video_likesCount", title="Most Liked videos")
            tab3.plotly_chart(fig)
        elif query_option == "What is the total number of views for each channel, and what are their corresponding channel names?":
            fig = px.bar(df, x="channel_name", y="channel_views_count",hover_data= "channel_views_count",title="Total Number of Views")
            tab3.plotly_chart(fig)
        elif query_option == "What is the average duration of all videos in each channel, and what are their corresponding channel names?":
            fig = px.bar(df, x="channel_name", y="avg_duration",title="Average Duration of all videos")
            tab3.plotly_chart(fig)
        elif query_option == "Which videos have the highest number of comments, and what are their corresponding channel names?":
            fig = px.bar(df, x="video_name", y="video_commentCount", color="channel_name", hover_data= "video_commentCount", title="Most commented videos")
            tab3.plotly_chart(fig)
        else:
            st.warning("Graph for this query option is not configured yet.")
