"""Render all customer/admin templates with strict Jinja variables without Flask."""
from scripts.qa_browser_pages import render_pages


def test_all_page_states_render_to_complete_html():
    pages=render_pages()
    assert len(pages)==13
    for name,path in pages.items():
        html=open(path,encoding='utf8').read()
        assert '<html' in html and '<main>' in html and '</main>' in html,name
        assert 'cost' in html.casefold() and 'quest' in html.casefold(),name


def test_guest_search_and_account_are_optional():
    pages=render_pages()
    index=open(pages['index'],encoding='utf8').read()
    assert 'No account required' in index
    assert 'Create account' in index
    assert 'search-clear' in index
    account=open(pages['account'],encoding='utf8').read()
    assert 'Remember searches for personalized suggestions' in account
    assert 'Delete account' in account
    admin=open(pages['admin'],encoding='utf8').read()
    assert 'PROTECTED ENGINEERING VIEW' in admin
