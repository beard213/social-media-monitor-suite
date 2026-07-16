import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  Shield, Monitor, Settings, Users, Bell,
  Search, Download, RefreshCw, Eye, Edit, Trash2, AlertTriangle,
  CheckCircle, Globe, Activity, Zap, LogOut, X, Plus, Upload,
  Video, MessageSquare, ChevronLeft, ChevronRight,
  Cpu, Play, FileBarChart, Key,
  Terminal, Flag, TrendingUp, TrendingDown,
  BarChart2, Server, UserCheck, Pause, Database, FileVideo, Link2, Square,
  AlertCircle, Info, Copy, Save, MapPin, Clock,
  SlidersHorizontal, Tag, Hash, Filter
} from "lucide-react";

const GLOBAL_STYLES = `
  @keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.25;} }
  @keyframes float { 0%,100%{transform:translateY(0px);} 50%{transform:translateY(-6px);} }
  .blink { animation:blink 1.4s ease-in-out infinite; }
  .float-anim { animation:float 4s ease-in-out infinite; }
  ::-webkit-scrollbar{width:4px;height:4px;}
  ::-webkit-scrollbar-track{background:transparent;}
  ::-webkit-scrollbar-thumb{background:rgba(59,130,246,0.25);border-radius:2px;}
`;

const DEMO_VIDEOS = [
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/SubaruOutbackOnStreetAndDirt.mp4",
];

type Page = "login"|"dashboard"|"accounts"|"alert"|"live"|"system";
type RiskLevel = "high"|"medium"|"low"|"safe";
interface Account { id:number; platform:string; name:string; uid:string; fans:string; status:string; risk:RiskLevel; lastCheck:string; tags:string[]; monitoring:boolean; }

const MAP_LOCATIONS = [
  {id:1,name:"FreedomVoice2024",lat:37.77,lng:-122.41,risk:"high" as RiskLevel,platform:"YouTube",city:"旧金山(美国)",fans:"847K",type:"AI生成"},
  {id:2,name:"china_analyst_hk",lat:22.32,lng:114.17,risk:"high" as RiskLevel,platform:"Twitter/X",city:"香港",fans:"234K",type:"境外渗透"},
  {id:3,name:"TruthSeeker99",lat:51.50,lng:-0.12,risk:"high" as RiskLevel,platform:"YouTube",city:"伦敦(英国)",fans:"1.1M",type:"虚假信息"},
  {id:4,name:"hk_voice_live",lat:22.38,lng:114.10,risk:"high" as RiskLevel,platform:"YouTube",city:"香港",fans:"320K",type:"违规内容"},
  {id:5,name:"asia_truth_net",lat:25.03,lng:121.57,risk:"high" as RiskLevel,platform:"Twitter/X",city:"台北",fans:"156K",type:"境外渗透"},
  {id:6,name:"ny_chinawatch",lat:40.71,lng:-74.01,risk:"high" as RiskLevel,platform:"YouTube",city:"纽约(美国)",fans:"432K",type:"AI生成"},
  {id:7,name:"jp_news_cn",lat:35.68,lng:139.69,risk:"medium" as RiskLevel,platform:"YouTube",city:"东京(日本)",fans:"89K",type:"信息操控"},
  {id:8,name:"sg_observer",lat:1.35,lng:103.82,risk:"medium" as RiskLevel,platform:"Twitter/X",city:"新加坡",fans:"67K",type:"境外"},
  {id:9,name:"aus_chinese_net",lat:-33.87,lng:151.21,risk:"medium" as RiskLevel,platform:"YouTube",city:"悉尼(澳大利亚)",fans:"94K",type:"信息操控"},
  {id:10,name:"科技前沿观察",lat:39.90,lng:116.40,risk:"high" as RiskLevel,platform:"抖音",city:"北京",fans:"2.3M",type:"AI内容"},
  {id:11,name:"时事速报站",lat:31.23,lng:121.47,risk:"medium" as RiskLevel,platform:"微博",city:"上海",fans:"892K",type:"敏感信息"},
  {id:12,name:"日常生活日记",lat:23.13,lng:113.27,risk:"medium" as RiskLevel,platform:"快手",city:"广州",fans:"1.2M",type:"伪造"},
  {id:13,name:"热舞达人小雨",lat:30.57,lng:104.07,risk:"medium" as RiskLevel,platform:"抖音",city:"成都",fans:"5.7M",type:"违规"},
  {id:14,name:"财经深度解析",lat:22.54,lng:114.06,risk:"low" as RiskLevel,platform:"抖音",city:"深圳",fans:"3.4M",type:"金融"},
  {id:15,name:"科技知识分享",lat:30.25,lng:120.15,risk:"low" as RiskLevel,platform:"B站",city:"杭州",fans:"456K",type:"AI辅助"},
  {id:16,name:"农村生活记录",lat:34.27,lng:108.95,risk:"safe" as RiskLevel,platform:"快手",city:"西安",fans:"3.1M",type:"正常"},
  {id:17,name:"cn_watch_2024",lat:22.26,lng:114.20,risk:"high" as RiskLevel,platform:"Twitter/X",city:"香港",fans:"178K",type:"境外渗透"},
];

const INITIAL_ACCOUNTS: Account[] = [
  {id:1,platform:"抖音",name:"科技前沿观察",uid:"DY_892341721",fans:"2.3M",status:"监测中",risk:"high",lastCheck:"2024-01-15 14:32",tags:["AI内容","科技"],monitoring:true},
  {id:2,platform:"YouTube",name:"FreedomVoice2024",uid:"YT_UC_x82Hq91",fans:"847K",status:"监测中",risk:"high",lastCheck:"2024-01-15 14:31",tags:["境外","涉政"],monitoring:true},
  {id:3,platform:"快手",name:"日常生活日记",uid:"KS_34892731",fans:"1.2M",status:"监测中",risk:"medium",lastCheck:"2024-01-15 13:45",tags:["伪造","生活"],monitoring:false},
  {id:4,platform:"Twitter/X",name:"china_analyst_hk",uid:"TW_1092847362",fans:"234K",status:"监测中",risk:"high",lastCheck:"2024-01-15 14:30",tags:["境外","矩阵"],monitoring:true},
  {id:5,platform:"微博",name:"时事速报站",uid:"WB_5634892",fans:"892K",status:"监测中",risk:"medium",lastCheck:"2024-01-15 14:28",tags:["新闻","敏感"],monitoring:false},
  {id:6,platform:"B站",name:"科技知识分享",uid:"BL_8923471",fans:"456K",status:"监测中",risk:"low",lastCheck:"2024-01-15 14:25",tags:["AI辅助","科教"],monitoring:false},
  {id:7,platform:"抖音",name:"热舞达人小雨",uid:"DY_763829401",fans:"5.7M",status:"监测中",risk:"medium",lastCheck:"2024-01-15 14:22",tags:["娱乐"],monitoring:false},
  {id:8,platform:"快手",name:"农村生活记录",uid:"KS_12837461",fans:"3.1M",status:"监测中",risk:"safe",lastCheck:"2024-01-15 14:18",tags:["三农","正常"],monitoring:false},
  {id:9,platform:"YouTube",name:"TruthSeeker99",uid:"YT_UC_ts99x",fans:"1.1M",status:"监测中",risk:"high",lastCheck:"2024-01-15 14:10",tags:["境外","虚假"],monitoring:true},
  {id:10,platform:"抖音",name:"财经深度解析",uid:"DY_234871920",fans:"3.4M",status:"暂停",risk:"low",lastCheck:"2024-01-15 12:30",tags:["财经"],monitoring:false},
];

const ALERT_DATA = [
  {id:1,platform:"YouTube",account:"FreedomVoice2024",uid:"YT_UC_x82Hq91",fans:"847K",type:"AI生成视频",risk:"high" as RiskLevel,time:"14:32:18",date:"2024-01-15",status:"待处置",title:"【内幕】某省政府秘密会议录音曝光全程",duration:"03:42",views:"23.4万",confidence:97.3,city:"旧金山(美国)",findings:["深度伪造人脸","AI合成声音","境外IP地址","账号矩阵关联"],scores:{deepfake:97,aiGen:94,political:89,spread:72,violence:3}},
  {id:2,platform:"Twitter/X",account:"china_analyst_hk",uid:"TW_1092847362",fans:"234K",type:"境外渗透",risk:"high" as RiskLevel,time:"14:31:54",date:"2024-01-15",status:"待处置",title:"转：经内部人士确认，XX即将被免职【速传】",duration:"-",views:"18.7万",confidence:96.1,city:"香港",findings:["境外账号","矩阵协同","批量转发","情绪煽动"],scores:{deepfake:12,aiGen:67,political:96,spread:93,violence:5}},
  {id:3,platform:"YouTube",account:"TruthSeeker99",uid:"YT_UC_ts99x",fans:"1.1M",type:"虚假信息",risk:"high" as RiskLevel,time:"14:28:41",date:"2024-01-15",status:"审核中",title:"中国经济真实数据被隐瞒？深度解析",duration:"12:18",views:"8.3万",confidence:88.4,city:"伦敦(英国)",findings:["数据造假","断章取义","境外媒体背景","高频发布"],scores:{deepfake:34,aiGen:78,political:88,spread:65,violence:0}},
  {id:4,platform:"抖音",account:"科技前沿观察",uid:"DY_892341721",fans:"2.3M",type:"AI生成内容",risk:"high" as RiskLevel,time:"14:27:03",date:"2024-01-15",status:"待处置",title:"AI技术内幕揭秘：这些都是真实发生的！",duration:"05:21",views:"45.6万",confidence:91.2,city:"北京",findings:["AI生成画面","虚假专家","诱导性标题","高播放量"],scores:{deepfake:91,aiGen:94,political:62,spread:78,violence:0}},
  {id:5,platform:"快手",account:"日常生活日记",uid:"KS_34892731",fans:"1.2M",type:"伪造视频",risk:"medium" as RiskLevel,time:"14:25:18",date:"2024-01-15",status:"已处置",title:"街头采访：市民如何评价最近的政策",duration:"08:34",views:"12.1万",confidence:76.8,city:"广州",findings:["剪辑拼接","音频伪造","场景不一致"],scores:{deepfake:55,aiGen:45,political:77,spread:42,violence:0}},
  {id:6,platform:"微博",account:"时事速报站",uid:"WB_5634892",fans:"892K",type:"敏感信息",risk:"medium" as RiskLevel,time:"14:22:47",date:"2024-01-15",status:"审核中",title:"网友爆料：某地发生重大事故，现场视频",duration:"-",views:"31.2万",confidence:71.3,city:"上海",findings:["未经证实","情绪化表述","标题党","转发诱导"],scores:{deepfake:18,aiGen:33,political:71,spread:81,violence:12}},
  {id:7,platform:"YouTube",account:"hk_voice_live",uid:"YT_hkvl_2024",fans:"320K",type:"违规直播",risk:"high" as RiskLevel,time:"14:18:22",date:"2024-01-15",status:"待处置",title:"【直播】香港最新现场实况（24小时不间断）",duration:"直播中",views:"5.2万",confidence:85.6,city:"香港",findings:["违规内容","境外传播","实名攻击","煽动性语言"],scores:{deepfake:22,aiGen:41,political:86,spread:74,violence:28}},
  {id:8,platform:"Twitter/X",account:"asia_truth_net",uid:"TW_atn_2024",fans:"156K",type:"协同操控",risk:"high" as RiskLevel,time:"14:12:05",date:"2024-01-15",status:"已处置",title:"[证据]当局正在对这件事情进行掩盖",duration:"-",views:"9.7万",confidence:83.2,city:"台北",findings:["账号矩阵","协同发布","买粉嫌疑","内容同质化"],scores:{deepfake:15,aiGen:58,political:83,spread:79,violence:4}},
];

const riskTrendData = [
  {time:"00:00",高危:40,中危:98},{time:"02:00",高危:29,中危:76},{time:"04:00",高危:21,中危:54},
  {time:"06:00",高危:33,中危:89},{time:"08:00",高危:66,中危:164},{time:"10:00",高危:100,中危:243},
  {time:"12:00",高危:125,中危:287},{time:"14:00",高危:115,中危:264},{time:"16:00",高危:137,中危:312},
  {time:"18:00",高危:160,中危:358},{time:"20:00",高危:145,中危:329},{time:"22:00",高危:110,中危:251},
];
const seed = (base: typeof riskTrendData, f: number) => base.map(d => ({...d, 高危: Math.round(d.高危*f), 中危: Math.round(d.中危*f)}));
const PLATFORMS_ORDERED = ["YouTube","Twitter/X","抖音","快手","微博","B站"];
const PLATFORM_TREND: Record<string, typeof riskTrendData> = {
  "全部": riskTrendData, "YouTube": seed(riskTrendData, 0.12), "Twitter/X": seed(riskTrendData, 0.09),
  "抖音": seed(riskTrendData, 0.38), "快手": seed(riskTrendData, 0.29), "微博": seed(riskTrendData, 0.18), "B站": seed(riskTrendData, 0.06),
};
const PLATFORM_STATS = [
  {name:"YouTube",risk:1247,color:"#10b981"},{name:"Twitter/X",risk:987,color:"#f59e0b"},
  {name:"抖音",risk:3847,color:"#3b8ef3"},{name:"快手",risk:2934,color:"#a855f7"},
  {name:"微博",risk:1823,color:"#06b6d4"},{name:"B站",risk:634,color:"#f97316"},
];
const contentPieData = [
  {name:"AI生成",value:31,color:"#a855f7"},{name:"虚假信息",value:24,color:"#ef4444"},
  {name:"违规内容",value:19,color:"#f97316"},{name:"境外渗透",value:14,color:"#f59e0b"},{name:"其他",value:12,color:"#64748b"},
];
const recentEvents = [
  {id:1,time:"14:32:18",platform:"YouTube",account:"@FreedomVoice2024",type:"AI生成内容",risk:"high" as RiskLevel,summary:"境外账号发布深度伪造政府官员讲话视频，AI合成声音，内容涉及重大政治敏感议题，已向全球大规模传播",fullSummary:"该账号 @FreedomVoice2024 于14:32在YouTube发布深度伪造视频，使用AI合成技术替换某官员面部及声音，散布虚假政治言论。视频时长3分42秒，发布后2小时内播放量突破23万次，已被多个境外媒体引用。经AI鉴伪系统检测，DeepFake置信度97.3%，建议立即上报处置并申请平台下架。"},
  {id:2,time:"14:31:54",platform:"Twitter/X",account:"@china_analyst_hk",type:"境外渗透",risk:"high" as RiskLevel,summary:"多账号矩阵协同传播境外势力炮制的虚假政治信息，情绪煽动性强，短期内形成热点",fullSummary:"账号 @china_analyst_hk 与关联矩阵账号（已确认3个）在Twitter/X协同转发境外势力炮制的虚假政治信息。内容声称某官员即将落马，附有伪造截图。2小时内矩阵转发超过1.8万次，评论区情绪对立明显，部分内容已渗透至境内社交平台。AI政治风险评分96.1%，建议立即启动溯源分析。"},
  {id:3,time:"14:28:41",platform:"YouTube",account:"@TruthSeeker99",type:"虚假信息",risk:"high" as RiskLevel,summary:"境外账号发布断章取义的经济数据解读视频，歪曲事实并配以煽动性标题，吸引境内用户",fullSummary:"@TruthSeeker99（伦敦）发布时长12分18秒的视频，将官方经济统计数据断章取义，配以煽动性标题声称数据造假。经文本语义分析，视频引用数据真实但解读方向存在严重偏差，AI内容生成评分78%，疑似部分使用AI辅助创作。播放量达8.3万次，需重点跟踪后续传播走向。"},
  {id:4,time:"14:27:03",platform:"抖音",account:"@tech_review_cn",type:"AI生成内容",risk:"high" as RiskLevel,summary:"国内账号发布AI生成的虚假专家采访视频，通过伪装权威来源传播未经证实的科技政策信息",fullSummary:"@tech_review_cn 发布AI生成的虚假专家采访视频，视频中的所谓专家经人脸比对无法匹配真实人物，为AI合成角色。视频内容涉及未经证实的重大科技政策信息，播放量已达45.6万次。AI内容生成评分94%，DeepFake评分91%。账号已在平台积累2.3M粉丝，传播影响力较大，建议优先处置。"},
  {id:5,time:"14:25:18",platform:"Twitter/X",account:"@asia_truth_net",type:"协同操控",risk:"high" as RiskLevel,summary:"台湾账号参与境外账号矩阵协同操控，批量发布内容同质化的政治攻击性帖子",fullSummary:"@asia_truth_net（台北）确认为境外账号矩阵成员之一，与至少5个账号保持高频率协同发布行为。内容主要围绕政治攻击性话题，帖子文案相似度超过85%，疑似由同一控制方统一生成分发。矩阵总传播量达9.7万次，已被标记为协同操控行为，建议批量上报相关平台。"},
  {id:6,time:"14:22:47",platform:"微博",account:"@breaking_news_hk",type:"违规内容",risk:"medium" as RiskLevel,summary:"账号发布未经核实的突发事件视频并诱导转发，内容情绪化表述明显，存在标题党和谣言传播风险",fullSummary:"@breaking_news_hk 发布声称为某地重大事故的现场视频，配以强烈情绪化描述，并在帖文末尾诱导用户转发扩散。经核查，视频实际为两年前他地事故画面，经过重新剪辑配文。转发量已达3.1万，评论中出现大量恐慌性内容。AI语义分析评分71%，建议联系平台添加辟谣标签并限制传播。"},
];

