import os
os.environ['DATABASE_URL']='sqlite:///./data/test.db'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get('/api/health').status_code==200
def test_create_task():
    r=client.post('/api/tasks',json={'name':'test','platforms':['demo'],'content_types':['video'],'include_keywords':['讨薪'],'exclude_keywords':[],'interval_seconds':60,'enabled':True})
    assert r.status_code==200

def test_console_contract():
    response = client.get('/api/console/connector-contract')
    assert response.status_code == 200
    paths = {item['path'] for item in response.json()['endpoints']}
    assert '/v1/search' in paths
    assert '/v1/comments' in paths


def test_console_overview():
    response = client.get('/api/console/overview')
    assert response.status_code == 200
    assert 'metrics' in response.json()


def test_live_monitor_by_id_waits_for_source():
    response = client.post(
        '/api/live-monitor/start',
        json={
            'platform': 'demo',
            'room_id': 'room-test-001',
            'keywords': ['雄安'],
            'regions': ['xiongan'],
            'segment_seconds': 120,
            'auto_capture': False,
            'auto_push': False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data['content_id'] > 0
    assert data['ready_for_capture'] is False


def test_connector_contract_has_relations():
    response = client.get('/api/console/connector-contract')
    paths = {item['path'] for item in response.json()['endpoints']}
    assert '/v1/relations' in paths


def test_live_monitor_by_id_accepts_existing_stream_url():
    response = client.post(
        '/api/live-monitor/start',
        json={
            'platform': 'demo',
            'room_id': 'room-test-ready',
            'stream_url': 'https://example.invalid/live/test.m3u8',
            'auto_capture': False,
        },
    )
    assert response.status_code == 200
    assert response.json()['ready_for_capture'] is True
