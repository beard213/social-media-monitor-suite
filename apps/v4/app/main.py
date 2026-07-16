from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.db.session import Base, engine
from app.db import models  # noqa
from app.api.routes import router
from app.api.console import router as console_router

Base.metadata.create_all(engine)
app=FastAPI(title=settings.app_name,version="4.0.0",description="公开内容事件级监测、区域筛选、评论采集、内容线索扩展与多模态检测；短视频搜索接口预留给外部项目方，直播支持按平台与房间ID接入；平台数据须通过授权连接器或 Provider Ingest 接入。")
@app.middleware("http")
async def optional_api_key(request:Request, call_next):
    if settings.admin_api_key and request.url.path.startswith('/api'):
        if request.headers.get('X-API-Key') != settings.admin_api_key:
            return JSONResponse(status_code=401,content={"detail":"invalid api key"})
    return await call_next(request)

app.include_router(router)
app.include_router(console_router)
app.mount('/static',StaticFiles(directory='web/static'),name='static')
@app.get('/',include_in_schema=False)
def index(): return FileResponse('web/index.html')

# V4直播页面功能热修复：添加成功提示与删除任务按钮
from app.live_ui_hotfix import install_live_ui_hotfix
install_live_ui_hotfix(app)