const BG_PAGE = "#f0f5ff";
const BG_CARD = "#ffffff";
const BORDER_CARD = "rgba(59,130,246,0.18)";
const riskColor = (r: string) => r==="high"?"#ef4444":r==="medium"?"#f59e0b":r==="low"?"#3b8ef3":"#10b981";


type AnyRecord = Record<string, any>;
const PLATFORM_CN: Record<string,string> = {douyin:"抖音",kuaishou:"快手",demo:"演示数据",youtube:"YouTube"};
const STATUS_CN: Record<string,string> = {
  success:"执行成功", pending:"等待执行", running:"执行中", failed:"执行失败",
  completed:"采集完成", stopped:"已停止", waiting_source:"等待直播源", skipped:"未启用",
  discovered:"已发现", audited:"已检测", captured:"已采集", comments_collected:"评论已采集",
  kept:"已确认", irrelevant:"已忽略", needs_review:"待确认", advertising:"营销内容",
  high:"高", medium:"中", low:"低", normal:"正常"
};
function apiHeaders(json=false): HeadersInit {
  const h: Record<string,string> = {};
  const key = localStorage.getItem("adminApiKey") || "";
  if (key) h["X-API-Key"] = key;
  if (json) h["Content-Type"] = "application/json";
  return h;
}
async function api<T=any>(path:string, options:RequestInit={}):Promise<T>{
  const response = await fetch(`/api${path}`, {...options, headers:{...apiHeaders(options.body!==undefined), ...(options.headers||{})}});
  if(!response.ok){
    let message=`请求失败（${response.status}）`;
    try{const d=await response.json();message=d.detail||d.message||message;}catch{/* ignore */}
    throw new Error(message);
  }
  return response.json();
}
async function apiText(path:string):Promise<string>{
  const response=await fetch(`/api${path}`,{headers:apiHeaders(false)});
  if(!response.ok) throw new Error(response.status===404?"文件不在当前服务器":`文件读取失败（${response.status}）`);
  return response.text();
}
function fmtDate(value?:string|null, withDate=true){
  if(!value)return "—"; const d=new Date(value); if(Number.isNaN(d.getTime()))return String(value);
  return new Intl.DateTimeFormat("zh-CN",{month:withDate?"2-digit":undefined,day:withDate?"2-digit":undefined,hour:"2-digit",minute:"2-digit",second:"2-digit",hour12:false}).format(d);
}
function fmtNum(v:any){return Number(v||0).toLocaleString("zh-CN");}
function platformCN(v?:string){return PLATFORM_CN[v||""]||v||"未知平台";}
function statusCN(v?:string){return STATUS_CN[v||""]||v||"—";}
function riskFrom(v?:string):RiskLevel{return v==="high"?"high":v==="medium"?"medium":v==="low"?"low":"safe";}
function evidenceUrl(id:number, download=false){return `/api/evidence/${id}/${download?"download":"view"}`;}

