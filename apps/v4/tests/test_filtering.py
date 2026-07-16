from app.services.filtering import content_filter

def test_event_kept():
    r=content_filter.evaluate('某项目工人反映拖欠工资，记者采访律师说明法规',['拖欠工资'],[])
    assert r['status']=='kept'
def test_ad_filtered():
    r=content_filter.evaluate('讨薪律师免费咨询，点击头像私信，加微信，全国接单',['讨薪'],[])
    assert r['status']=='advertising'
