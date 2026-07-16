from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
app=FastAPI(title='mock detector')
class TextBody(BaseModel): content:str
@app.get('/health')
def health(): return {'ok':True,'version':'mock-1.0','modalities':['video','audio','text']}
@app.post('/api/v1/detect/text')
def text(body:TextBody):
    ad=any(x in body.content for x in ['加微信','免费咨询','全国接单','点击头像'])
    return {'data':{'content_category':'疑似' if ad else '合规','content_result':[{'label':'advertising' if ad else 'normal','confidence':0.92 if ad else 0.98,'risk_words':['加微信'] if '加微信' in body.content else []}]}}
@app.post('/api/v1/detect/video')
async def video(file:UploadFile=File(...)): return {'data':{'content_category':'合规','content_result':[{'label':'video-normal','confidence':0.95}]}}
@app.post('/api/v1/detect/audio')
async def audio(file:UploadFile=File(...)): return {'data':{'content_category':'合规','content_result':[{'label':'audio-normal','confidence':0.95}]}}