// ── Shared ──────────────────────────────────────────────────────────────────────
function GlassCard({children, className="", style={}}: {children: React.ReactNode; className?: string; style?: React.CSSProperties}) {
  return <div className={`rounded-xl border ${className}`} style={{background: BG_CARD, borderColor: BORDER_CARD, boxShadow:"0 1px 6px rgba(59,130,246,0.06)", ...style}}>{children}</div>;
}
function RiskBadge({level, size="sm"}: {level: RiskLevel; size?: "sm"|"md"}) {
  const m: Record<RiskLevel, {label: string; cls: string; dot: string}> = {
    high: {label:"高危", cls:"bg-red-50 text-red-600 border-red-200", dot:"bg-red-500 blink"},
    medium: {label:"中危", cls:"bg-yellow-50 text-yellow-600 border-yellow-200", dot:"bg-yellow-500"},
    low: {label:"低危", cls:"bg-blue-50 text-blue-600 border-blue-200", dot:"bg-blue-500"},
    safe: {label:"安全", cls:"bg-green-50 text-green-600 border-green-200", dot:"bg-green-500"},
  };
  const {label, cls, dot} = m[level];
  const px = size==="md" ? "px-3 py-1 text-xs" : "px-2 py-0.5 text-[10px]";
  return <span className={`inline-flex items-center gap-1 rounded border font-mono font-medium ${px} ${cls}`}>
    <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`}/>{label}
  </span>;
}
function MetricCard({label, value, sub, color="#3b8ef3", icon: Icon, trend}: {label:string; value:string; sub?:string; color?:string; icon:React.ElementType; trend?:"up"|"down"}) {
  return <div className="rounded-xl border p-4 flex flex-col gap-2 relative overflow-hidden bg-white"
    style={{borderColor: BORDER_CARD, boxShadow:"0 1px 6px rgba(59,130,246,0.06)"}}>
    <div className="absolute top-0 right-0 w-20 h-20 rounded-full" style={{background: color, filter:"blur(22px)", opacity:0.08, transform:"translate(30%,-30%)"}}/>
    <div className="flex items-center justify-between">
      <span className="text-[11px] text-slate-500 font-medium">{label}</span>
      <div className="p-1.5 rounded-lg" style={{background:`${color}15`}}><Icon size={13} style={{color}}/></div>
    </div>
    <div className="font-mono font-bold text-xl" style={{color}}>{value}</div>
    {sub && <div className="flex items-center gap-1 text-[10px]">
      {trend==="up" ? <TrendingUp size={9} className="text-red-500"/> : trend==="down" ? <TrendingDown size={9} className="text-green-500"/> : null}
      <span className="text-slate-500">{sub}</span>
    </div>}
  </div>;
}
function PlatformLogo({name}: {name: string}) {
  const colors: Record<string, string> = {抖音:"#000", 快手:"#FA6400", 微博:"#E6162D", YouTube:"#FF0000", "Twitter/X":"#1DA1F2", B站:"#00A1D6"};
  return <div className="w-7 h-7 rounded-md flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
    style={{background: colors[name]||"#3b8ef3"}}>{name==="Twitter/X"?"X":name.charAt(0)}</div>;
}
function ChartTip({active, payload, label}: any) {
  if (!active || !payload?.length) return null;
  return <div className="rounded-lg border px-3 py-2 text-xs" style={{background:"rgba(255,255,255,0.98)", borderColor:"rgba(59,130,246,0.25)", boxShadow:"0 4px 16px rgba(59,130,246,0.1)"}}>
    <div className="text-blue-600 font-medium mb-1">{label}</div>
    {payload.map((p: any, i: number) => <div key={i} className="flex items-center gap-2">
      <span className="w-2 h-2 rounded-sm" style={{background:p.color}}/>
      <span className="text-slate-500">{p.name}: </span>
      <span className="text-slate-800 font-mono">{typeof p.value==="number"?p.value.toLocaleString():p.value}</span>
    </div>)}
  </div>;
}
function Modal({open, onClose, title, children, width="max-w-lg"}: {open:boolean; onClose:()=>void; title:string; children:React.ReactNode; width?:string}) {
  if (!open) return null;
  return <div className="fixed inset-0 z-[100] flex items-center justify-center">
    <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" onClick={onClose}/>
    <div className={`relative z-10 rounded-2xl p-6 w-full ${width} mx-4 max-h-[90vh] overflow-auto bg-white`}
      style={{border:"1px solid rgba(59,130,246,0.2)", boxShadow:"0 20px 60px rgba(59,130,246,0.15)"}}>
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-base font-semibold text-slate-800">{title}</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-slate-700"><X size={16}/></button>
      </div>
      {children}
    </div>
  </div>;
}
function FormField({label, type="text", value, onChange, placeholder=""}: {label:string; type?:string; value:string; onChange:(v:string)=>void; placeholder?:string}) {
  return <div className="flex flex-col gap-1.5">
    <label className="text-xs text-slate-600">{label}</label>
    <input type={type} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}
      className="w-full px-3 py-2.5 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none"
      style={{background:"#f8faff", border:"1px solid rgba(59,130,246,0.2)"}}/>
  </div>;
}
function FormSelect({label, value, onChange, options}: {label:string; value:string; onChange:(v:string)=>void; options:{value:string;label:string}[]}) {
  return <div className="flex flex-col gap-1.5">
    <label className="text-xs text-slate-600">{label}</label>
    <select value={value} onChange={e=>onChange(e.target.value)} className="w-full px-3 py-2.5 rounded-lg text-sm text-slate-800 focus:outline-none"
      style={{background:"#f8faff", border:"1px solid rgba(59,130,246,0.2)"}}>
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>;
}
function BtnPrimary({children, onClick, className="", disabled=false}: {children:React.ReactNode; onClick?:()=>void; className?:string; disabled?:boolean}) {
  return <button onClick={onClick} disabled={disabled}
    className={`flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm text-white font-medium transition-all hover:opacity-90 active:scale-95 disabled:opacity-40 ${className}`}
    style={{background:"linear-gradient(135deg,#1d4ed8,#3b8ef3)"}}>{children}</button>;
}
function BtnSecondary({children, onClick, className=""}: {children:React.ReactNode; onClick?:()=>void; className?:string}) {
  return <button onClick={onClick}
    className={`flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg text-sm text-slate-600 font-medium transition-all hover:text-slate-800 hover:bg-slate-50 active:scale-95 ${className}`}
    style={{border:"1px solid rgba(59,130,246,0.2)"}}>{children}</button>;
}
function Toast({msg, type, onClose}: {msg:string; type:"success"|"error"|"info"; onClose:()=>void}) {
  useEffect(() => {const t = setTimeout(onClose, 3500); return () => clearTimeout(t);}, [onClose]);
  const c = {success:"#10b981", error:"#ef4444", info:"#3b8ef3"}[type];
  return <div className="fixed top-16 right-4 z-[200] flex items-center gap-3 px-4 py-3 rounded-xl text-sm text-slate-800 shadow-2xl max-w-sm bg-white"
    style={{border:`1px solid ${c}30`, boxShadow:`0 4px 20px ${c}18`}}>
    {type==="success"?<CheckCircle size={15} style={{color:c}}/>:type==="error"?<AlertCircle size={15} style={{color:c}}/>:<Info size={15} style={{color:c}}/>}
    <span className="flex-1">{msg}</span>
  </div>;
}

// ── World Map (react-simple-maps) ───────────────────────────────────────────────
const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-50m.json";

const COUNTRY_LABELS = [
  {name:"中国",coords:[104,35] as [number,number]},
  {name:"俄罗斯",coords:[98,62] as [number,number]},
  {name:"美国",coords:[-98,38] as [number,number]},
  {name:"加拿大",coords:[-96,60] as [number,number]},
  {name:"巴西",coords:[-52,-10] as [number,number]},
  {name:"澳大利亚",coords:[134,-25] as [number,number]},
  {name:"印度",coords:[80,22] as [number,number]},
  {name:"沙特阿拉伯",coords:[45,24] as [number,number]},
  {name:"法国",coords:[2,46] as [number,number]},
  {name:"德国",coords:[10,51] as [number,number]},
  {name:"英国",coords:[-2,54] as [number,number]},
  {name:"日本",coords:[138,37] as [number,number]},
  {name:"韩国",coords:[128,36] as [number,number]},
  {name:"印度尼西亚",coords:[117,-2] as [number,number]},
  {name:"南非",coords:[25,-29] as [number,number]},
  {name:"墨西哥",coords:[-102,24] as [number,number]},
  {name:"阿根廷",coords:[-65,-35] as [number,number]},
  {name:"伊朗",coords:[53,32] as [number,number]},
  {name:"土耳其",coords:[35,39] as [number,number]},
  {name:"埃及",coords:[30,26] as [number,number]},
  {name:"尼日利亚",coords:[8,10] as [number,number]},
  {name:"巴基斯坦",coords:[70,30] as [number,number]},
  {name:"哈萨克斯坦",coords:[67,48] as [number,number]},
  {name:"蒙古",coords:[105,46] as [number,number]},
  {name:"缅甸",coords:[96,19] as [number,number]},
  {name:"越南",coords:[106,16] as [number,number]},
  {name:"菲律宾",coords:[122,12] as [number,number]},
  {name:"泰国",coords:[101,15] as [number,number]},
  {name:"马来西亚",coords:[110,4] as [number,number]},
  {name:"太平洋",coords:[-160,0] as [number,number]},
  {name:"大西洋",coords:[-30,15] as [number,number]},
  {name:"印度洋",coords:[75,-25] as [number,number]},
];
const CITY_LABELS = [
  {name:"北京",coords:[116.4,39.9] as [number,number]},
  {name:"上海",coords:[121.5,31.2] as [number,number]},
  {name:"广州",coords:[113.3,23.1] as [number,number]},
  {name:"深圳",coords:[114.1,22.5] as [number,number]},
  {name:"成都",coords:[104.1,30.6] as [number,number]},
  {name:"杭州",coords:[120.2,30.3] as [number,number]},
  {name:"西安",coords:[108.9,34.3] as [number,number]},
  {name:"武汉",coords:[114.3,30.6] as [number,number]},
  {name:"天津",coords:[117.2,39.1] as [number,number]},
  {name:"重庆",coords:[106.5,29.6] as [number,number]},
  {name:"南京",coords:[118.8,32.1] as [number,number]},
  {name:"沈阳",coords:[123.4,41.8] as [number,number]},
  {name:"哈尔滨",coords:[126.5,45.8] as [number,number]},
  {name:"香港",coords:[114.2,22.3] as [number,number]},
  {name:"台北",coords:[121.6,25.0] as [number,number]},
  {name:"东京",coords:[139.7,35.7] as [number,number]},
  {name:"大阪",coords:[135.5,34.7] as [number,number]},
  {name:"首尔",coords:[127.0,37.6] as [number,number]},
  {name:"新加坡",coords:[103.8,1.3] as [number,number]},
  {name:"曼谷",coords:[100.5,13.8] as [number,number]},
  {name:"雅加达",coords:[106.8,-6.2] as [number,number]},
  {name:"吉隆坡",coords:[101.7,3.1] as [number,number]},
  {name:"河内",coords:[105.8,21.0] as [number,number]},
  {name:"莫斯科",coords:[37.6,55.8] as [number,number]},
  {name:"圣彼得堡",coords:[30.3,59.9] as [number,number]},
  {name:"伦敦",coords:[-0.1,51.5] as [number,number]},
  {name:"巴黎",coords:[2.3,48.9] as [number,number]},
  {name:"柏林",coords:[13.4,52.5] as [number,number]},
  {name:"阿姆斯特丹",coords:[4.9,52.4] as [number,number]},
  {name:"斯德哥尔摩",coords:[18.1,59.3] as [number,number]},
  {name:"华沙",coords:[21.0,52.2] as [number,number]},
  {name:"纽约",coords:[-74.0,40.7] as [number,number]},
  {name:"洛杉矶",coords:[-118.2,34.1] as [number,number]},
  {name:"旧金山",coords:[-122.4,37.8] as [number,number]},
  {name:"芝加哥",coords:[-87.6,41.9] as [number,number]},
  {name:"华盛顿",coords:[-77.0,38.9] as [number,number]},
  {name:"休斯顿",coords:[-95.4,29.8] as [number,number]},
  {name:"多伦多",coords:[-79.4,43.7] as [number,number]},
  {name:"温哥华",coords:[-123.1,49.3] as [number,number]},
  {name:"悉尼",coords:[151.2,-33.9] as [number,number]},
  {name:"墨尔本",coords:[145.0,-37.8] as [number,number]},
  {name:"开罗",coords:[31.2,30.1] as [number,number]},
  {name:"约翰内斯堡",coords:[28.0,-26.2] as [number,number]},
  {name:"迪拜",coords:[55.3,25.2] as [number,number]},
  {name:"德黑兰",coords:[51.4,35.7] as [number,number]},
  {name:"伊斯坦布尔",coords:[29.0,41.0] as [number,number]},
  {name:"卡拉奇",coords:[67.0,24.9] as [number,number]},
  {name:"孟买",coords:[72.9,19.1] as [number,number]},
  {name:"德里",coords:[77.2,28.6] as [number,number]},
  {name:"圣保罗",coords:[-46.6,-23.5] as [number,number]},
  {name:"布宜诺斯艾利斯",coords:[-58.4,-34.6] as [number,number]},
  {name:"墨西哥城",coords:[-99.1,19.4] as [number,number]},
  {name:"拉各斯",coords:[3.4,6.5] as [number,number]},
];

function MapFallback({locations, selId, onSelect}: {locations:typeof MAP_LOCATIONS; selId:number|null; onSelect:(id:number)=>void}) {
  const points = locations.length ? locations : [];
  return <div className="w-full h-full relative overflow-hidden select-none" style={{background:"linear-gradient(145deg,#dbeafe,#bfdbfe 46%,#dbeafe)"}}>
    <svg className="absolute inset-0 w-full h-full opacity-70" viewBox="0 0 1000 500" preserveAspectRatio="none">
      <defs><pattern id="map-grid-original" width="45" height="45" patternUnits="userSpaceOnUse"><path d="M45 0H0V45" fill="none" stroke="#60a5fa" strokeWidth="0.45"/></pattern></defs>
      <rect width="1000" height="500" fill="url(#map-grid-original)"/>
      <path d="M75,165 C160,82 250,76 330,124 C390,160 428,139 474,105 C565,37 666,60 724,115 C774,163 868,148 930,195 L912,332 C818,337 742,296 663,321 C563,354 490,306 405,334 C302,369 216,322 121,344 Z" fill="#bfdbfe" stroke="#7fb8ee" strokeWidth="2"/>
      <path d="M575,172 C630,143 702,151 738,188 C766,218 740,254 694,265 C638,277 582,251 557,216 Z" fill="#c7ddf3" stroke="#8dbce8" strokeWidth="1.5"/>
    </svg>
    {points.map((loc,i)=>{
      const left=10+((loc.lng+180)/360)*80; const top=12+((90-loc.lat)/180)*70; const selected=selId===loc.id;
      return <button key={loc.id} onClick={()=>onSelect(loc.id)} className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full transition-all" style={{left:`${left}%`,top:`${top}%`,width:selected?16:11,height:selected?16:11,background:riskColor(loc.risk),border:"2px solid white",boxShadow:`0 0 0 5px ${riskColor(loc.risk)}22`}} title={`${loc.name} · ${loc.city}`}/>;
    })}
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div className="px-5 py-3 rounded-xl text-center" style={{background:"rgba(255,255,255,.88)",border:`1px solid ${BORDER_CARD}`,boxShadow:"0 8px 25px rgba(30,64,175,.08)"}}>
        <Globe size={24} className="mx-auto text-blue-500 mb-2"/>
        <div className="text-sm font-medium text-slate-700">公开内容平台分布</div>
        <div className="text-[10px] text-slate-500 mt-1">平台接口未返回可靠地理位置时，不生成虚拟登录位置</div>
      </div>
    </div>
    <div className="absolute top-2 left-2 text-[9px] flex items-center gap-1.5" style={{background:"rgba(255,255,255,.9)",padding:"4px 8px",borderRadius:"6px"}}><span className="w-1.5 h-1.5 rounded-full bg-green-500 blink"/><span className="text-green-700">真实后端数据已接入</span></div>
  </div>;
}


// ── Login// ── Login ───────────────────────────────────────────────────────────────────────
function LoginPage({onLogin}: {onLogin:()=>void}) {
  const [user, setUser] = useState("");
  const [pass, setPass] = useState("");
  const [loading, setLoading] = useState(false);
  const [captcha, setCaptcha] = useState("AX7K");
  const [captchaIn, setCaptchaIn] = useState("");
  const doLogin = () => {if (!user || !pass) return; setLoading(true); setTimeout(() => {setLoading(false); onLogin();}, 1800);};
  return <div className="min-h-screen flex items-center justify-center relative overflow-hidden"
    style={{background:"radial-gradient(ellipse at 30% 50%,rgba(59,130,246,0.12),transparent 60%),radial-gradient(ellipse at 70% 80%,rgba(99,102,241,0.08),transparent 60%),#f0f5ff"}}>
    <svg className="absolute inset-0 w-full h-full opacity-20">
      <defs><pattern id="lg" width="60" height="60" patternUnits="userSpaceOnUse"><path d="M60 0L0 0 0 60" fill="none" stroke="#3b8ef3" strokeWidth="0.4"/></pattern></defs>
      <rect width="100%" height="100%" fill="url(#lg)"/>
    </svg>
    <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-8 py-4" style={{borderBottom:"1px solid rgba(59,130,246,0.1)", background:"rgba(255,255,255,0.85)", backdropFilter:"blur(8px)"}}>
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-lg" style={{background:"rgba(59,130,246,0.1)", border:"1px solid rgba(59,130,246,0.2)"}}><Shield size={20} className="text-blue-600"/></div>
        <div>
          <div className="text-sm font-bold text-blue-700" style={{fontFamily:"Rajdhani,sans-serif", letterSpacing:"0.05em"}}>HARMFUL CONTENT DETECTION PLATFORM</div>
          <div className="text-[10px] text-slate-500">网络直播内容有害监测平台 v3.2.1</div>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[11px] text-slate-500"><span className="w-1.5 h-1.5 rounded-full bg-green-500 blink"/>系统运行正常</div>
    </div>
    <div className="relative z-10 w-full max-w-md px-4">
      <div className="rounded-2xl overflow-hidden bg-white" style={{border:"1px solid rgba(59,130,246,0.2)", boxShadow:"0 20px 60px rgba(59,130,246,0.12)"}}>
        <div className="px-8 py-6 text-center" style={{borderBottom:"1px solid rgba(59,130,246,0.1)", background:"linear-gradient(135deg,#f0f5ff,#dbeafe)"}}>
          <div className="flex justify-center mb-4">
            <div className="relative float-anim">
              <div className="w-16 h-16 rounded-2xl flex items-center justify-center" style={{background:"linear-gradient(135deg,#1d4ed8,#3b8ef3)", boxShadow:"0 8px 24px rgba(59,130,246,0.35)"}}><Shield size={32} className="text-white"/></div>
              <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-green-500 border-2 border-white blink"/>
            </div>
          </div>
          <h1 className="text-xl font-bold text-slate-800 mb-1" style={{fontFamily:"Rajdhani,sans-serif", letterSpacing:"0.05em"}}>网络直播内容有害监测平台</h1>
          <p className="text-xs text-slate-500">AI驱动 · 全平台直播内容有害信息智能检测</p>
        </div>
        <div className="px-8 py-6 flex flex-col gap-4">
          <FormField label="用户名 / 工号" value={user} onChange={setUser} placeholder="admin"/>
          <FormField label="密码" type="password" value={pass} onChange={setPass} placeholder="••••••••"/>
          <div className="flex gap-3">
            <div className="flex-1"><FormField label="验证码" value={captchaIn} onChange={setCaptchaIn} placeholder="输入验证码"/></div>
            <div className="flex-shrink-0 mt-5"><div className="h-10 w-24 rounded-lg flex items-center justify-center cursor-pointer font-mono font-bold text-lg select-none"
              style={{background:"linear-gradient(135deg,#dbeafe,#bfdbfe)", border:"1px solid rgba(59,130,246,0.3)", color:"#1d4ed8", letterSpacing:"0.2em"}}
              onClick={() => setCaptcha(Math.random().toString(36).substring(2,6).toUpperCase())}>{captcha}</div></div>
          </div>
          <BtnPrimary onClick={doLogin} className="w-full py-3">
            {loading ? <><RefreshCw size={14} className="animate-spin"/>身份验证中...</> : "安全登录"}
          </BtnPrimary>
          <div className="text-center text-[10px] text-slate-400">本系统仅供授权人员使用 · 所有操作均留存日志</div>
        </div>
      </div>
    </div>
  </div>;
}

// ── Sidebar ─────────────────────────────────────────────────────────────────────
const navItems = [
  {id:"dashboard", icon:Monitor, label:"态势大屏", badge:null},
  {id:"accounts", icon:SlidersHorizontal, label:"监测配置", badge:null},
  {id:"live", icon:Activity, label:"直播监控", badge:null},
  {id:"alert", icon:AlertTriangle, label:"预警处置", badge:null},
  {id:"system", icon:Settings, label:"系统管理", badge:null},
];
function Sidebar({current, onChange, collapsed, onToggle}: {current:Page; onChange:(p:Page)=>void; collapsed:boolean; onToggle:()=>void}) {
  return <div className="flex flex-col h-full transition-all duration-300" style={{width:collapsed?"60px":"220px", background:"#1e40af", borderRight:"1px solid rgba(255,255,255,0.08)"}}>
    <div className="flex items-center gap-3 px-3 py-4" style={{borderBottom:"1px solid rgba(255,255,255,0.1)"}}>
      <div className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center" style={{background:"rgba(255,255,255,0.2)", border:"1px solid rgba(255,255,255,0.3)"}}><Shield size={16} className="text-white"/></div>
      {!collapsed && <div><div className="text-xs font-bold text-white whitespace-nowrap" style={{fontFamily:"Rajdhani,sans-serif", letterSpacing:"0.06em"}}>AI SAFETY</div><div className="text-[9px] text-blue-200 whitespace-nowrap">网络直播内容有害监测平台</div></div>}
    </div>
    <nav className="flex-1 py-3 px-2 flex flex-col gap-0.5">
      {navItems.map(item => {
        const active = current === item.id;
        return <button key={item.id} onClick={() => onChange(item.id as Page)}
          className={`w-full flex items-center gap-3 px-2.5 py-2.5 rounded-lg text-left transition-all text-xs font-medium group ${active?"text-white":"text-blue-100 hover:text-white"}`}
          style={{background:active?"rgba(255,255,255,0.18)":"transparent", borderLeft:active?"2px solid rgba(255,255,255,0.8)":"2px solid transparent"}}>
          <item.icon size={15} className={active?"text-white":"text-blue-200 group-hover:text-white"}/>
          {!collapsed && <><span className="flex-1 whitespace-nowrap">{item.label}</span>
            {item.badge && <span className="text-[9px] px-1.5 py-0.5 rounded font-mono" style={{background:item.badge==="新"?"rgba(168,85,247,0.5)":"rgba(255,255,255,0.2)", color:"#ffffff"}}>{item.badge}</span>}
          </>}
        </button>;
      })}
    </nav>
    <div className="px-2 py-3" style={{borderTop:"1px solid rgba(255,255,255,0.1)"}}>
      {!collapsed && <div className="flex items-center gap-2 px-2 py-2 mb-1">
        <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold text-white">管</div>
        <div><div className="text-xs text-white whitespace-nowrap">张明远 / 管理员</div><div className="text-[9px] text-blue-200 whitespace-nowrap">admin@aisp.gov.cn</div></div>
      </div>}
      <button onClick={onToggle} className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-blue-200 hover:text-white text-xs">
        {collapsed ? <ChevronRight size={14}/> : <ChevronLeft size={14}/>}{!collapsed && "收起侧栏"}
      </button>
    </div>
  </div>;
}

// ── TopBar ──────────────────────────────────────────────────────────────────────
function TopBar({title, onLogout}: {title:string; onLogout:()=>void}) {
  const [t, setT] = useState(new Date());
  useEffect(() => {const id = setInterval(() => setT(new Date()), 1000); return () => clearInterval(id);}, []);
  return <div className="flex items-center justify-between px-5 py-2.5 flex-shrink-0 bg-white"
    style={{borderBottom:"1px solid rgba(59,130,246,0.12)", boxShadow:"0 1px 4px rgba(59,130,246,0.06)"}}>
    <div className="text-sm font-medium text-slate-800">{title}</div>
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-1.5 text-[11px] text-green-600"><span className="w-1.5 h-1.5 rounded-full bg-green-500 blink"/>系统正常</div>
      <div className="text-[11px] font-mono text-slate-500">{t.toLocaleString("zh-CN", {hour12:false})}</div>
      <button className="relative p-1.5 rounded-lg text-slate-500 hover:text-slate-800" style={{background:"rgba(0,0,0,0.04)"}}><Bell size={14}/><span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-red-500 blink"/></button>
      <button onClick={onLogout} className="flex items-center gap-1.5 text-[11px] text-slate-500 hover:text-red-500"><LogOut size={13}/>退出</button>
    </div>
  </div>;
}

// ── Dashboard ───────────────────────────────────────────────────────────────────
function DashboardPage() {
  const [overview,setOverview]=useState<AnyRecord|null>(null);
  const [contents,setContents]=useState<AnyRecord[]>([]);
  const [sessions,setSessions]=useState<AnyRecord[]>([]);
  const [jobs,setJobs]=useState<AnyRecord[]>([]);
  const [selPlatform,setSelPlatform]=useState("全部");
  const [loading,setLoading]=useState(true);
  const load=useCallback(async()=>{
    setLoading(true);
    try{
      const [o,c,s,j]=await Promise.all([api("/console/overview"),api("/contents?limit=30"),api("/live-sessions"),api("/jobs?limit=200")]);
      setOverview(o);setContents(c);setSessions(s);setJobs(j);
    }catch(e){console.error(e);}finally{setLoading(false);}
  },[]);
  useEffect(()=>{load();const id=setInterval(load,20000);return()=>clearInterval(id);},[load]);
  const metrics=overview?.metrics||{};
  const evidenceTotal=contents.reduce((n,x)=>n+Number(x.evidence_count||0),0);
  const auditTotal=contents.reduce((n,x)=>n+Number(x.audit_count||0),0);
  const needsReview=contents.filter(x=>x.filter_status==="needs_review").length;
  const failedJobs=jobs.filter(x=>x.status==="failed").length;
  const activeSessions=sessions.filter(x=>!["completed","stopped","failed"].includes(x.status)).length;
  const platforms=["全部",...Array.from(new Set(contents.map(x=>platformCN(x.platform))))];
  const filtered=selPlatform==="全部"?contents:contents.filter(x=>platformCN(x.platform)===selPlatform);
  const trend=(overview?.hourly_alerts||[]).map((x:AnyRecord)=>({time:x.label,高危:x.high||0,中危:x.discovered||0}));
  const riskAccounts=overview?.risk_accounts||[];
  const platformCounts=contents.reduce((acc:Record<string,number>,x)=>{const p=platformCN(x.platform);acc[p]=(acc[p]||0)+1;return acc;},{});
  return <div className="flex flex-col h-full overflow-hidden gap-3 p-3" style={{background:BG_PAGE}}>
    <div className="grid grid-cols-6 gap-3 flex-shrink-0">
      {[
        {label:"监测内容",value:fmtNum(metrics.total_contents||contents.length),icon:Search,color:"#3b8ef3",sub:"真实数据库累计"},
        {label:"直播会话",value:fmtNum(sessions.length),icon:Activity,color:"#a855f7",sub:`运行中 ${activeSessions}`},
        {label:"证据文件",value:fmtNum(evidenceTotal),icon:Database,color:"#06b6d4",sub:"视频/音频/文本/元数据"},
        {label:"检测结果",value:fmtNum(auditTotal),icon:Cpu,color:"#10b981",sub:"模型运行记录"},
        {label:"待人工确认",value:fmtNum(needsReview),icon:AlertTriangle,color:"#f97316",sub:"内容详情内处理"},
        {label:"后台失败任务",value:fmtNum(failedJobs),icon:AlertCircle,color:"#ef4444",sub:`队列共 ${jobs.length} 条`},
      ].map(m=><MetricCard key={m.label}{...m}/>) }
    </div>
    <div className="flex gap-3 flex-1 min-h-0">
      <div style={{width:"58%",borderColor:BORDER_CARD}} className="rounded-xl border overflow-hidden flex flex-col bg-white shadow-sm">
        <div className="flex items-center justify-between px-3 py-2 flex-shrink-0" style={{borderBottom:`1px solid ${BORDER_CARD}`}}>
          <span className="text-xs font-medium text-slate-700 flex items-center gap-1.5"><Globe size={12} className="text-blue-500"/>平台与公开内容分布</span>
          <span className="text-[10px] text-slate-400">地理位置仅在平台提供可靠字段后展示</span>
        </div>
        <div className="relative flex-1 min-h-0"><MapFallback locations={[]} selId={null} onSelect={()=>{}}/>
          <div className="absolute bottom-4 left-4 right-4 grid grid-cols-3 gap-2">
            {Object.entries(platformCounts).slice(0,6).map(([p,n])=><div key={p} className="rounded-lg bg-white/90 border border-blue-100 px-3 py-2"><div className="text-[10px] text-slate-500">{p}</div><div className="font-mono text-lg font-bold text-blue-600">{n}</div></div>)}
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-2 flex-1 min-w-0 overflow-hidden">
        <GlassCard className="flex-shrink-0 p-1 flex gap-0.5 flex-wrap">{platforms.map(p=><button key={p} onClick={()=>setSelPlatform(p)} className={`px-2.5 py-1.5 rounded-lg text-[11px] font-medium ${selPlatform===p?"text-white":"text-slate-500"}`} style={{background:selPlatform===p?"rgba(59,130,246,.8)":"transparent"}}>{p}</button>)}</GlassCard>
        <GlassCard className="p-3 flex-shrink-0" style={{height:"150px"}}>
          <div className="text-[11px] font-medium text-slate-700 mb-1.5 flex items-center justify-between"><span className="flex items-center gap-1.5"><BarChart2 size={11} className="text-blue-500"/>24小时任务与内容趋势</span><button onClick={load} className="text-[10px] text-blue-500 flex items-center gap-1"><RefreshCw size={10} className={loading?"animate-spin":""}/>刷新</button></div>
          <ResponsiveContainer width="100%" height={105}><AreaChart data={trend.length?trend:riskTrendData.slice(-8)} margin={{top:4,right:4,left:-28,bottom:0}}><CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,.06)"/><XAxis dataKey="time" tick={{fill:"#94a3b8",fontSize:8}}/><YAxis tick={{fill:"#94a3b8",fontSize:8}}/><Tooltip content={<ChartTip/>}/><Area type="monotone" dataKey="中危" stroke="#3b82f6" fill="#3b82f6" fillOpacity={.12}/><Area type="monotone" dataKey="高危" stroke="#ef4444" fill="#ef4444" fillOpacity={.18}/></AreaChart></ResponsiveContainer>
        </GlassCard>
        <div className="grid grid-cols-4 gap-2 flex-shrink-0">{[
          {label:"今日线索",value:metrics.today_alerts||0,color:"#ef4444"},{label:"互动数据",value:metrics.total_interactions||0,color:"#10b981"},{label:"高关注账号",value:metrics.high_accounts||0,color:"#a855f7"},{label:"任务等待",value:metrics.pending_actions||0,color:"#f59e0b"}
        ].map(x=><GlassCard key={x.label} className="p-2.5 text-center"><div className="text-lg font-mono font-bold" style={{color:x.color}}>{fmtNum(x.value)}</div><div className="text-[9px] text-slate-500">{x.label}</div></GlassCard>)}</div>
        <GlassCard className="flex-1 min-h-0 overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-3 py-2" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><span className="text-[11px] font-medium text-slate-700 flex items-center gap-1.5"><AlertTriangle size={11} className="text-orange-500"/>最新监测内容</span><span className="text-[9px] text-slate-400">{filtered.length} 条</span></div>
          <div className="overflow-auto flex-1">{filtered.slice(0,8).map(item=><div key={item.id} className="px-3 py-2 hover:bg-blue-50/40" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><div className="flex items-center gap-2"><RiskBadge level={riskFrom(item.risk_status)}/><span className="text-[11px] text-slate-700 truncate flex-1">{item.title}</span><span className="text-[9px] text-slate-400">{fmtDate(item.last_seen_at,false)}</span></div><div className="text-[9px] text-slate-400 mt-1">{platformCN(item.platform)} · {item.author_alias||"公开账号"} · 证据 {item.evidence_count||0}</div></div>)}{!filtered.length&&<div className="h-full flex items-center justify-center text-xs text-slate-400">暂无监测内容</div>}</div>
        </GlassCard>
      </div>
    </div>
  </div>;
}

// ── Report Editor// ── Report Editor ───────────────────────────────────────────────────────────────
function ReportEditor({alertData, onBack, showToast}: {alertData:typeof ALERT_DATA[0]; onBack:()=>void; showToast:(m:string,t:"success"|"error"|"info")=>void}) {
  const editorRef = useRef<HTMLDivElement>(null);
  const [fontSize, setFontSize] = useState("14");
  const exec = (cmd: string, val?: string) => document.execCommand(cmd, false, val);
  const initial = `<h2 style="text-align:center;font-size:18px;font-weight:bold;margin-bottom:24px">有害内容分析处置报告</h2><p style="text-align:right;color:#64748b;font-size:12px">报告编号：RPT-${Date.now().toString().slice(-8)}　　生成时间：${alertData.date} ${alertData.time}</p><hr style="border:none;border-top:2px solid #1d4ed8;margin:16px 0"/><h3 style="font-size:15px;font-weight:bold;color:#1d4ed8;margin:16px 0 8px">一、基本情况</h3><p>发现账号 <strong>${alertData.account}</strong>（${alertData.platform}，粉丝数 ${alertData.fans}）于 ${alertData.date} ${alertData.time} 发布疑似违规内容，内容标题为：《${alertData.title}》。内容类型为 <strong>${alertData.type}</strong>，AI系统综合置信度评分 <strong>${alertData.confidence}%</strong>，属于<strong>${alertData.risk==="high"?"高风险":"中等风险"}</strong>级别。</p><h3 style="font-size:15px;font-weight:bold;color:#1d4ed8;margin:16px 0 8px">二、主要发现</h3><ul>${alertData.findings.map(f=>`<li>${f}</li>`).join("")}</ul><h3 style="font-size:15px;font-weight:bold;color:#1d4ed8;margin:16px 0 8px">三、AI风险评分详情</h3><p>DeepFake检测：${alertData.scores.deepfake}%　AI生成识别：${alertData.scores.aiGen}%　政治风险：${alertData.scores.political}%　传播风险：${alertData.scores.spread}%</p><h3 style="font-size:15px;font-weight:bold;color:#1d4ed8;margin:16px 0 8px">四、处置建议</h3><p>建议立即对该账号实施重点监控，向${alertData.platform}平台提交内容下架申请，同时对关联账号矩阵进行溯源排查，防止内容进一步扩散。</p><br/><p>审核人：___________　　日期：___________</p>`;
  const handleDownload = () => {
    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>分析报告</title><style>body{font-family:"SimSun",serif;max-width:800px;margin:0 auto;padding:60px;font-size:14px;line-height:1.9;color:#111}</style></head><body>${editorRef.current?.innerHTML||""}</body></html>`;
    const blob = new Blob([html], {type:"text/html"});
    const a = document.createElement("a"); a.href=URL.createObjectURL(blob);
    a.download=`安全分析报告_${alertData.account}_${alertData.date}.html`; a.click();
    showToast("报告已导出", "success");
  };

  return <div className="flex flex-col h-full overflow-hidden" style={{background:"#f3f4f6"}}>
    <div className="flex items-center gap-3 px-4 py-2 flex-shrink-0 bg-white" style={{borderBottom:"1px solid #e2e8f0", boxShadow:"0 1px 3px rgba(0,0,0,0.06)"}}>
      <button onClick={onBack} className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded hover:bg-slate-100">
        <ChevronLeft size={13}/>返回预警处置
      </button>
      <div style={{width:"1px", height:"20px", background:"#e2e8f0"}}/>
      <div className="flex items-center gap-1">
        {[{cmd:"bold",icon:"B",style:"font-bold"},{cmd:"italic",icon:"I",style:"italic"},{cmd:"underline",icon:"U",style:"underline"}].map(b=>(
          <button key={b.cmd} onMouseDown={e=>{e.preventDefault();exec(b.cmd);}}
            className={`w-7 h-7 text-xs rounded hover:bg-slate-100 text-slate-700 ${b.style}`}>{b.icon}</button>
        ))}
      </div>
      <div style={{width:"1px", height:"20px", background:"#e2e8f0"}}/>
      <div className="flex items-center gap-1">
        {["h1","h2","h3"].map((h,i)=>(
          <button key={h} onMouseDown={e=>{e.preventDefault();exec("formatBlock",h);}}
            className="px-2 h-7 text-xs rounded hover:bg-slate-100 text-slate-700 font-bold"
            style={{fontSize:`${14-i*2}px`}}>H{i+1}</button>
        ))}
        <button onMouseDown={e=>{e.preventDefault();exec("formatBlock","p");}}
          className="px-2 h-7 text-xs rounded hover:bg-slate-100 text-slate-700">正文</button>
      </div>
      <div style={{width:"1px", height:"20px", background:"#e2e8f0"}}/>
      <div className="flex items-center gap-1">
        {["justifyLeft","justifyCenter","justifyRight"].map((cmd,i)=>(
          <button key={cmd} onMouseDown={e=>{e.preventDefault();exec(cmd);}}
            className="w-7 h-7 text-xs rounded hover:bg-slate-100 text-slate-700 flex items-center justify-center">
            {i===0?"≡":i===1?"≡":i===2?"≡":""}
          </button>
        ))}
        <button onMouseDown={e=>{e.preventDefault();exec("insertUnorderedList");}}
          className="w-7 h-7 text-xs rounded hover:bg-slate-100 text-slate-700 flex items-center justify-center">•</button>
        <button onMouseDown={e=>{e.preventDefault();exec("insertOrderedList");}}
          className="w-7 h-7 text-xs rounded hover:bg-slate-100 text-slate-700 flex items-center justify-center">1.</button>
      </div>
      <div style={{width:"1px", height:"20px", background:"#e2e8f0"}}/>
      <div className="flex items-center gap-1">
        <select value={fontSize} onChange={e=>{setFontSize(e.target.value);exec("fontSize","3");}}
          className="h-7 px-1 text-xs rounded border border-slate-200 bg-white text-slate-700">
          {["10","12","14","16","18","20","24"].map(s=><option key={s} value={s}>{s}pt</option>)}
        </select>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <button onClick={()=>{showToast("已保存到系统","success");}} className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg text-slate-600 hover:bg-slate-100">
          <Save size={12}/>保存
        </button>
        <button onClick={()=>window.print()} className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg text-slate-600 hover:bg-slate-100">
          <Copy size={12}/>打印
        </button>
        <BtnPrimary onClick={handleDownload} className="py-1.5 text-xs"><Download size={12}/>导出HTML</BtnPrimary>
      </div>
    </div>
    <div className="flex-1 overflow-auto py-8 px-4 bg-slate-100">
      <div style={{width:"794px", margin:"0 auto", background:"#fff", minHeight:"1000px", padding:"72px 96px",
        boxShadow:"0 4px 20px rgba(0,0,0,0.1)"}}>
        <div ref={editorRef} contentEditable suppressContentEditableWarning
          dangerouslySetInnerHTML={{__html:initial}}
          style={{outline:"none", fontFamily:"'SimSun','宋体',Georgia,serif", fontSize:"14px", lineHeight:"1.9", color:"#111", minHeight:"880px"}}/>
      </div>
    </div>
  </div>;
}

