from pathlib import Path

def transcribe(audio:Path, output:Path):
    try:
        from funasr import AutoModel
    except Exception as exc:
        output.write_text("[FunASR未安装，未执行转写]",encoding="utf-8")
        return {"status":"skipped","error":str(exc),"text":output.read_text(encoding='utf-8')}
    model=AutoModel(model="paraformer-zh",vad_model="fsmn-vad",punc_model="ct-punc",device="cpu")
    result=model.generate(input=str(audio),batch_size_s=300)
    texts=[]
    for item in result if isinstance(result,list) else [result]:
        if isinstance(item,dict) and item.get("text"): texts.append(str(item["text"]))
    text='\n'.join(texts).strip(); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(text,encoding='utf-8')
    return {"status":"success","text":text,"raw":result}
