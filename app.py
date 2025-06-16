import streamlit as st
import pandas as pd
import random
import requests
from datetime import datetime
from fuzzywuzzy import process, fuzz
import os
import io
import re # 用於正則表達式，提取 YouTube 影片 ID

# --- 常數定義 ---
API_KEY = 'CWA-0E43DDDC-2610-4A83-82F4-5F26478F0A8E' # 請替換為您的 API 金鑰

GITHUB_USERNAME = "SantanaWang" # <-- 請將此處替換為您的 GitHub 用戶名
GITHUB_REPOSITORY = "Weather"   # <-- 請將此處替換為您的儲存庫名稱
GITHUB_MAIN_BRANCH = "main" # 通常是 main 或 master

EXCEL_FILE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/{GITHUB_MAIN_BRANCH}/YT_weather_matched.xlsx"
MOVIE_POSTER_BASE_URL = f"https://raw.githubusercontent.com/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/{GITHUB_MAIN_BRANCH}/movie/"
GITHUB_API_MOVIE_DIR_URL = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPOSITORY}/contents/movie"


# --- 手動校正字典 & 天氣關鍵字映射 (保持不變) ---
MANUAL_CORRECTIONS = {
    "台北市": "臺北市", "台北": "臺北市", "北市": "臺北市", "北": "臺北市",
    "新北": "新北市", "臺北縣": "新北市",
    "桃園": "桃園市", "桃園縣": "桃園市", "桃": "桃園市", "園": "桃園市",
    "台中": "臺中市", "台中市": "臺中市", "台中縣": "臺中市", "臺中縣": "臺中市", "中縣": "臺中市", "中市": "臺中市", "臺中": "臺中市", "中": "臺中市",
    "台南": "臺南市", "台南市": "臺南市", "臺南": "臺南市", "台南縣": "臺南市", "臺南縣": "臺南市",
    "高雄": "高雄市", "雄市": "高雄市",  "雄": "高雄市", "高雄縣": "高雄市",
    "基隆": "基隆市", "基": "基隆市", "隆": "基隆市", "雞": "基隆市", "籠": "基隆市", "雞籠": "基隆市", "基隆縣": "基隆市", "基市": "基隆市", "隆市": "基隆市", "雞市": "基隆市", "籠市": "基隆市", "雞籠市": "基隆市", "雞籠縣": "基隆市", "雞縣": "基隆市", "籠縣": "基隆市",
    "新竹": "新竹市", "竹": "新竹市", "竹市": "新竹市", "竹縣": "新竹縣",
    "嘉義": "嘉義市", "嘉": "嘉義市", "義": "嘉義市", "嘉縣": "嘉義縣", "義縣": "嘉義縣",
    "苗栗": "苗栗縣", "苗": "苗栗縣", "栗": "苗栗縣", "栗縣": "苗栗縣", "苗縣": "苗栗縣", "苗栗市": "苗栗縣",
    "彰化": "彰化縣", "彰": "彰化縣", "化": "彰化縣", "彰縣": "彰化縣", "化縣": "彰化縣", "彰化市": "彰化縣",
    "南投": "南投縣", "投": "南投縣", "投縣": "南投縣", "南投市": "南投縣",
    "雲林": "雲林縣", "雲": "雲林縣", "林": "雲林縣", "雲縣": "雲林縣", "林縣": "雲林縣", "雲林市": "雲林縣",
    "屏東": "屏東縣", "屏": "屏東縣", "屏縣": "屏東縣", "屏東市": "屏東縣", "琉球嶼": "屏東縣", "小琉球": "屏東縣", "琉球": "屏東縣",
    "宜蘭": "宜蘭縣", "宜": "宜蘭縣", "蘭": "宜蘭縣", "宜縣": "宜蘭縣", "蘭縣": "宜蘭縣", "宜蘭市": "宜蘭縣", "龜山島": "宜蘭縣",
    "花蓮": "花蓮縣", "花": "花蓮縣", "蓮": "花蓮縣", "花縣": "花蓮縣", "蓮縣": "花蓮縣", "花蓮市": "花蓮縣",
    "台東": "臺東縣", "台東縣": "臺東縣", "台東市": "臺東市", "綠島": "臺東縣", "綠鳥": "臺東縣", "蘭嶼": "臺東縣",
    "澎湖": "澎湖縣", "澎": "澎湖縣", "湖": "澎湖縣", "澎縣": "澎湖縣", "湖縣": "澎湖縣", "澎湖市": "澎湖縣",
    "金門": "金門縣", "金": "金門縣", "門": "金門縣", "金縣": "金門縣", "門縣": "金門縣", "金門市": "金門縣",
    "連江": "連江縣", "連江市": "連江縣", "馬祖": "連江縣", "馬縣": "連江縣", "祖縣": "連江縣", "連": "連江縣", "江": "連江縣", "連縣": "連江縣"
}