// ── Alert Page ──────────────────────────────────────────────────────────────────
function AlertPage({showToast}: {showToast:(m:string, t:"success"|"error"|"info")=>void}) {
  const [contents,setContents]=useState<AnyRecord[]>([]);
  const [selected,setSelected]=useState<number|null>(null);
  const [detail,setDetail]=useState<AnyRecord|null>(null);
  const [filter,setFilter]=useState("all");
  const [query,setQuery]=useState("");
  const [loading,setLoading]=useState(false);
  const load=useCallback(async()=>{try{const c=await api<AnyRecord[]>("/contents?limit=300");setContents(c);if(!selected&&c.length)setSelected(c[0].id);}catch(e:any){showToast(e.message,"error")}},[selected,showToast]);
  useEffect(()=>{load()},[load]);
  useEffect(()=>{if(!selected){setDetail(null);return;}setLoading(true);api(`/contents/${selected}`).then(setDetail).catch((e:any)=>showToast(e.message,"error")).finally(()=>setLoading(false));},[selected,showToast]);
  const rows=contents.filter(x=>(filter==="all"||x.filter_status===filter||x.risk_status===filter)&&(!query||`${x.title} ${x.description} ${x.author_alias}`.includes(query)));
  const current=detail?.content;
  async function review(status:string){if(!selected)return;try{await api(`/contents/${selected}/review?status=${status}`,{method:"POST"});showToast("人工确认状态已更新","success");await load();setDetail(await api(`/contents/${selected}`));}catch(e:any){showToast(e.message,"error")}}
  async function action(path:string,msg:string){if(!selected)return;try{await api(`/contents/${selected}/${path}`,{method:"POST"});showToast(msg,"success");setDetail(await api(`/contents/${selected}`));await load();}catch(e:any){showToast(e.message,"error")}}
  function exportReport(){if(!current)return;const html=`<!doctype html><meta charset="utf-8"><title>${current.title}</title><h1>内容分析记录</h1><p>平台：${platformCN(current.platform)}</p><p>标题：${current.title}</p><p>账号：${current.author_alias||"—"}</p><p>人工状态：${statusCN(current.filter_status)}</p><p>检测状态：${statusCN(current.risk_status)}</p><h2>描述</h2><p>${current.description||"—"}</p><h2>关键词</h2><p>${(current.matched_keywords||[]).join("、")||"—"}</p><h2>证据</h2><p>${(detail.evidence||[]).length} 个文件</p>`;const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([html],{type:"text/html;charset=utf-8"}));a.download=`内容分析_${current.id}.html`;a.click();URL.revokeObjectURL(a.href);}
  return <div className="p-3 h-full overflow-hidden flex flex-col gap-3" style={{background:BG_PAGE}}>
    <div className="grid grid-cols-4 gap-3 flex-shrink-0">{[
      {label:"待确认",value:contents.filter(x=>x.filter_status==="needs_review").length,color:"#ef4444"},{label:"已确认",value:contents.filter(x=>x.filter_status==="kept").length,color:"#10b981"},{label:"已忽略",value:contents.filter(x=>x.filter_status==="irrelevant").length,color:"#64748b"},{label:"检测记录",value:contents.reduce((n,x)=>n+Number(x.audit_count||0),0),color:"#3b82f6"}
    ].map(x=><GlassCard key={x.label} className="p-3"><div className="text-[10px] text-slate-500">{x.label}</div><div className="text-xl font-bold font-mono" style={{color:x.color}}>{fmtNum(x.value)}</div></GlassCard>)}</div>
    <div className="flex gap-3 flex-1 min-h-0">
      <GlassCard className="w-[360px] flex-shrink-0 flex flex-col overflow-hidden">
        <div className="p-3 flex flex-col gap-2" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><div className="flex items-center justify-between"><span className="text-xs font-medium text-slate-700">内容事件</span><button onClick={load} className="text-blue-500"><RefreshCw size={12}/></button></div><div className="flex gap-1"><select value={filter} onChange={e=>setFilter(e.target.value)} className="text-[10px] px-2 py-1.5 rounded-lg border border-blue-100 bg-white"><option value="all">全部</option><option value="needs_review">待确认</option><option value="kept">已确认</option><option value="irrelevant">已忽略</option><option value="high">高风险标签</option></select><div className="relative flex-1"><Search size={11} className="absolute left-2 top-2 text-slate-400"/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="搜索内容" className="w-full pl-7 pr-2 py-1.5 text-[10px] rounded-lg border border-blue-100"/></div></div></div>
        <div className="overflow-auto flex-1">{rows.map(x=><button key={x.id} onClick={()=>setSelected(x.id)} className="w-full text-left p-3 hover:bg-blue-50/50" style={{background:selected===x.id?"rgba(59,130,246,.08)":"transparent",borderBottom:`1px solid ${BORDER_CARD}`}}><div className="flex items-center gap-2"><PlatformLogo name={platformCN(x.platform)}/><span className="text-[11px] font-medium text-slate-700 truncate flex-1">{x.title}</span><RiskBadge level={riskFrom(x.risk_status)}/></div><div className="text-[9px] text-slate-400 mt-1">{x.author_alias||"公开账号"} · {fmtDate(x.last_seen_at)}</div><div className="flex gap-1 mt-1.5 flex-wrap">{(x.matched_keywords||[]).slice(0,3).map((k:string)=><span key={k} className="text-[9px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600">{k}</span>)}</div></button>)}{!rows.length&&<div className="p-8 text-center text-xs text-slate-400">暂无匹配内容</div>}</div>
      </GlassCard>
      <div className="flex-1 min-w-0 overflow-auto flex flex-col gap-3">
        {!current?<GlassCard className="h-full flex items-center justify-center text-slate-400">选择左侧内容查看真实检测与证据</GlassCard>:<>
          <GlassCard className="p-4"><div className="flex items-start gap-3"><div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center"><Video size={20} className="text-blue-500"/></div><div className="flex-1 min-w-0"><div className="flex items-center gap-2"><span className="text-sm font-semibold text-slate-800">{current.title}</span>{current.platform==="demo"&&<span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600">演示数据</span>}</div><div className="text-[10px] text-slate-500 mt-1">{platformCN(current.platform)} · {current.author_alias||"公开账号"} · {fmtDate(current.last_seen_at)}</div><div className="text-xs text-slate-600 mt-2 leading-relaxed">{current.description||"暂无描述"}</div></div><div className="flex flex-col items-end gap-2"><RiskBadge level={riskFrom(current.risk_status)} size="md"/><span className="text-[10px] text-slate-500">{statusCN(current.filter_status)}</span></div></div></GlassCard>
          <div className="grid grid-cols-2 gap-3">
            <GlassCard className="p-4"><div className="text-xs font-medium text-slate-700 mb-3 flex items-center gap-1.5"><Cpu size={12} className="text-purple-500"/>检测结果</div>{loading?<div className="text-xs text-slate-400">加载中...</div>:(detail.audits||[]).length?(detail.audits||[]).slice(0,8).map((a:AnyRecord)=><div key={a.id} className="p-2.5 rounded-lg bg-slate-50 mb-2"><div className="flex items-center justify-between"><span className="text-[11px] text-slate-700">{a.model_name||a.audit_type||"文本检测"}</span><span className="text-[10px] text-blue-600">{a.confidence!=null?`${Math.round(Number(a.confidence)*100)}%`:statusCN(a.status)}</span></div><div className="text-[10px] text-slate-500 mt-1">标签：{(a.labels||[]).join("、")||"无"}</div><div className="text-[9px] text-slate-400 mt-1">版本 {a.model_version||"—"} · {fmtDate(a.created_at)}</div></div>):<div className="text-xs text-slate-400">暂无检测记录，可点击“重新检测”</div>}</GlassCard>
            <GlassCard className="p-4"><div className="text-xs font-medium text-slate-700 mb-3 flex items-center gap-1.5"><Database size={12} className="text-cyan-500"/>证据与评论</div><div className="grid grid-cols-3 gap-2 mb-3">{[{k:"证据",v:(detail.evidence||[]).length},{k:"评论",v:(detail.comments||[]).length},{k:"线索",v:(detail.leads||[]).length}].map(x=><div key={x.k} className="bg-slate-50 rounded-lg p-2 text-center"><div className="font-mono text-lg text-blue-600">{x.v}</div><div className="text-[9px] text-slate-500">{x.k}</div></div>)}</div><div className="max-h-36 overflow-auto">{(detail.evidence||[]).slice(0,10).map((e:AnyRecord)=><a key={e.id} href={evidenceUrl(e.id)} target="_blank" rel="noreferrer" className="flex items-center justify-between text-[10px] px-2 py-1.5 rounded hover:bg-blue-50"><span>{statusCN(e.file_type)||e.file_type} · {e.path?.split(/[\\/]/).pop()||`证据${e.id}`}</span><Eye size={10} className="text-blue-500"/></a>)}</div></GlassCard>
          </div>
          <GlassCard className="p-3"><div className="flex flex-wrap gap-2"><BtnPrimary onClick={()=>review("kept")}><CheckCircle size={12}/>确认保留</BtnPrimary><BtnSecondary onClick={()=>review("needs_review")}><Clock size={12}/>标记待确认</BtnSecondary><BtnSecondary onClick={()=>review("irrelevant")}><X size={12}/>忽略</BtnSecondary><BtnSecondary onClick={()=>action("audit","检测任务已提交")}><Cpu size={12}/>重新检测</BtnSecondary><BtnSecondary onClick={()=>action("comments/fetch","评论采集任务已提交")}><MessageSquare size={12}/>采集评论</BtnSecondary><BtnSecondary onClick={()=>action("relations/fetch","公开关系采集任务已提交")}><Link2 size={12}/>采集线索</BtnSecondary><BtnSecondary onClick={()=>action("expand","关联内容扩展任务已提交")}><Search size={12}/>扩展内容</BtnSecondary><BtnSecondary onClick={exportReport}><FileBarChart size={12}/>导出分析记录</BtnSecondary></div></GlassCard>
        </>}
      </div>
    </div>
  </div>;
}

