# flask
from flask import (
    Flask,
    request,
    abort
)

# Linebot-sdk
from linebot import (
    LineBotApi,
    WebhookHandler
)

from linebot.exceptions import (
    InvalidSignatureError
)

from linebot.models.events import (
    FollowEvent,
    MessageEvent
    # PostbackEvent
)

from linebot.models.messages import (
    TextMessage
    # ImageMessage

)

from linebot.models.send_messages import (
    TextSendMessage
    # ImageSendMessage
)


# Other utile modules
from pprint import pprint
import json
import requests
from pymongo import MongoClient, ReturnDocument
from googletrans import Translator, LANGCODES


# load necessary Linebot information to use LineBotApi
with open("../line_secret_key", "r", encoding="utf-8") as infile:
    conf_json = json.load(infile)

channel_access_token = conf_json.get("channel_access_token")  # 回傳訊息給 Line 時使用
secret_key = conf_json.get("secret_key")  # WebhookHandler驗證事件消息是否來自Line使用
linebot_developer_id = conf_json.get("self_user_id")
server_url = "https://" + conf_json.get("server_url")
rich_menu_id = conf_json.get("rich_menu_id")


# load mongodb settings
with open("../mongo_client_settings", "r", encoding="utf-8") as infile:
    mongo_client_settings = json.loads(infile.read())

line_bot_api = LineBotApi(channel_access_token) # 回傳訊息給 Line 時使用
handler = WebhookHandler(secret_key) # WebhookHandler驗證事件消息是否來自Line使用


# Make the arranged lang_list
LANGCODES["chinese_tw"] = LANGCODES.pop("chinese (traditional)")
LANGCODES["chinese_cn"] = LANGCODES.pop("chinese (simplified)")
LANGCODES["kurdish"] = LANGCODES.pop("kurdish (kurmanji)")
LANGCODES["myanmar"] = LANGCODES.pop("myanmar (burmese)")
LANGCODES.pop("Filipino")
LANGCODES.pop("Hebrew")

lang_list = sorted([key for key in LANGCODES])

# New a tranlator to deal with translation requests
translator = Translator(service_urls=['translate.google.com',
                                      'translate.google.com.tw',
                                      'translate.google.co.kr',
                                      'translate.google.co.jp'
                                     ]
                       )


app = Flask(__name__, static_url_path="/res", static_folder="../res")


# Line MessegeEvent entrypoint
@app.route("/", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    print(body)
    app.logger.info("Request body: " + body)

    # Line webhook url verification testing
    if eval(body).get("events")[0].get("source").get("userId") == "Udeadbeefdeadbeefdeadbeefdeadbeef":
        return "OK"

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# handle FollowEvent
"""
1. Get user info and save it
2. Bind function UI to the user
3. Send "Welcome" messages to the user

"""

follow_message_list = [
    TextSendMessage("Welcome to MyTranslator bot."),
    TextSendMessage("This bot would translate any language input to English by default."),
    TextSendMessage("You can easily use the rich menu to change the translated language to English, Japanese or French."),
    TextSendMessage("Or you can type ^to_LANGUAGE format to change the translated language you want."),
    TextSendMessage("To see the available translated languages, type lang_list to get the information.")
]

@handler.add(FollowEvent)
def follows(event):
    uri = mongo_client_settings.get("uri")
    port = mongo_client_settings.get("port")
    conn = MongoClient(uri, port=port)
    db = conn.translator
    collection = db.translator_users

    # check if the user already a member
    is_already_member = collection.find_one({"userId": event.source.user_id})

    if is_already_member is not None:
        print("An old friend comes back.")
        pprint(is_already_member)

    # Get user info and save it
    else:
        user_profile = line_bot_api.get_profile(event.source.user_id)
        user_profile = user_profile.as_json_dict()
        user_profile["src"] = "auto"
        user_profile["dest"] = "en"
        pprint(user_profile)
        #     print(type(user_profile))
        #     pprint(user_profile.__doc__)
        #     with open("../users.json", "a", encoding="utf-8") as outfile:
        #         outfile.write(json.dumps(user_profile))
        #         outfile.write("\n")

        try:
            inserted_user_id = collection.insert_one(user_profile).inserted_id
        except errors.InvalidDocument as inv_doc_err:
            print(inv_doc_err)

        # Bind the rich menu to the user
        bind_rich_menu_base_url = 'https://api.line.me/v2/bot/user/%s/richmenu/%s'
        bind_rich_menu_id = rich_menu_id

        bind_rich_menu_id_upload_endpoint = bind_rich_menu_base_url % (event.source.user_id, bind_rich_menu_id)
        bind_rich_menu_request_headers = {'Content-Type': 'image/jpeg',
                                          'Authorization': 'Bearer %s' % channel_access_token
                                          }

        bind_rich_menu_response = requests.post(bind_rich_menu_id_upload_endpoint,
                                                headers=bind_rich_menu_request_headers)
        print("LINE binding rich menu response: ", bind_rich_menu_response)

    # Send "Welcome" messages
    line_bot_api.reply_message(event.reply_token,
                               follow_message_list)


# 接 mongodb
@handler.add(MessageEvent, message=TextMessage)
def translate(event):
    """
    step1. 建立Mongodb連線
    step2. 檢查是否要改翻譯目標語言，並把用戶的翻譯設定撈出來
    step3. 呼叫 googletrans API 並把翻譯內容回傳使用者

    """

    def _getUserTranslationSettings(user_profile):
        user_profile = collection.find_one({"userId": userId})
        return user_profile

    def _changeUserTranslationDest(user_profile, dest):
        user_lang_modified = collection.find_one_and_update(filter={"userId": userId},
                                                            update={"$set": {"dest": dest}},
                                                            return_document=ReturnDocument.AFTER)
        return user_lang_modified

    def _changSettings():
        lang = event.message.text[4:]
        dest = LANGCODES.get(lang)
        user_lang_modified = _changeUserTranslationDest(user_profile, dest=dest)
        print("Translated destination language is successfully changed to: %s" % user_lang_modified.get("dest"))
        return user_lang_modified

    # step1
    #     with open("../mongo_client_settings", "r", encoding="utf-8") as infile:
    #         mongo_client_settings = json.loads(infile.read())

    uri = mongo_client_settings.get("uri")
    port = mongo_client_settings.get("port")
    conn = MongoClient(uri, port=port)
    db = conn.translator
    collection = db.translator_users

    # step2
    user_profile = line_bot_api.get_profile(event.source.user_id).as_json_dict()
    userId = user_profile.get("userId")

    if event.message.text.find("^to_") != -1:  # find("pattern")回傳值型態為 int， 若有這個字串，回傳0：沒有這個字串則回傳-1
        user_lang_modified = _changSettings()
        change_settings_msg = TextSendMessage(
            "The translated language is successfully changed to %s."%(event.message.text[4:]))
        line_bot_api.reply_message(event.reply_token,
                                   change_settings_msg
                                   )
    elif event.message.text.find("lang_list") != -1:
        lang_list_msg = TextSendMessage(str(lang_list))
        line_bot_api.reply_message(event.reply_token,
                                   lang_list_msg
                                   )
    else:
        # step3
        user_profile = _getUserTranslationSettings(user_profile)  # return the user_profile with "src" and "dest"

        dest = user_profile.get("dest")

        translated_text_send_message = TextSendMessage(translator.translate(event.message.text, dest=dest).text)

        line_bot_api.reply_message(event.reply_token,
                                   translated_text_send_message
                                   )

if __name__ == "__main__":
    app.run(host="0.0.0.0")