WEATHER_KEYWORDS_MAP = {
    "晴天": "晴", "晴朗": "晴", "太陽": "晴", "大太陽": "晴", "晴": "晴",
    "雨天": "雨", "下雨": "雨", "大雨": "雨", "小雨": "雨", "雷雨": "雨", "雨": "雨",
    "陰天": "陰", "灰濛濛": "陰", "陰沉": "陰", "陰": "陰",
    "多雲": "多雲", "雲": "多雲",
    "雪天": "雪", "下雪": "雪", "大雪": "雪", "暴雪": "雪", "雪": "雪",
}

# --- 工具函數 ---
@st.cache_data(ttl=3600)
def get_location_names():
    """從中央氣象署 API 獲取台灣縣市列表。"""
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={API_KEY}'
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        if 'records' in data and 'location' in data['records']:
            return [loc['locationName'] for loc in data['records']['location']]
    except requests.exceptions.RequestException as e:
        st.error(f"錯誤：無法獲取縣市列表，請檢查網路或 API 金鑰：{e}")
    return ["臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市", "基隆市", "新竹市", "嘉義市", "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"]

@st.cache_data(ttl=3600)
def get_weather_data(city_name):
    """根據城市名稱獲取天氣資訊。"""
    url = f'https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?Authorization={API_KEY}&locationName={city_name}'
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        data = res.json()
        if 'records' in data and 'location' in data['records'] and data['records']['location']:
            time_elements = data['records']['location'][0]['weatherElement'][0]['time']
            forecast = min(time_elements,
                           key=lambda x: abs(datetime.strptime(x['startTime'], '%Y-%m-%d %H:%M:%S') - datetime.now()))
            desc = forecast['parameter']['parameterName']
            start_dt = datetime.strptime(forecast['startTime'], '%Y-%m-%d %H:%M:%S')
            hour = start_dt.hour
            time_desc = "午夜到早晨" if 0<=hour<6 else "早晨到中午" if 6<=hour<12 else "中午到傍晚" if 12<=hour<18 else "傍晚到午夜"

            pop_data = next((elem for elem in data['records']['location'][0]['weatherElement'] if elem['elementName'] == 'PoP'), None)
            pop = "N/A"
            if pop_data:
                for pop_time in pop_data['time']:
                    if pop_time['startTime'] == forecast['startTime'] and pop_time['endTime'] == forecast['endTime']:
                        pop = pop_time['parameter']['parameterName'] + "%"
                        break

            display_text = f"{city_name} {start_dt.month}/{start_dt.day} {time_desc}是：**{desc}**，降雨機率**{pop}**喔！"
            return desc, display_text
        return None, "無法取得天氣資料：資料結構異常或該縣市無預報資料。"
    except requests.exceptions.RequestException as e:
        return None, f"無法取得天氣資料：網路或 API 錯誤 ({e})"
    except Exception as e:
        return None, f"處理天氣資料時發生錯誤: {e}"

@st.cache_data(ttl=3600)
def initialize_videos(excel_url):
    """從指定的 Excel URL 讀取影片資料。"""
    try:
        response = requests.get(excel_url)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content))
        videos = []
        for _, row in df.iterrows():
            url, desc = str(row.get('影片URL','')), str(row.get('matched_weather_descriptions',''))
            if url and desc:
                if url.strip() and not pd.isna(url):
                    videos.append({'url': url.strip(), 'desc': desc.strip()})
        st.success(f"初始化影片列表，共 {len(videos)} 筆影片。")
        return videos
    except Exception as e:
        st.error(f"從 URL 讀取 Excel 檔案時發生錯誤: {e}")
        return []

@st.cache_data(ttl=3600)
def get_movie_poster_urls_from_github():
    """從 GitHub API 動態獲取 movie 資料夾中的所有圖片 URL。"""
    try:
        response = requests.get(GITHUB_API_MOVIE_DIR_URL)
        response.raise_for_status()
        files_data = response.json()

        poster_urls = []
        for file in files_data:
            if file['type'] == 'file' and (file['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.gif'))):
                poster_urls.append(f"{MOVIE_POSTER_BASE_URL}{file['name']}")
        st.success(f"成功從 GitHub 資料夾獲取 {len(poster_urls)} 張電影海報 URL。")
        return poster_urls
    except requests.exceptions.RequestException as e:
        st.error(f"從 GitHub API 獲取電影海報列表時發生錯誤: {e}")
        st.warning("將使用預設的空列表作為備用，可能無法推薦電影海報。")
        return []

