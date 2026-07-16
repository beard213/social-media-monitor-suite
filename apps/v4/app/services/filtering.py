from __future__ import annotations
import re, yaml
from pathlib import Path

class ContentFilter:
    def __init__(self, path="config/filter_rules.yaml"):
        self.config=yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    def evaluate(self, text:str, include_keywords:list[str]|None=None, exclude_keywords:list[str]|None=None):
        include_keywords=include_keywords or []
        exclude_keywords=exclude_keywords or self.config["relevance"].get("default_exclude",[])
        t=(text or "").strip()
        matched=[x for x in include_keywords if x and x.lower() in t.lower()]
        excluded=[x for x in exclude_keywords if x and x.lower() in t.lower()]
        score=0; reasons=[]
        ad=self.config["advertising"]
        for phrase, points in ad.get("phrases",{}).items():
            if phrase.lower() in t.lower(): score+=points; reasons.append(f"营销词:{phrase}")
        for pattern in ad.get("contact_patterns",[]):
            if re.search(pattern,t,re.I): score+=3; reasons.append("联系方式导流")
        for combo in ad.get("combinations",[]):
            if all(x.lower() in t.lower() for x in combo): score+=2; reasons.append("营销组合:"+"+".join(combo))
        if excluded: reasons += [f"排除词:{x}" for x in excluded]
        if include_keywords and not matched:
            return {"status":"irrelevant","score":score,"reasons":["未命中关注词",*reasons],"matched":matched}
        if score >= ad.get("threshold",5): status="advertising"
        elif excluded and not matched: status="irrelevant"
        else: status="kept"
        return {"status":status,"score":score,"reasons":reasons,"matched":matched}

content_filter=ContentFilter()