// ── Accounts// ── Accounts ────────────────────────────────────────────────────────────────────
interface Keyword { id:number; platforms:string[]; keyword:string; status:string; matchCount:number; }

const INIT_KEYWORDS: Keyword[] = [
  {id:1,platforms:["YouTube","Twitter/X"],keyword:"CCP collapse",status:"启用",matchCount:7823},
  {id:2,platforms:["Twitter/X"],keyword:"revolution China",status:"启用",matchCount:5421},
  {id:3,platforms:["YouTube","Twitter/X","抖音"],keyword:"境外势力",status:"启用",matchCount:4247},
  {id:4,platforms:["YouTube"],keyword:"leaked document",status:"启用",matchCount:1893},
  {id:5,platforms:["Twitter/X"],keyword:"suppress freedom",status:"启用",matchCount:2341},
  {id:6,platforms:["快手","微博"],keyword:"封锁消息",status:"启用",matchCount:567},
  {id:7,platforms:["微博"],keyword:"颠覆政权",status:"启用",matchCount:89},
  {id:8,platforms:["抖音"],keyword:"内幕曝光",status:"启用",matchCount:834},
  {id:9,platforms:["微博"],keyword:"实名举报",status:"暂停",matchCount:234},
  {id:10,platforms:["抖音","快手"],keyword:"真相只有一个",status:"启用",matchCount:2341},
  {id:11,platforms:["快手"],keyword:"求扩散",status:"启用",matchCount:4823},
  {id:12,platforms:["B站"],keyword:"AI换脸教程",status:"启用",matchCount:1124},
];

