import json
import time
import urllib.request
from pathlib import Path


OUTPUT = Path(
    "output/douyin_live_dataset"
)

AUDIT_URL = "http://localhost:8080"


def post_json(url, data):

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        }
    )

    with urllib.request.urlopen(
        req,
        timeout=120
    ) as r:
        return json.loads(
            r.read()
        )


def upload_file(url, file):

    boundary = "----audit"

    body = []

    body.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{file.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    )

    body.append(
        file.read_bytes()
    )

    body.append(
        f"\r\n--{boundary}--\r\n"
    )

    data = b""

    for x in body:
        if isinstance(x,str):
            x=x.encode()
        data+=x


    req=urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type":
            f"multipart/form-data; boundary={boundary}"
        }
    )


    with urllib.request.urlopen(
        req,
        timeout=300
    ) as r:

        return json.loads(
            r.read()
        )



def audit_segment(folder):


    video=list(folder.glob("video/*.mp4"))
    audio=list(folder.glob("audio/*.wav"))
    text=list(folder.glob("text/*.txt"))


    result={}


    # 视频
    for f in video:

        print(
            "检测视频:",
            f
        )

        result["video"]=upload_file(
            AUDIT_URL+
            "/api/v1/detect/video",
            f
        )


    # 音频

    for f in audio:

        print(
            "检测音频:",
            f
        )

        result["audio"]=upload_file(
            AUDIT_URL+
            "/api/v1/detect/audio",
            f
        )



    # 文本

    for f in text:

        content=f.read_text(
            encoding="utf-8"
        )


        if (
            "未启用语音转写"
            in content
        ):
            continue


        print(
            "检测文本:",
            f
        )


        result["text"]=post_json(
            AUDIT_URL+
            "/api/v1/detect/text",
            {
                "content":content
            }
        )


    out=folder/"audit_all.json"


    out.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print(
        "完成:",
        out
    )



def loop():

    while True:

        for account in OUTPUT.iterdir():

            if account.is_dir():

                audit_segment(
                    account
                )


        time.sleep(30)



if __name__=="__main__":

    loop()