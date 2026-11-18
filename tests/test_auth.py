from datetime import datetime, timedelta, timezone
import jwt
from tests.helpers import authenticate


def test_register_login_me(client):
    user = client.get('/auth/me').json()
    assert user['email'] and not user['is_owner']
    assert 'password_hash' not in user
    assert client.post('/auth/register', json={'email': user['email'].upper(), 'display_name': 'Other',
                                              'password': 'not-a-real-secret'}).status_code == 409
    assert client.post('/auth/login', json={'email': user['email'], 'password': 'wrong'}).status_code == 401
    assert client.post('/auth/login', json={'email': 'missing@example.com', 'password': 'wrong'}).status_code == 401


def test_no_owner_self_registration(client):
    assert client.post('/auth/register', json={'email': 'root@example.com', 'display_name': 'Root',
        'password': 'not-a-real-secret', 'is_owner': True}).status_code == 422


def test_invalid_tokens(client):
    uid = client.get('/auth/me').json()['id']
    key = client.app.state.settings.jwt_secret.get_secret_value()
    for token in ['broken', jwt.encode({'sub': uid}, key, algorithm='HS256'),
                  jwt.encode({'sub': uid, 'exp': datetime.now(timezone.utc)-timedelta(seconds=5),
                              'iat': datetime.now(timezone.utc)-timedelta(hours=1),
                              'iss': 'meeting-assistant', 'aud': 'meeting-assistant-api'}, key, algorithm='HS256')]:
        client.headers['Authorization'] = 'Bearer ' + token
        assert client.get('/auth/me').status_code == 401
        assert client.get('/meetings').status_code == 401
    client.headers.pop('Authorization')
    assert client.get('/meetings').status_code == 401
    assert client.get('/health').status_code == 200


def test_meeting_authorization(client):
    mid = client.post('/meetings', json={'title': 'Private', 'content': 'Private synthetic note'}).json()['id']
    authenticate(client)
    assert client.get('/meetings').json() == []
    assert client.get('/meetings/'+mid).status_code == 404
    assert client.patch('/meetings/'+mid, json={'title': 'changed'}).status_code == 404
    assert client.delete('/meetings/'+mid).status_code == 404


def test_owner_and_inactive_user(client):
    from app.db.session import get_session
    from app.models.user import User
    from uuid import UUID
    mid = client.post('/meetings', json={'title': 'Private', 'content': 'Note'}).json()['id']
    other = authenticate(client)
    session = next(client.app.dependency_overrides[get_session]())
    user = session.get(User, UUID(other['id']))
    assert user.password_hash.startswith('$argon2id$')
    user.is_owner = True
    session.commit()
    assert client.get('/meetings/'+mid).status_code == 200
    user.is_active = False
    session.commit()
    assert client.get('/auth/me').status_code == 401
