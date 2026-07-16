from pathlib import Path
import argparse
from sqlalchemy import select
from app.db.session import SessionLocal, Base, engine
from app.db.models import Content
from app.services.evidence import register_file
from app.utils import anonymize

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',required=True,help='旧 output/douyin_live_dataset 目录');args=ap.parse_args()
    Base.metadata.create_all(engine); root=Path(args.root)
    with SessionLocal() as db:
        for account in root.iterdir():
            if not account.is_dir(): continue
            for video in (account/'video').glob('*.mp4') if (account/'video').exists() else []:
                pid=f"legacy:{account.name}:{video.stem}"
                c=db.scalar(select(Content).where(Content.platform=='douyin',Content.platform_content_id==pid))
                if not c:
                    c=Content(platform='douyin',platform_content_id=pid,content_type='live',title=f'旧直播片段 {account.name} {video.stem}',author_alias=anonymize(account.name),filter_status='kept');db.add(c);db.commit();db.refresh(c)
                register_file(db,c.id,'video',video)
                audio=account/'audio'/(video.stem+'.wav'); text=account/'text'/(video.stem+'.txt')
                if audio.exists(): register_file(db,c.id,'audio',audio)
                if text.exists(): register_file(db,c.id,'text',text)
                print('imported',video)
if __name__=='__main__': main()