# --- 新增：提取 YouTube 影片 ID 的函數 ---
def extract_youtube_id(url):
    """
    從 YouTube URL 中提取影片 ID。
    支援的 URL 格式：
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtu.be/dQw4w9WgXcQ
    - https://m.youtube.com/watch?v=dQw4w9WgXcQ
    """
    # 匹配標準 watch URL
    match = re.search(r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    return None

# --- 核心邏輯函數 (修改音樂推薦相關) ---
def auto_correct_city(input_city, location_names):
    """自動校正城市名稱，優先使用手動校正，其次模糊匹配。"""
    corrected = MANUAL_CORRECTIONS.get(input_city, input_city)
    if corrected in location_names: return corrected
    if location_names:
        match, score, _ = process.extractOne(corrected, location_names, scorer=fuzz.ratio)
        if score >= 75: return match
    return None

def find_and_recommend_music(weather_desc, all_videos):
    """根據天氣描述推薦相關音樂，並返回文字描述和 YouTube ID。"""
    if not all_videos:
        return "音樂列表為空，無法推薦音樂。", None

    best_match, best_score = None, -1
    for video in all_videos:
        score = fuzz.partial_ratio(weather_desc, video['desc'])
        if score > best_score:
            best_match, best_score = video, score

    if best_match and best_score > 70:
        youtube_id = extract_youtube_id(best_match['url'])
        if youtube_id:
            return f"為您推薦與「{weather_desc}」相關的音樂：\n**{best_match['desc']}**", youtube_id
        else:
            return f"為您推薦與「{weather_desc}」相關的音樂：\n**[{best_match['desc']}]({best_match['url']})** (無法播放，請點擊連結)", None # 如果無法提取ID，提供連結
    else:
        return f"找不到與 '{weather_desc}' 相關的音樂，請嘗試隨機推薦。", None

def random_music_recommendation(all_videos):
    """隨機推薦一首音樂，並返回文字描述和 YouTube ID。"""
    if not all_videos:
        return "音樂列表為空，無法隨機推薦音樂。", None
    video = random.choice(all_videos)
    youtube_id = extract_youtube_id(video['url'])
    if youtube_id:
        return f"已為您隨機推薦了一首音樂：\n**{video['desc']}**", youtube_id
    else:
        return f"已為您隨機推薦了一首音樂：\n**[{video['desc']}]({video['url']})** (無法播放，請點擊連結)", None

def random_movie_recommendation(movie_poster_urls):
    """隨機推薦一部電影海報。"""
    if not movie_poster_urls:
        return "目前沒有可推薦的電影海報圖片。", None, 0

    if 'available_posters' not in st.session_state or not st.session_state.available_posters:
        st.session_state.available_posters = list(movie_poster_urls)

    if not st.session_state.available_posters:
        return "所有電影都已推薦完畢！(且無可重置的圖片)", None, 0

    poster_url = random.choice(st.session_state.available_posters)
    st.session_state.available_posters.remove(poster_url)

    display_name = os.path.splitext(os.path.basename(poster_url))[0]

    return display_name, poster_url, len(st.session_state.available_posters)


# --- Streamlit 應用程式主體 ---
def main():
    st.set_page_config(
        page_title="天氣心情點播機",
        layout="centered",
        initial_sidebar_state="auto"
    )

    st.title("天氣心情點播機")
    st.markdown("---")

    location_names = get_location_names()
    all_videos = initialize_videos(EXCEL_FILE_URL)
    movie_poster_urls = get_movie_poster_urls_from_github()

    city_input = st.text_input(
        "請輸入縣市名稱或天氣關鍵字：",
        placeholder="例如：臺北市 或 晴天",
        key="city_text_input"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("查詢天氣", key="btn_query_weather"):
            process_query(city_input, location_names, all_videos, movie_poster_urls, recommend_music=False)
        if st.button("隨機音樂推薦", key="btn_random_music"):
            # 隨機音樂推薦現在返回文本和 YouTube ID
            text_result, youtube_id = random_music_recommendation(all_videos)
            st.session_state.result_text = text_result
            st.session_state.recommended_youtube_id = youtube_id # 儲存 YouTube ID
            st.session_state.recommended_image_url = None # 清除海報顯示
            st.rerun()

    with col2:
        if st.button("查詢天氣並推薦音樂", key="btn_query_music"):
            process_query(city_input, location_names, all_videos, movie_poster_urls, recommend_music=True)
        if st.button("隨機電影推薦", key="btn_random_movie"):
            display_name, poster_url, remaining = random_movie_recommendation(movie_poster_urls)
            if poster_url:
                st.session_state.result_text = f"為您推薦電影：**{display_name}**\n(剩餘 {remaining} 張電影可推薦)"
                st.session_state.recommended_image_url = poster_url
            else:
                st.session_state.result_text = display_name
                st.session_state.recommended_image_url = None
            st.session_state.recommended_youtube_id = None # 清除音樂播放器
            st.rerun()

    st.markdown("---")

    # 顯示結果
    if 'result_text' in st.session_state and st.session_state.result_text:
        st.subheader("結果：")
        st.info(st.session_state.result_text)

    # 顯示推薦的 YouTube 影片
    if 'recommended_youtube_id' in st.session_state and st.session_state.recommended_youtube_id:
        st.video(f"https://www.youtube.com/watch?v={st.session_state.recommended_youtube_id}")
        st.caption("上方為推薦的 YouTube 影片") # 可以添加一個標題

    # 顯示推薦的電影海報
    if 'recommended_image_url' in st.session_state and st.session_state.recommended_image_url:
        st.image(st.session_state.recommended_image_url, caption="推薦電影海報", use_column_width=True)

    st.markdown("---")
    st.markdown("Powered by [Streamlit](https://streamlit.io/)")


# --- 處理查詢邏輯 (主要修改在音樂推薦部分) ---
def process_query(city_input, location_names, all_videos, movie_poster_urls, recommend_music):
    if 'result_text' not in st.session_state:
        st.session_state.result_text = ""
    if 'recommended_image_url' not in st.session_state:
        st.session_state.recommended_image_url = None
    if 'recommended_youtube_id' not in st.session_state: # 初始化 YouTube ID 狀態
        st.session_state.recommended_youtube_id = None

    if not city_input:
        st.session_state.result_text = "請輸入縣市名稱或天氣關鍵字！"
        st.session_state.recommended_image_url = None
        st.session_state.recommended_youtube_id = None
        st.rerun()
        return

    matched_type = None
    best_score = 0
    for keyword, anim_type in WEATHER_KEYWORDS_MAP.items():
        score = fuzz.ratio(city_input.lower(), keyword.lower())
        if score > best_score and score >= 70:
            best_score, matched_type = score, anim_type

    if matched_type:
        st.session_state.result_text = f"已識別關鍵字「{city_input}」，這類天氣適合的推薦功能將根據此關鍵字進行。"
        st.session_state.recommended_image_url = None
        st.session_state.recommended_youtube_id = None # 清除舊的音樂播放器

        if recommend_music:
            text_result, youtube_id = find_and_recommend_music(matched_type, all_videos) # 這裡要接收兩個返回值
            st.session_state.result_text += f"\n\n{text_result}"
            st.session_state.recommended_youtube_id = youtube_id # 儲存 YouTube ID
        st.rerun()
        return

    if any(char.isdigit() for char in city_input):
        st.session_state.result_text = "縣市名稱不能包含數字！"
        st.session_state.recommended_image_url = None
        st.session_state.recommended_youtube_id = None
        st.rerun()
        return

    corrected_city = auto_correct_city(city_input, location_names)
    if not corrected_city:
        st.session_state.result_text = f"無效或無法識別的縣市: **{city_input}**"
        st.session_state.recommended_image_url = None
        st.session_state.recommended_youtube_id = None
        st.rerun()
        return

    weather_desc, display_text = get_weather_data(corrected_city)
    st.session_state.result_text = display_text

    if weather_desc and recommend_music:
        text_result, youtube_id = find_and_recommend_music(weather_desc, all_videos) # 這裡要接收兩個返回值
        st.session_state.result_text += f"\n\n{text_result}"
        st.session_state.recommended_youtube_id = youtube_id # 儲存 YouTube ID

    st.session_state.recommended_image_url = None # 清除海報顯示
    st.rerun()


if __name__ == "__main__":
    # 在應用程式啟動時初始化 session state
    if 'result_text' not in st.session_state:
        st.session_state.result_text = "歡迎使用天氣心情點播機！"
    if 'recommended_image_url' not in st.session_state:
        st.session_state.recommended_image_url = None
    if 'recommended_youtube_id' not in st.session_state:
        st.session_state.recommended_youtube_id = None
    if 'available_posters' not in st.session_state:
        st.session_state.available_posters = []

    main()
