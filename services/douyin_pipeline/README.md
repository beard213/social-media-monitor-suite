# 评论抓取 + 词表匹配 后端

对指定的一批 YouTube 博主，**逐个视频**抓取：封面、标题等元信息，以及评论区的
**用户 id + 评论内容**(不下载视频)；再用**两个词表**匹配评论，找出提到这些词的用户。
结果持久化到磁盘，可增量重跑。

---

## 一、环境准备(首次)

1. **Python 3.10+**，安装依赖：
   ```bat
   pip install -r requirements.txt
   ```
2. **Node.js**(YouTube 反爬 bgutil 需要)：安装后在包内构建 bgutil 依赖：
   ```bat
   cd bgutil-ytdlp-pot-provider\server
   npm install
   cd ..\..
   ```
   > 包里已带 bgutil 的编译产物(`server\build`)，只需 `npm install` 补运行依赖。

3. **配置 YouTube 登录 cookies(强烈建议，几乎必须)**

   不配的话，YouTube 会把脚本当机器人，报
   `Sign in to confirm you're not a bot`，一条评论都抓不到。
   注意：**浏览器登录 ≠ 脚本登录**，必须把 cookie 导给脚本。按顺序做：

   1. 浏览器装扩展 **「Get cookies.txt LOCALLY」**(Chrome/Edge 应用商店都有)。
   2. 浏览器**登录 youtube.com**。
   3. 停在 youtube.com 页面，点扩展 → **Export**，保存成 `cookies.txt`(Netscape 格式)。
   4. 把 `cookies.txt` **直接放到本文件夹**(和 `抓取评论.bat` 同一层)。
      脚本会自动识别，**不用改任何代码或设环境变量**。
   5. 双击 `抓取评论.bat` 开跑。

   > cookie 会过期(通常几天~几周)，报 bot 错误时重新导一份覆盖即可。
   > 也可设环境变量 `CRAWLER_COOKIES_FILE` 指到别处的 cookies.txt。

---

## 二、配置要抓的博主

编辑 `config.py` 里的 `CHANNELS` 列表(YouTube 频道的 `/videos` 页地址)。
输出目录默认在包内 `output\`，可用环境变量 `SCRAPE_OUTPUT` 改到别处。

---

## 三、抓取评论

双击 **`抓取评论.bat`**，或：
```bat
python scrape_comments.py --limit 100      # 每个频道抓最新 100 个视频
```
常用参数：
- `--limit N`   每个频道抓多少个视频
- `--channel K` 只抓第 K 个频道(1 起)
- `--refresh`   忽略已抓记录，强制重抓
- `--loop 120`  每 120 分钟循环补抓(常驻)

**产出结构**(`output\comment_dataset\`)：
```
<频道>\<video_id__标题>\
  ├ metadata.json   标题/封面URL/上传日期/播放·点赞·评论数/简介/标签...
  ├ comments.json   [{id, author, author_id, text, like_count, time_text, parent, is_reply}]
  └ cover.jpg
```
> 带增量记录 `_seen.json`：重跑只补新视频。每视频评论上限在 `scrape_comments.py` 顶部
> `MAX_COMMENTS`(默认 500)可调。

---

## 四、词表匹配

1. 准备两个词表，放到包内 `wordlists\`：
   - `events.jsonl`、`chains.jsonl`
   - 格式：**每行一个 JSON**，形如 `{"word": "某个词"}`
2. 双击 **`匹配词表.bat`**，或：
   ```bat
   python match_keywords.py
   ```
   可选参数：`--dataset`(数据集目录)、`--events`/`--chains`(词表路径)、`--min-len`(忽略过短词)。

**产出**(`output\comment_dataset\_match_result\`)：
| 文件 | 内容 |
|------|------|
| `matched_users.csv` | 每个命中用户一行(Excel 可开)：用户id/用户名/命中数/各词表命中词/所在频道 |
| `matched_users.json` | 每用户完整汇总 + 样例评论 |
| `match_details.jsonl` | 每条命中评论一行 |
| `summary.json` | 总体统计 + 高频命中词 |

---

## 五、说明

- 仅抓取**公开**评论；请遵守 YouTube 条款与当地法规，合理频率使用。
- 大批量抓取时 YouTube 可能限流：放慢 `SCRAPE_SLEEP`、配登录 cookies 会更稳。
- 本包**不含**任何词表和抓取结果，需各自准备。


---

## 六、抖音直播采集（新增）

如果 YouTube 无法访问，可以改用国内抖音直播作为视频来源。新增脚本 `douyin_live_capture.py` 支持：

- 每 120 秒保存一段直播视频；
- 自动从视频抽取 wav 音频；
- 可选用 FunASR 或 faster-whisper 生成文本；
- 输出到专属目录 `output/douyin_live_dataset/`，不和原评论数据混在一起。

快速运行：

```bat
python douyin_live_capture.py --source "测试=https://live.douyin.com/你的直播间ID" --segment 120 --transcribe none
```

详细说明见：`抖音直播采集说明.md`。
