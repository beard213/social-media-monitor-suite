import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


RULES = {
    "涉稳风险": ["讨薪", "上访", "集会", "聚集", "维权", "冲击"],
    "暴恐风险": ["炸弹", "爆炸", "袭击", "枪支", "纵火"],
    "违法风险": ["诈骗", "赌博", "毒品", "卖淫"],
    "军事安全": ["军校偷拍", "部队偷拍", "军事偷拍"],
    "政治敏感": ["敌对势力", "颠覆", "煽动"],
}


class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        raw = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(status)
        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )
        self.send_header(
            "Content-Length",
            str(len(raw))
        )
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            self.send_json({
                "status": "ok",
                "service": "douyin-demo-text-detector"
            })
            return

        self.send_json(
            {"detail": "Not Found"},
            status=404
        )

    def do_POST(self):
        if self.path != "/api/v1/detect/text":
            self.send_json(
                {"detail": "Not Found"},
                status=404
            )
            return

        try:
            length = int(
                self.headers.get("Content-Length", "0")
            )

            payload = json.loads(
                self.rfile.read(length).decode("utf-8")
            )

            content = str(
                payload.get("content", "")
            )
        except Exception as exc:
            self.send_json(
                {"detail": repr(exc)},
                status=400
            )
            return

        labels = []
        risk_words = []

        for label, words in RULES.items():
            hits = [
                word for word in words
                if word in content
            ]

            if hits:
                labels.append(label)
                risk_words.extend(hits)

        if labels:
            category = "疑似"
            confidence = 0.88
        else:
            category = "合规"
            confidence = 0.93

        result = {
            "content_category": category,
            "labels": labels,
            "risk_words": risk_words,
            "max_confidence": confidence,
            "confidence": confidence,
            "suggestion": (
                "review" if labels else "pass"
            ),
            "conclusion": category
        }

        self.send_json({
            "code": 0,
            "message": "success",
            "data": {
                **result,
                "upstream_response": {
                    "data": result
                },
                "text_detection": {
                    "data": result
                },
                "result": result
            }
        })

    def log_message(self, fmt, *args):
        print(
            "[DETECTOR]",
            fmt % args,
            flush=True
        )


server = ThreadingHTTPServer(
    ("127.0.0.1", 8080),
    Handler
)

print(
    "Detector listening on "
    "http://127.0.0.1:8080",
    flush=True
)

server.serve_forever()