function MonitoringConfigPage({accounts, setAccounts, showToast}: {accounts:Account[]; setAccounts:(a:Account[])=>void; showToast:(m:string,t:"success"|"error"|"info")=>void}) {
  const [tab,setTab]=useState<"accounts"|"keywords">("accounts");
  const [health,setHealth]=useState<AnyRecord|null>(null);
  const [tasks,setTasks]=useState<AnyRecord[]>([]);
  const [showLive,setShowLive]=useState(false);
  const [showTask,setShowTask]=useState(false);
  const [showYoutube,setShowYoutube]=useState(false);
  const [youtubeForm,setYoutubeForm]=useState({url:"",maxVideos:"3",maxComments:"100",maxHeight:"720",downloadVideo:true,autoTranscribe:true,autoAudit:true,auditMedia:true,monitorEnabled:false,intervalSeconds:"1800"});
  const [liveForm,setLiveForm]=useState({platform:"douyin",room:"",title:"",segment:"120",keywords:"",notes:""});
  const [taskForm,setTaskForm]=useState({name:"",platform:"demo",keywords:"",exclude:"",region:"",video:true,live:true,comments:true,audit:true,expand:true,capture:false,push:false});
  const load=useCallback(async()=>{try{const [h,t,y]=await Promise.all([api("/health"),api("/tasks"),api("/youtube/health")]);setHealth({...h,youtube:y});setTasks(t);}catch(e:any){showToast(e.message,"error")}},[showToast]);
  useEffect(()=>{load()},[load]);
  const connectors=[
    {id:"douyin",name:"抖音",state:health?.platforms?.douyin,desc:"短视频搜索、评论、媒体解析与公开关系"},
    {id:"kuaishou",name:"快手",state:health?.platforms?.kuaishou,desc:"短视频搜索、评论、媒体解析与公开关系"},
    {id:"youtube",name:"YouTube",state:health?.youtube,desc:"频道/视频采集、评论、字幕、ASR与内容检测"},
    {id:"live",name:"直播采集桥接",state:{configured:health?.live_monitor_bridge?.configured,enabled:health?.live_monitor_bridge?.configured,base_url:health?.live_monitor_bridge?.base_url},desc:"直播ID解析、视频分片、音频提取与ASR"},
    {id:"detector",name:"内容检测服务",state:{configured:health?.detector?.enabled,enabled:health?.detector?.ok},desc:health?.detector?.message||"文本/音频/视频检测"},
    {id:"push",name:"结果同步服务",state:{configured:health?.push_target?.enabled,enabled:health?.push_target?.events_url_configured},desc:health?.push_target?.name||"下游结果同步"},
  ];
  async function testConnector(id:string){if(id==="youtube"){try{const r=await api("/youtube/health");showToast(r.ok?"YouTube代理与采集器正常":"YouTube采集器或代理未就绪",r.ok?"success":"error");await load();}catch(e:any){showToast(e.message,"error")}return;}if(["douyin","kuaishou"].includes(id)){try{const r=await api(`/console/connectors/${id}/test`,{method:"POST"});showToast(r.ok?`${platformCN(id)}连接正常`:r.message||"连接能力未配置",r.ok?"success":"info");await load();}catch(e:any){showToast(e.message,"error")}}else showToast("当前状态来自后端健康检查","info");}
  function extractRoom(v:string){const m=v.match(/live\.douyin\.com\/(\d+)/);return m?.[1]||v.trim().split(/[\s,]/)[0];}
  async function startLive(){const room=extractRoom(liveForm.room);if(!room){showToast("请输入直播间ID或链接","error");return;}try{const source=liveForm.room.startsWith("http")?liveForm.room:(liveForm.platform==="douyin"?`https://live.douyin.com/${room}`:"");await api("/live-monitor/start",{method:"POST",body:JSON.stringify({platform:liveForm.platform,room_id:room,title:liveForm.title||`${platformCN(liveForm.platform)}直播间 ${room}`,source_url:source,stream_url:"",author_id:room,keywords:liveForm.keywords.split(/[，,\n]/).map(x=>x.trim()).filter(Boolean),regions:[],topic_template:"custom",segment_seconds:Number(liveForm.segment),auto_capture:true,auto_push:false,notes:liveForm.notes||"由原始治理前端接入"})});showToast(`直播间 ${room} 添加成功，系统已开始监控`,"success");setShowLive(false);setLiveForm({...liveForm,room:"",title:""});}catch(e:any){showToast(e.message,"error")}}
  async function startYoutube(){const url=youtubeForm.url.trim();if(!url){showToast("请输入YouTube频道或视频地址","error");return;}try{const r=await api("/youtube/tasks",{method:"POST",body:JSON.stringify({url,max_videos:Number(youtubeForm.maxVideos),max_comments:Number(youtubeForm.maxComments),max_height:Number(youtubeForm.maxHeight),download_video:youtubeForm.downloadVideo,auto_transcribe:youtubeForm.autoTranscribe,auto_audit:youtubeForm.autoAudit,audit_media:youtubeForm.auditMedia,monitor_enabled:youtubeForm.monitorEnabled,interval_seconds:Number(youtubeForm.intervalSeconds)})});showToast(`YouTube任务 #${r.job_id} 已创建`,"success");setShowYoutube(false);setYoutubeForm({...youtubeForm,url:""});await load();}catch(e:any){showToast(e.message,"error")}}
  async function createTask(){const kws=taskForm.keywords.split(/[，,\n]/).map(x=>x.trim()).filter(Boolean);if(!taskForm.name||!kws.length){showToast("请填写任务名称和关键词","error");return;}try{const types=[];if(taskForm.video)types.push("video");if(taskForm.live)types.push("live");await api("/tasks",{method:"POST",body:JSON.stringify({name:taskForm.name,platforms:[taskForm.platform],content_types:types,include_keywords:kws,exclude_keywords:taskForm.exclude.split(/[，,\n]/).map(x=>x.trim()).filter(Boolean),interval_seconds:300,enabled:true,topic_template:"custom",regions:taskForm.region?[taskForm.region]:[],keyword_match_mode:"any",time_range_hours:24,sort_by:"latest",result_limit:50,collect_comments:taskForm.comments,expand_related:taskForm.expand,auto_audit:taskForm.audit,auto_capture:taskForm.capture,auto_push:taskForm.push,push_after_review:true,notes:"由原始治理前端创建"})});showToast("关键词监测任务已创建","success");setShowTask(false);await load();}catch(e:any){showToast(e.message,"error")}}
  async function taskAction(id:number,action:"run"|"toggle"|"delete"){try{if(action==="delete")await api(`/tasks/${id}`,{method:"DELETE"});else await api(`/tasks/${id}/${action}`,{method:"POST"});showToast(action==="run"?"任务已加入运行队列":action==="toggle"?"任务状态已更新":"任务已删除","success");await load();}catch(e:any){showToast(e.message,"error")}}
  const tabStyle=(active:boolean)=>({padding:"8px 20px",borderRadius:"8px",fontSize:"13px",fontWeight:500,cursor:"pointer",background:active?"rgba(59,130,246,.15)":"transparent",color:active?"#1d4ed8":"#64748b",border:`1px solid ${active?"rgba(59,130,246,.35)":"transparent"}`});
  return <div className="p-4 flex flex-col gap-4 h-full overflow-hidden" style={{background:BG_PAGE}}>
    <div className="grid grid-cols-6 gap-2 flex-shrink-0">{connectors.map(c=><GlassCard key={c.id} className="px-3 py-3"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><PlatformLogo name={c.name}/><span className="text-[11px] font-medium text-slate-700">{c.name}</span></div><span className={`text-[9px] px-1.5 py-0.5 rounded ${c.state?.configured?"bg-green-50 text-green-600":"bg-slate-100 text-slate-500"}`}>{c.state?.configured?"已配置":"待配置"}</span></div><div className="text-[9px] text-slate-400 mt-2 min-h-7">{c.desc}</div><button onClick={()=>testConnector(c.id)} className="mt-2 text-[10px] text-blue-600 flex items-center gap-1"><RefreshCw size={10}/>测试连接</button></GlassCard>)}</div>
    <div className="flex items-center gap-2 flex-shrink-0 p-1 rounded-xl bg-slate-100" style={{border:"1px solid rgba(59,130,246,.1)",width:"fit-content"}}><button style={tabStyle(tab==="accounts")} onClick={()=>setTab("accounts")}>平台 + 账号配置</button><button style={tabStyle(tab==="keywords")} onClick={()=>setTab("keywords")}>平台 + 关键词配置</button></div>
    {tab==="accounts"?<GlassCard className="flex-1 flex flex-col overflow-hidden"><div className="p-4 flex items-center justify-between" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><div><div className="text-sm font-medium text-slate-800">平台账号与直播接入</div><div className="text-[10px] text-slate-400 mt-1">账号授权由后端安全保存；当前页面展示连接能力并提供直播ID接入</div></div><div className="flex gap-2"><BtnPrimary onClick={()=>setShowYoutube(true)}><Plus size={12}/>接入YouTube</BtnPrimary><BtnPrimary onClick={()=>setShowLive(true)}><Plus size={12}/>接入直播间</BtnPrimary></div></div><div className="p-4 grid grid-cols-2 gap-3 overflow-auto"><GlassCard className="p-4"><div className="text-xs font-medium text-slate-700 mb-3">抖音账号能力</div>{["直播ID采集","短视频搜索","公开视频评论","实时直播弹幕"].map((x,i)=><div key={x} className="flex justify-between py-2 text-[11px] border-b border-slate-100"><span className="text-slate-600">{x}</span><span className={i===0&&health?.live_monitor_bridge?.configured?"text-green-600":"text-slate-400"}>{i===0&&health?.live_monitor_bridge?.configured?"已接入":"待配置"}</span></div>)}</GlassCard><GlassCard className="p-4"><div className="text-xs font-medium text-slate-700 mb-3">快手账号能力</div>{["直播ID采集","短视频搜索","公开视频评论","实时直播弹幕"].map(x=><div key={x} className="flex justify-between py-2 text-[11px] border-b border-slate-100"><span className="text-slate-600">{x}</span><span className="text-slate-400">待配置</span></div>)}</GlassCard><GlassCard className="p-4"><div className="text-xs font-medium text-slate-700 mb-3">YouTube采集能力</div>{["频道最新视频","单视频下载","评论与回复","字幕/语音转写","视频与文本检测"].map(x=><div key={x} className="flex justify-between py-2 text-[11px] border-b border-slate-100"><span className="text-slate-600">{x}</span><span className={health?.youtube?.ok?"text-green-600":"text-slate-400"}>{health?.youtube?.ok?"已接入":"待配置"}</span></div>)}</GlassCard><GlassCard className="p-4 col-span-2"><div className="text-xs font-medium text-slate-700 mb-2">接入说明</div><div className="text-[11px] leading-6 text-slate-500">服务器地址、Token、Secret 等敏感字段继续保存在后端环境变量中，前端只展示连接状态。直播间支持直接粘贴完整链接，系统会自动提取房间ID。</div></GlassCard></div></GlassCard>:
    <GlassCard className="flex-1 flex flex-col overflow-hidden"><div className="p-4 flex items-center justify-between" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><div><div className="text-sm font-medium text-slate-800">关键词监测任务</div><div className="text-[10px] text-slate-400 mt-1">真实调用任务中心接口创建、运行、暂停和删除</div></div><BtnPrimary onClick={()=>setShowTask(true)}><Plus size={12}/>新增关键词任务</BtnPrimary></div><div className="overflow-auto flex-1"><table className="w-full text-xs"><thead className="sticky top-0 bg-slate-50"><tr>{["任务名称","平台","关键词","内容类型","状态","最近运行","操作"].map(h=><th key={h} className="text-left px-4 py-3 text-slate-500 font-medium">{h}</th>)}</tr></thead><tbody>{tasks.map(t=><tr key={t.id} className="hover:bg-blue-50/40 border-t border-slate-100"><td className="px-4 py-3 text-slate-700 font-medium">{t.name}</td><td className="px-4 py-3 text-slate-500">{(t.platforms||[]).map(platformCN).join("、")}</td><td className="px-4 py-3 text-slate-500 max-w-64 truncate">{(t.include_keywords||[]).join("、")}</td><td className="px-4 py-3 text-slate-500">{(t.content_types||[]).map((x:string)=>x==="live"?"直播":"短视频").join("、")}</td><td className="px-4 py-3"><span className={t.enabled?"text-green-600":"text-slate-400"}>{t.enabled?"启用":"暂停"}</span></td><td className="px-4 py-3 text-slate-400">{fmtDate(t.last_run_at)}</td><td className="px-4 py-3"><div className="flex gap-1"><button onClick={()=>taskAction(t.id,"run")} className="p-1 text-blue-500"><Play size={12}/></button><button onClick={()=>taskAction(t.id,"toggle")} className="p-1 text-orange-500">{t.enabled?<Pause size={12}/>:<Play size={12}/>}</button><button onClick={()=>taskAction(t.id,"delete")} className="p-1 text-red-500"><Trash2 size={12}/></button></div></td></tr>)}{!tasks.length&&<tr><td colSpan={7} className="text-center py-12 text-slate-400">暂无任务</td></tr>}</tbody></table></div></GlassCard>}
    <Modal open={showLive} onClose={()=>setShowLive(false)} title="接入直播间" width="max-w-xl"><div className="flex flex-col gap-4"><div className="grid grid-cols-2 gap-3"><FormSelect label="平台" value={liveForm.platform} onChange={v=>setLiveForm({...liveForm,platform:v})} options={[{value:"douyin",label:"抖音"},{value:"kuaishou",label:"快手"}]}/><FormSelect label="分片时长" value={liveForm.segment} onChange={v=>setLiveForm({...liveForm,segment:v})} options={[{value:"60",label:"60秒"},{value:"120",label:"120秒"},{value:"300",label:"300秒"}]}/></div><FormField label="直播间ID或完整链接 *" value={liveForm.room} onChange={v=>setLiveForm({...liveForm,room:v})} placeholder="https://live.douyin.com/840704572526"/><FormField label="任务名称" value={liveForm.title} onChange={v=>setLiveForm({...liveForm,title:v})} placeholder="可留空自动生成"/><FormField label="关注关键词" value={liveForm.keywords} onChange={v=>setLiveForm({...liveForm,keywords:v})} placeholder="多个词用逗号分隔"/><div className="flex gap-2"><BtnSecondary onClick={()=>setShowLive(false)} className="flex-1">取消</BtnSecondary><BtnPrimary onClick={startLive} className="flex-1">确认接入</BtnPrimary></div></div></Modal>
    <Modal open={showYoutube} onClose={()=>setShowYoutube(false)} title="接入YouTube监控" width="max-w-2xl"><div className="flex flex-col gap-4"><FormField label="YouTube频道、播放列表或视频地址 *" value={youtubeForm.url} onChange={v=>setYoutubeForm({...youtubeForm,url:v})} placeholder="https://www.youtube.com/@channel/videos"/><div className="grid grid-cols-3 gap-3"><FormField label="抓取视频数" value={youtubeForm.maxVideos} onChange={v=>setYoutubeForm({...youtubeForm,maxVideos:v})} placeholder="3"/><FormField label="每条最大评论数" value={youtubeForm.maxComments} onChange={v=>setYoutubeForm({...youtubeForm,maxComments:v})} placeholder="100"/><FormSelect label="最高画质" value={youtubeForm.maxHeight} onChange={v=>setYoutubeForm({...youtubeForm,maxHeight:v})} options={[{value:"480",label:"480P"},{value:"720",label:"720P"},{value:"1080",label:"1080P"}]}/></div><div className="grid grid-cols-3 gap-2">{[{k:"downloadVideo",l:"下载视频"},{k:"autoTranscribe",l:"字幕/ASR转写"},{k:"autoAudit",l:"自动文本检测"},{k:"auditMedia",l:"视频/音频检测"},{k:"monitorEnabled",l:"持续监控"}].map(x=><label key={x.k} className="flex items-center gap-2 text-[11px] text-slate-600 bg-slate-50 rounded-lg p-2"><input type="checkbox" checked={(youtubeForm as any)[x.k]} onChange={e=>setYoutubeForm({...youtubeForm,[x.k]:e.target.checked})}/>{x.l}</label>)}</div>{youtubeForm.monitorEnabled&&<FormSelect label="监控间隔" value={youtubeForm.intervalSeconds} onChange={v=>setYoutubeForm({...youtubeForm,intervalSeconds:v})} options={[{value:"600",label:"10分钟"},{value:"1800",label:"30分钟"},{value:"3600",label:"1小时"},{value:"21600",label:"6小时"}]}/>}<div className="text-[10px] leading-5 text-slate-400">公开内容默认无需Cookie；任务会采集视频、封面、元数据、评论和字幕，并按选项执行转写及检测。</div><div className="flex gap-2"><BtnSecondary onClick={()=>setShowYoutube(false)} className="flex-1">取消</BtnSecondary><BtnPrimary onClick={startYoutube} className="flex-1">创建YouTube任务</BtnPrimary></div></div></Modal>
    <Modal open={showTask} onClose={()=>setShowTask(false)} title="新增关键词任务" width="max-w-2xl"><div className="flex flex-col gap-4"><div className="grid grid-cols-2 gap-3"><FormField label="任务名称 *" value={taskForm.name} onChange={v=>setTaskForm({...taskForm,name:v})} placeholder="例如：公开话题监测"/><FormSelect label="平台" value={taskForm.platform} onChange={v=>setTaskForm({...taskForm,platform:v})} options={[{value:"demo",label:"演示连接器"},{value:"douyin",label:"抖音"},{value:"kuaishou",label:"快手"},{value:"youtube",label:"YouTube"}]}/><FormField label="关注关键词 *" value={taskForm.keywords} onChange={v=>setTaskForm({...taskForm,keywords:v})} placeholder="多个词用逗号分隔"/><FormField label="排除词" value={taskForm.exclude} onChange={v=>setTaskForm({...taskForm,exclude:v})} placeholder="广告词等"/><FormField label="区域" value={taskForm.region} onChange={v=>setTaskForm({...taskForm,region:v})} placeholder="可留空"/></div><div className="grid grid-cols-4 gap-2">{[{k:"video",l:"短视频"},{k:"live",l:"直播"},{k:"comments",l:"采集评论"},{k:"audit",l:"自动检测"},{k:"expand",l:"扩展线索"},{k:"capture",l:"媒体采集"},{k:"push",l:"结果同步"}].map(x=><label key={x.k} className="flex items-center gap-2 text-[11px] text-slate-600 bg-slate-50 rounded-lg p-2"><input type="checkbox" checked={(taskForm as any)[x.k]} onChange={e=>setTaskForm({...taskForm,[x.k]:e.target.checked})}/>{x.l}</label>)}</div><div className="flex gap-2"><BtnSecondary onClick={()=>setShowTask(false)} className="flex-1">取消</BtnSecondary><BtnPrimary onClick={createTask} className="flex-1">创建任务</BtnPrimary></div></div></Modal>
  </div>;
}

