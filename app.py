from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
import openai
import os

app = Flask(__name__)

# 環境變數設定（記得部署時設定這些變數）
openai.api_key = os.getenv('OPENAI_API_KEY')
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler1 = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 全域變數：OpenAI 回應計數
openai_response_counter = 0

@app.route('/callback', methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler1.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler1.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global openai_response_counter
    user_input = event.message.text.strip()

    # 🎨 如果開頭是「畫圖：」或「繪圖：」，使用 DALL·E 生圖
    if user_input.startswith("畫圖：") or user_input.startswith("繪圖："):
        prompt = user_input.split("：", 1)[-1].strip()
        try:
            dalle_response = openai.Image.create(
                prompt=prompt,
                n=1,
                size="1024x1024"
            )
            image_url = dalle_response['data'][0]['url']
            openai_response_counter += 1  # 計數 +1

            messages = [
                ImageSendMessage(
                    original_content_url=image_url,
                    preview_image_url=image_url
                ),
                TextSendMessage(text=f"🖼️ 這是你要的圖！\n📊 OpenAI 已產生回應次數：{openai_response_counter}")
            ]
            line_bot_api.reply_message(event.reply_token, messages)
        except Exception as e:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"產生圖片時發生錯誤：{e}"))
        return

    # 🌐 否則預設為中翻英老師
    try:
        response = openai.ChatCompletion.create(
            messages=[
                {"role": "system", "content": "你是一位中翻英老師，請將使用者輸入的中文句子翻譯成英文，並簡短說明語法或用法重點。"},
                {"role": "user", "content": user_input}
            ],
            model="gpt-4o-mini-2024-07-18",
            temperature=0.5,
        )
        ret = response['choices'][0]['message']['content'].strip()
        openai_response_counter += 1  # 計數 +1
        ret += f"\n\n📊 OpenAI 已產生回應次數：{openai_response_counter}"
    except Exception as e:
        ret = f"⚠️ 發生錯誤：{e}"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ret))

if __name__ == '__main__':
    app.run()
