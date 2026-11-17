"""Flask integration checks: run with `pip install -r requirements.txt` on Mac.

These tests are skipped in minimal offline environments without Flask.
"""
import pytest
pytest.importorskip('flask')

from app import create_app
from config import Config
from database import get_user_by_email, get_user_searches


def make_client(tmp_path, monkeypatch):
    class TestConfig(Config):
        TESTING = True
        DATABASE_PATH = str(tmp_path/'test.sqlite3')
        CSRF_ENABLED = False
        SEARCH_RATE_LIMIT = 1000
    app=create_app(TestConfig)
    # Explicitly prevent network calls in integration tests.
    monkeypatch.setattr('app.search_products',lambda *args:([],[]))
    monkeypatch.setattr('app.save_price_snapshots',lambda *args:None)
    return app.test_client(), app


def test_guest_search_homepage_and_autocomplete(tmp_path,monkeypatch):
    client,app=make_client(tmp_path,monkeypatch)
    home=client.get('/')
    assert home.status_code==200
    html=home.get_data(as_text=True)
    assert 'Shop' in html or 'shop' in html
    assert 'Fashion' in html and 'Sports' in html and 'Furniture' in html
    assert 'search-clear' in html
    suggestion=client.get('/api/suggestions?q=Atomic%20Habits')
    assert suggestion.status_code==200
    payload=suggestion.get_json()
    assert any('Atomic Habits' in item['title'] for item in payload['suggestions'])
    assert all('price' not in item for item in payload['suggestions'])
    result=client.get('/compare?q=Sony%20WH-1000XM5')
    assert result.status_code==200
    page=result.get_data(as_text=True)
    assert 'search-clear' in page
    assert 'Explore similar products' in page


def test_account_opt_in_and_clear_history(tmp_path,monkeypatch):
    client,app=make_client(tmp_path,monkeypatch)
    values={'email':'shopper@example.com','password':'a-safe-password-123',
            'confirm_password':'a-safe-password-123'}
    response=client.post('/register',data=values)
    assert response.status_code==302
    with app.app_context():
        user=get_user_by_email('shopper@example.com')
        assert not user['history_enabled']
    client.get('/compare?q=Atomic%20Habits')
    with app.app_context():
        assert not get_user_searches(user['id'])  # disabled by default
    client.post('/account/preferences',data={'history_enabled':'yes'})
    client.get('/compare?q=Atomic%20Habits')
    with app.app_context():
        assert len(get_user_searches(user['id']))==1
    account=client.get('/account')
    assert account.status_code==200 and 'Atomic Habits' in account.get_data(as_text=True)
    client.post('/account/preferences',data={})
    with app.app_context():
        assert not get_user_searches(user['id'])
    exported=client.get('/account/export').get_json()
    assert exported['search_history']==[]


def test_account_admin_and_errors_are_protected(tmp_path,monkeypatch):
    client,app=make_client(tmp_path,monkeypatch)
    assert client.get('/admin').status_code==403
    assert client.get('/account').status_code==302
    assert client.get('/does-not-exist').status_code==404
    assert b'could not be found' in client.get('/does-not-exist').data
    assert client.get('/login').status_code==200
    assert client.get('/register').status_code==200
    assert client.get('/health').status_code==200
    assert client.get('/watchlist').status_code==302
    assert client.get('/api/suggestions?q=Voltas').status_code==200


def test_admin_uses_explicit_email_allowlist(tmp_path,monkeypatch):
    class AdminConfig(Config):
        TESTING=True
        DATABASE_PATH=str(tmp_path/'admin.sqlite3')
        CSRF_ENABLED=False
        ADMIN_EMAILS='reviewer@example.com'
    app=create_app(AdminConfig)
    client=app.test_client()
    client.post('/register',data={'email':'regular@example.com', 'password':'secure-passphrase-456',
                                  'confirm_password':'secure-passphrase-456'})
    assert client.get('/admin').status_code==403
    client.post('/logout')
    client.post('/register',data={'email':'reviewer@example.com','password':'secure-passphrase-789',
                                  'confirm_password':'secure-passphrase-789'})
    dashboard=client.get('/admin')
    assert dashboard.status_code==200
    assert b'Cost Quest diagnostics' in dashboard.data
    assert 'no-store' in dashboard.headers.get('Cache-Control','')