// ── Live Page// ── Live Page ───────────────────────────────────────────────────────────────────
function LivePage({accounts, showToast}: {accounts:Account[]; showToast:(m:string,t:"success"|"error"|"info")=>void}) {
  const [sessions,setSessions]=useState<AnyRecord[]>([]);
  const [contents,setContents]=useState<AnyRecord[]>([]);
  const [feed,setFeed]=useState<AnyRecord[]>([]);
  const [jobs,setJobs]=useState<AnyRecord[]>([]);
  const [selected,setSelected]=useState<number|null>(null);
  const [detail,setDetail]=useState<AnyRecord|null>(null);
  const [transcript,setTranscript]=useState("");
  const [tab,setTab]=useState<"transcript"|"video"|"danmu"|"comments"|"audit"|"logs">("transcript");
  const load=useCallback(async()=>{try{const [s,c,f,j]=await Promise.all([api("/live-sessions"),api("/contents?content_type=live&limit=200"),api("/console/feed?limit=500"),api("/jobs?limit=300")]);setSessions(s);setContents(c);setFeed(f);setJobs(j);if(!selected&&s.length)setSelected(s[0].id);}catch(e:any){showToast(e.message,"error")}},[selected,showToast]);
  useEffect(()=>{load();const id=setInterval(load,20000);return()=>clearInterval(id)},[load]);
  const session=sessions.find(x=>x.id===selected);
  const content=contents.find(x=>x.id===session?.content_id);
  useEffect(()=>{setTranscript("");if(!content){setDetail(null);return;}api(`/contents/${content.id}`).then(async d=>{setDetail(d);const t=(d.evidence||[]).filter((x:AnyRecord)=>x.file_type==="text").sort((a:AnyRecord,b:AnyRecord)=>new Date(b.collected_at||0).getTime()-new Date(a.collected_at||0).getTime())[0];if(t)try{setTranscript(await apiText(`/evidence/${t.id}/view`));}catch{setTranscript("转写文件无法从当前服务器读取");}}).catch((e:any)=>showToast(e.message,"error"));},[content?.id,showToast]);
  const videos=(detail?.evidence||[]).filter((x:AnyRecord)=>x.file_type==="video").sort((a:AnyRecord,b:AnyRecord)=>new Date(b.collected_at||0).getTime()-new Date(a.collected_at||0).getTime());
  const latestVideo=videos[0];
  const liveMessages=feed.filter(x=>x.kind==="live_message"&&(!content||x.content_id===content.id));
  const comments=feed.filter(x=>x.kind==="comment"&&(!content||x.content_id===content.id));
  const sessionJobs=jobs.filter(x=>Number(x.payload?.content_id)===Number(content?.id)||Number(x.payload?.session_id)===Number(session?.id));
  async function stop(){if(!session)return;try{await api(`/live-sessions/${session.id}/stop`,{method:"POST"});showToast("直播会话已停止","success");await load();}catch(e:any){showToast(e.message,"error")}}

  async function removeSession(){
    if(!session)return;

    const confirmed=window.confirm(
      "确定删除这个直播监测任务吗？\n"+
      "删除后任务将从直播检测会话列表移除，已采集的历史检测结果仍然保留。"
    );

    if(!confirmed)return;

    try{
      // 先调用原有停止接口
      try{
        await api(
          `/live-sessions/${session.id}/stop`,
          {method:"POST"}
        );
      }catch(_stopError){
        // 会话可能已经停止，不影响继续删除
      }

      // 再删除会话记录
      await api(
        `/live-sessions/${session.id}`,
        {method:"DELETE"}
      );

      showToast(
        "直播监测任务已删除",
        "success"
      );

      setSelected(null);
      await load();
    }catch(e:any){
      showToast(
        e.message||"删除直播监测任务失败",
        "error"
      );
    }
  }


  function auditObject(value:any):AnyRecord {
    if(value && typeof value==="object"){
      return value;
    }

    if(typeof value==="string"){
      try{
        const parsed=JSON.parse(value);
        return parsed && typeof parsed==="object"
          ? parsed
          : {};
      }catch(_error){
        return {};
      }
    }

    return {};
  }

  function auditList(value:any):string[] {
    if(Array.isArray(value)){
      return value
        .map(x=>String(x))
        .filter(Boolean);
    }

    if(typeof value==="string"){
      const trimmed=value.trim();

      if(!trimmed){
        return [];
      }

      try{
        const parsed=JSON.parse(trimmed);

        if(Array.isArray(parsed)){
          return parsed
            .map(x=>String(x))
            .filter(Boolean);
        }
      }catch(_error){
        return trimmed
          .split(/[，,、]/)
          .map(x=>x.trim())
          .filter(Boolean);
      }
    }

    return [];
  }

  function auditView(a:AnyRecord){
    const response=auditObject(a.response);
    const legacy=auditObject(response.legacy_response);
    const directData=auditObject(response.data);

    const legacyTextData=auditObject(
      legacy?.raw_results
        ?.text
        ?.chunks
        ?.[0]
        ?.result
        ?.response_json
        ?.data
    );

    const data=Object.keys(directData).length
      ? directData
      : legacyTextData;

    const status=String(
      a.status
      || data.conclusion
      || data.content_category
      || legacy.status
      || "未知"
    );

    const confidenceRaw=
      a.confidence
      ?? data.confidence
      ?? data.max_confidence
      ?? legacy.max_confidence;

    const confidence=(
      confidenceRaw!==null
      && confidenceRaw!==undefined
      && Number.isFinite(Number(confidenceRaw))
    )
      ? Number(confidenceRaw)
      : null;

    const rootLabels=auditList(a.labels);
    const dataLabels=auditList(data.labels);
    const legacyLabels=auditList(legacy.labels);

    const labels=rootLabels.length
      ? rootLabels
      : dataLabels.length
        ? dataLabels
        : legacyLabels;

    const rootWords=auditList(a.risk_words);
    const dataWords=auditList(data.risk_words);
    const legacyWords=auditList(legacy.risk_words);

    const riskWords=rootWords.length
      ? rootWords
      : dataWords.length
        ? dataWords
        : legacyWords;

    const suggestionRaw=String(
      data.suggestion
      || legacy.suggestion
      || ""
    ).toLowerCase();

    const suggestion=
      suggestionRaw==="pass"
        ? "正常通过"
        : suggestionRaw==="review"
          ? "建议人工复核"
          : ["block","reject"].includes(suggestionRaw)
            ? "建议拦截处置"
            : status==="合规"
              ? "正常通过"
              : status==="疑似"
                ? "建议人工复核"
                : status==="违规"
                  ? "建议拦截处置"
                  : "暂无建议";

    const modalityStatus=auditObject(
      legacy.modality_status
    );

    const modalityName=
      a.modality==="legacy_live_text"
        ? "直播转写文本检测"
        : a.modality==="legacy_audit"
          ? "直播内容综合检测"
          : a.modality==="text"
            ? "文本检测"
            : a.modality==="audio"
              ? "音频检测"
              : a.modality==="video"
                ? "视频检测"
                : a.modality||"内容检测";

    return {
      status,
      confidence,
      labels,
      riskWords,
      suggestion,
      modalityName,
      modalityStatus,
      detectorName:
        a.detector_name
        || a.model_name
        || "内容安全检测器",
      detectorVersion:
        a.detector_version
        || a.model_version
        || "—",
      segmentId:
        legacy.segment_id
        || response.segment_id
        || "",
      createdAt:
        a.created_at
        || legacy.audit_time
        || "",
    };
  }

  function auditStatusClass(status:string){
    if(status==="合规"){
      return "text-green-700 bg-green-50 border-green-200";
    }

    if(status==="疑似"){
      return "text-amber-700 bg-amber-50 border-amber-200";
    }

    if(status==="违规"){
      return "text-red-700 bg-red-50 border-red-200";
    }

    if(status==="未启用"){
      return "text-slate-500 bg-slate-100 border-slate-200";
    }

    return "text-blue-700 bg-blue-50 border-blue-200";
  }


  return <div className="p-3 h-full overflow-hidden flex gap-3" style={{background:BG_PAGE}}>
    <GlassCard className="w-72 flex-shrink-0 flex flex-col overflow-hidden"><div className="p-3 flex items-center justify-between" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><div><div className="text-xs font-medium text-slate-700">直播会话</div><div className="text-[9px] text-slate-400 mt-0.5">共 {sessions.length} 个会话</div></div><button onClick={load} className="text-blue-500"><RefreshCw size={12}/></button></div><div className="overflow-auto flex-1">{sessions.map(s=>{const c=contents.find(x=>x.id===s.content_id);return <button key={s.id} onClick={()=>setSelected(s.id)} className="w-full text-left p-3 hover:bg-blue-50/50" style={{background:selected===s.id?"rgba(59,130,246,.08)":"transparent",borderBottom:`1px solid ${BORDER_CARD}`}}><div className="flex items-center gap-2"><span className={`w-2 h-2 rounded-full ${["completed","stopped"].includes(s.status)?"bg-slate-300":"bg-green-500 blink"}`}/><span className="text-[11px] font-medium text-slate-700 truncate flex-1">{c?.title||`直播会话 ${s.id}`}</span></div><div className="text-[9px] text-slate-400 mt-1">状态：{statusCN(s.status)} · {s.segment_seconds}s</div><div className="text-[9px] text-slate-400 mt-1">{fmtDate(s.started_at)}</div>{s.last_error&&<div className="text-[9px] text-red-500 mt-1 truncate">{s.last_error}</div>}</button>})}{!sessions.length&&<div className="p-8 text-center text-xs text-slate-400">暂无直播会话，请先在监测配置中接入直播间</div>}</div></GlassCard>
    <div className="flex-1 min-w-0 flex flex-col gap-3 overflow-hidden">
      <GlassCard className="flex-1 min-h-0 overflow-hidden flex flex-col"><div className="p-3 flex items-center justify-between" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><div><div className="text-sm font-medium text-slate-800">{content?.title||"请选择直播会话"}</div><div className="text-[10px] text-slate-400 mt-1">{content?`${platformCN(content.platform)} · 房间/内容ID ${content.platform_content_id}`:"视频片段、语音转写和检测结果来自真实后端"}</div></div><div className="flex gap-2">{session&&<>
  <BtnSecondary onClick={stop}>
    <Square size={11}/>
    停止监测
  </BtnSecondary>
  <BtnSecondary onClick={removeSession}>
    删除任务
  </BtnSecondary>
</>}
<BtnSecondary onClick={load}>
  <RefreshCw size={11}/>
  刷新
</BtnSecondary></div></div>
        {content?<div className="flex-1 min-h-0 grid grid-cols-[1.4fr_1fr] gap-3 p-3"><div className="rounded-xl overflow-hidden bg-slate-900 relative min-h-0">{latestVideo?<video key={latestVideo.id} src={evidenceUrl(latestVideo.id)} controls className="w-full h-full object-contain"/>:<div className="h-full flex flex-col items-center justify-center text-slate-400"><Video size={34}/><div className="text-xs mt-2">暂无可播放视频分片</div><div className="text-[10px] mt-1">会话状态：{statusCN(session?.status)}</div></div>}<div className="absolute top-2 left-2 text-[9px] px-2 py-1 rounded bg-black/60 text-white">{latestVideo?"最新视频分片":"等待采集"}</div></div><div className="overflow-auto"><div className="grid grid-cols-2 gap-2 mb-3">{[{k:"视频片段",v:videos.length},{k:"转写文件",v:(detail?.evidence||[]).filter((x:AnyRecord)=>x.file_type==="text").length},{k:"检测记录",v:(detail?.audits||[]).length},{k:"任务记录",v:sessionJobs.length}].map(x=><div key={x.k} className="rounded-lg bg-slate-50 p-3"><div className="font-mono text-lg text-blue-600">{x.v}</div><div className="text-[9px] text-slate-500">{x.k}</div></div>)}</div>{["直播源解析","视频录制","音频提取","语音转写","内容检测","证据归档"].map((x,i)=>{const ok=i===0?!!session:i===1?videos.length>0:i===2?(detail?.evidence||[]).some((e:AnyRecord)=>e.file_type==="audio"):i===3?!!transcript:i===4?(detail?.audits||[]).length>0:(detail?.evidence||[]).length>0;return <div key={x} className="flex items-center justify-between py-2 border-b border-slate-100 text-[11px]"><span className="text-slate-600">{i+1}. {x}</span><span className={ok?"text-green-600":"text-slate-400"}>{ok?"已完成":i===4?"未启用或等待":"等待中"}</span></div>})}</div></div>:<div className="flex-1 flex items-center justify-center text-slate-400 text-xs">选择左侧直播会话</div>}
      </GlassCard>
      <GlassCard className="h-[310px] flex flex-col overflow-hidden"><div className="p-1 flex gap-1 border-b border-blue-100 overflow-x-auto">{[{id:"transcript",l:"语音转写"},{id:"video",l:"视频片段"},{id:"danmu",l:"实时弹幕"},{id:"comments",l:"公开视频评论"},{id:"audit",l:"检测结果"},{id:"logs",l:"运行日志"}].map(x=><button key={x.id} onClick={()=>setTab(x.id as any)} className={`px-3 py-2 rounded-lg text-[10px] whitespace-nowrap ${tab===x.id?"bg-blue-600 text-white":"text-slate-500 hover:bg-blue-50"}`}>{x.l}</button>)}</div><div className="flex-1 overflow-auto p-3">{tab==="transcript"&&(transcript?<pre className="whitespace-pre-wrap text-[11px] leading-6 text-slate-700 font-sans">{transcript}</pre>:<div className="h-full flex items-center justify-center text-xs text-slate-400">暂无ASR转写文本</div>)}{tab==="video"&&(videos.length?<div className="grid grid-cols-3 gap-2">{videos.map((e:AnyRecord)=><a key={e.id} href={evidenceUrl(e.id)} target="_blank" rel="noreferrer" className="rounded-lg border border-blue-100 p-3 hover:bg-blue-50"><FileVideo size={18} className="text-blue-500"/><div className="text-[10px] text-slate-700 mt-2 truncate">{e.path?.split(/[\\/]/).pop()||`视频证据 ${e.id}`}</div><div className="text-[9px] text-slate-400 mt-1">{fmtDate(e.collected_at)}</div></a>)}</div>:<div className="h-full flex items-center justify-center text-xs text-slate-400">暂无视频片段</div>)}{tab==="danmu"&&(liveMessages.length?liveMessages.map(x=><div key={x.id} className="py-2 border-b border-slate-100"><div className="text-[9px] text-slate-400">[{platformCN(x.platform)}] [{fmtDate(x.event_time,false)}] 账号：{x.author_alias||"匿名"}</div><div className="text-[11px] text-slate-700 mt-1">{x.text}</div></div>):<div className="h-full flex flex-col items-center justify-center text-center text-slate-400"><MessageSquare size={24}/><div className="text-xs mt-2">实时弹幕接口尚未接入</div><div className="text-[10px] mt-1 max-w-md">当前已接入视频分片、音频提取和语音转写；公开视频评论不会混入实时弹幕。</div></div>)}{tab==="comments"&&(comments.length?comments.map(x=><div key={x.id} className="py-2 border-b border-slate-100"><div className="text-[9px] text-slate-400">数据来源：公开视频评论 · {x.author_alias||"匿名"} · {fmtDate(x.event_time)}</div><div className="text-[11px] text-slate-700 mt-1">{x.text}</div></div>):<div className="h-full flex items-center justify-center text-xs text-slate-400">暂无公开视频评论</div>)}{tab==="audit"&&(
  (detail?.audits||[]).length
    ? <div className="space-y-2">
        {(detail?.audits||[]).map((a:AnyRecord)=>{
          const view=auditView(a);
          const modalities=view.modalityStatus;

          return <div
            key={a.id}
            className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className="text-[12px] font-medium text-slate-800">
                  {view.modalityName}
                </div>

                <div className="text-[9px] text-slate-400 mt-1">
                  {view.detectorName}
                  {" · "}
                  版本 {view.detectorVersion}
                  {view.segmentId
                    ? ` · 片段 ${view.segmentId}`
                    : ""}
                </div>
              </div>

              <div className="flex items-center gap-2">
                {view.confidence!==null&&
                  <span className="text-[11px] font-mono text-blue-600">
                    {Math.round(view.confidence*100)}%
                  </span>
                }

                <span
                  className={`px-2.5 py-1 rounded-full border text-[10px] font-medium ${auditStatusClass(view.status)}`}
                >
                  {view.status}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-x-5 gap-y-2 mt-3 text-[10px]">
              <div>
                <span className="text-slate-400">检测结论：</span>
                <span className="text-slate-700 font-medium">
                  {view.status}
                </span>
              </div>

              <div>
                <span className="text-slate-400">处置建议：</span>
                <span className="text-slate-700">
                  {view.suggestion}
                </span>
              </div>

              <div>
                <span className="text-slate-400">风险标签：</span>
                <span className="text-slate-700">
                  {view.labels.length
                    ? view.labels.join("、")
                    : "未命中风险标签"}
                </span>
              </div>

              <div>
                <span className="text-slate-400">风险词：</span>
                <span className="text-slate-700">
                  {view.riskWords.length
                    ? view.riskWords.join("、")
                    : "未命中风险词"}
                </span>
              </div>
            </div>

            {Object.keys(modalities).length>0&&
              <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-slate-100">
                <span className="text-[9px] text-slate-400">
                  分模态结果
                </span>

                <span className={`text-[9px] px-2 py-1 rounded ${
                  modalities.video==="合规"
                    ? "text-green-700 bg-green-50"
                    : modalities.video==="违规"
                      ? "text-red-700 bg-red-50"
                      : "text-slate-500 bg-slate-100"
                }`}>
                  视频：{modalities.video||"未知"}
                </span>

                <span className={`text-[9px] px-2 py-1 rounded ${
                  modalities.audio==="合规"
                    ? "text-green-700 bg-green-50"
                    : modalities.audio==="违规"
                      ? "text-red-700 bg-red-50"
                      : "text-slate-500 bg-slate-100"
                }`}>
                  音频：{modalities.audio||"未知"}
                </span>

                <span className={`text-[9px] px-2 py-1 rounded ${
                  modalities.text==="合规"
                    ? "text-green-700 bg-green-50"
                    : modalities.text==="违规"
                      ? "text-red-700 bg-red-50"
                      : modalities.text==="疑似"
                        ? "text-amber-700 bg-amber-50"
                        : "text-slate-500 bg-slate-100"
                }`}>
                  文本：{modalities.text||"未知"}
                </span>
              </div>
            }

            <div className="text-[9px] text-slate-400 mt-3">
              检测时间：{fmtDate(view.createdAt)}
            </div>
          </div>
        })}
      </div>
    : <div className="h-full flex items-center justify-center text-xs text-slate-400">
        检测服务未运行或暂无结果
      </div>
)}{tab==="logs"&&(sessionJobs.length?sessionJobs.map(j=><div key={j.id} className="py-2 border-b border-slate-100 text-[10px]"><span className="font-mono text-slate-400">#{j.id}</span> <span className="text-slate-700">{j.job_type}</span> <span className={j.status==="failed"?"text-red-500":"text-green-600"}>{statusCN(j.status)}</span><span className="text-slate-400 ml-2">{fmtDate(j.updated_at)}</span>{j.last_error&&<div className="text-red-500 mt-1">{j.last_error}</div>}</div>):<div className="h-full flex items-center justify-center text-xs text-slate-400">暂无相关任务日志</div>)}</div></GlassCard>
    </div>
  </div>;
}

// ── System Page// ── System Page ─────────────────────────────────────────────────────────────────
function SystemPage({showToast}: {showToast:(m:string,t:"success"|"error"|"info")=>void}) {
  const [tab,setTab]=useState<"users"|"logs">("users");
  const [health,setHealth]=useState<AnyRecord|null>(null);
  const [jobs,setJobs]=useState<AnyRecord[]>([]);
  const [statusFilter,setStatusFilter]=useState("");
  const load=useCallback(async()=>{try{const [h,j]=await Promise.all([api("/health"),api(`/jobs?limit=500${statusFilter?`&status=${statusFilter}`:""}`)]);setHealth(h);setJobs(j);}catch(e:any){showToast(e.message,"error")}},[showToast,statusFilter]);
  useEffect(()=>{load()},[load]);
  const services=[
    {name:"任务中心API",ok:health?.ok,desc:"FastAPI与数据库"},
    {name:"抖音连接器",ok:health?.platforms?.douyin?.configured,desc:health?.platforms?.douyin?.base_url||"未配置"},
    {name:"快手连接器",ok:health?.platforms?.kuaishou?.configured,desc:health?.platforms?.kuaishou?.base_url||"未配置"},
    {name:"直播采集桥接",ok:health?.live_monitor_bridge?.configured,desc:health?.live_monitor_bridge?.base_url||"未配置"},
    {name:"内容检测服务",ok:health?.detector?.ok,desc:health?.detector?.message||"未启用"},
    {name:"结果同步服务",ok:health?.push_target?.enabled,desc:health?.push_target?.name||"未配置"},
  ];
  return <div className="p-4 flex flex-col gap-4 h-full overflow-hidden" style={{background:BG_PAGE}}><GlassCard className="p-1 flex gap-1 flex-shrink-0"><button onClick={()=>setTab("users")} className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium ${tab==="users"?"text-white":"text-slate-500"}`} style={{background:tab==="users"?"rgba(59,130,246,.8)":"transparent"}}><Server size={12}/>运行状态</button><button onClick={()=>setTab("logs")} className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium ${tab==="logs"?"text-white":"text-slate-500"}`} style={{background:tab==="logs"?"rgba(59,130,246,.8)":"transparent"}}><Terminal size={12}/>任务记录</button></GlassCard><div className="flex-1 overflow-hidden">{tab==="users"?<div className="grid grid-cols-3 gap-3 h-full content-start overflow-auto">{services.map(s=><GlassCard key={s.name} className="p-4"><div className="flex items-center justify-between"><div className="flex items-center gap-2"><div className={`w-8 h-8 rounded-lg flex items-center justify-center ${s.ok?"bg-green-50":"bg-slate-100"}`}><Server size={15} className={s.ok?"text-green-600":"text-slate-400"}/></div><div><div className="text-xs font-medium text-slate-700">{s.name}</div><div className="text-[9px] text-slate-400 mt-0.5 max-w-52 truncate">{s.desc}</div></div></div><span className={`text-[9px] px-2 py-1 rounded ${s.ok?"bg-green-50 text-green-600":"bg-slate-100 text-slate-500"}`}>{s.ok?"正常/已配置":"待配置"}</span></div></GlassCard>)}<GlassCard className="p-4 col-span-3"><div className="flex items-center justify-between"><div><div className="text-xs font-medium text-slate-700">敏感配置说明</div><div className="text-[10px] text-slate-500 mt-2 leading-6">连接器地址、Token、Secret 与检测服务地址均由后端环境变量保存。前端只显示是否配置，不返回完整敏感值。</div></div><BtnSecondary onClick={load}><RefreshCw size={11}/>刷新状态</BtnSecondary></div></GlassCard></div>:<GlassCard className="h-full flex flex-col overflow-hidden"><div className="p-3 flex items-center gap-3" style={{borderBottom:`1px solid ${BORDER_CARD}`}}><span className="text-xs font-medium text-slate-700">后台任务记录</span><select value={statusFilter} onChange={e=>setStatusFilter(e.target.value)} className="text-[10px] px-2 py-1.5 rounded-lg border border-blue-100"><option value="">全部状态</option><option value="pending">等待执行</option><option value="running">执行中</option><option value="success">执行成功</option><option value="failed">执行失败</option></select><button onClick={load} className="ml-auto text-blue-500"><RefreshCw size={12}/></button></div><div className="overflow-auto flex-1"><table className="w-full text-xs"><thead className="sticky top-0 bg-slate-50"><tr>{["任务ID","类型","状态","目标","尝试次数","更新时间","错误"].map(h=><th key={h} className="text-left px-4 py-3 text-slate-500 font-medium">{h}</th>)}</tr></thead><tbody>{jobs.map(j=><tr key={j.id} className="border-t border-slate-100 hover:bg-blue-50/30"><td className="px-4 py-2.5 font-mono text-slate-400">#{j.id}</td><td className="px-4 py-2.5 text-slate-700">{j.job_type}</td><td className={`px-4 py-2.5 ${j.status==="failed"?"text-red-500":j.status==="success"?"text-green-600":"text-orange-500"}`}>{statusCN(j.status)}</td><td className="px-4 py-2.5 text-slate-500">{j.payload?.task_id||j.payload?.content_id||j.payload?.session_id||"—"}</td><td className="px-4 py-2.5 text-slate-500">{j.attempts}/{j.max_attempts}</td><td className="px-4 py-2.5 text-slate-400">{fmtDate(j.updated_at)}</td><td className="px-4 py-2.5 text-red-500 max-w-72 truncate">{j.last_error||"—"}</td></tr>)}</tbody></table></div></GlassCard>}</div></div>;
}

// ── App// ── App ─────────────────────────────────────────────────────────────────────────
export default function App() {
  const [loggedIn, setLoggedIn] = useState(false);
  const [page, setPage] = useState<Page>("dashboard");
  const [collapsed, setCollapsed] = useState(false);
  const [accounts, setAccounts] = useState<Account[]>(INITIAL_ACCOUNTS);
  const [toast, setToast] = useState<{msg:string;type:"success"|"error"|"info"}|null>(null);
  const showToast = useCallback((msg: string, type: "success"|"error"|"info") => setToast({msg,type}), []);

  const labels: Record<Page,string> = {
    login:"登录", dashboard:"网络直播内容有害监测平台 · 态势大屏", accounts:"监测配置",
    alert:"预警处置中心", live:"网络直播实时监控", system:"系统管理",
  };

  return <>
    <style dangerouslySetInnerHTML={{__html:GLOBAL_STYLES}}/>
    <div className="w-screen h-screen overflow-hidden" style={{background:BG_PAGE, fontFamily:"'Noto Sans SC',sans-serif"}}>
      {toast && <Toast msg={toast.msg} type={toast.type} onClose={() => setToast(null)}/>}
      {!loggedIn
        ? <LoginPage onLogin={() => setLoggedIn(true)}/>
        : <div className="flex h-full">
          <Sidebar current={page} onChange={setPage} collapsed={collapsed} onToggle={() => setCollapsed(v => !v)}/>
          <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
            <TopBar title={labels[page]} onLogout={() => setLoggedIn(false)}/>
            <div className="flex-1 overflow-hidden">
              {page==="dashboard" && <DashboardPage/>}
              {page==="accounts" && <MonitoringConfigPage accounts={accounts} setAccounts={setAccounts} showToast={showToast}/>}
              {page==="alert" && <AlertPage showToast={showToast}/>}
              {page==="live" && <LivePage accounts={accounts} showToast={showToast}/>}
              {page==="system" && <SystemPage showToast={showToast}/>}
            </div>
          </div>
        </div>}
    </div>
  </>;
}
