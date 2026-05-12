import pytest
import requests
import time
from unittest.mock import patch, MagicMock
from backend.services.naver_theme.crawler import _get_session, fetch_theme_list_page, fetch_theme_detail_page


@pytest.mark.unit
def test_session_singleton_creation():
    """_get_session() creates a Session on first call."""
    import backend.services.naver_theme.crawler as crawler_module
    crawler_module._session = None

    session = _get_session()
    assert isinstance(session, requests.Session)


@pytest.mark.unit
def test_session_singleton_reuse():
    """_get_session() reuses the same Session on subsequent calls."""
    import backend.services.naver_theme.crawler as crawler_module
    crawler_module._session = None

    session1 = _get_session()
    session2 = _get_session()
    assert session1 is session2


@pytest.mark.unit
def test_session_has_retry_adapter():
    """Session has HTTPAdapter with Retry configuration mounted."""
    import backend.services.naver_theme.crawler as crawler_module
    crawler_module._session = None

    session = _get_session()
    https_adapter = session.get_adapter("https://")
    assert hasattr(https_adapter, 'max_retries')


@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.requests.Session.get')
def test_fetch_theme_list_page_returns_html(mock_get):
    """fetch_theme_list_page() returns HTML string."""
    mock_response = MagicMock()
    mock_response.text = "<html><body>Theme List</body></html>"
    mock_get.return_value = mock_response

    html = fetch_theme_list_page(1)
    assert isinstance(html, str)
    assert "Theme List" in html


@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.requests.Session.get')
def test_fetch_theme_list_page_calls_correct_url(mock_get):
    """fetch_theme_list_page() calls the correct URL with page parameter."""
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_get.return_value = mock_response

    fetch_theme_list_page(3)

    called_url = mock_get.call_args[0][0]
    assert "page=3" in called_url or "=3" in called_url


@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.requests.Session.get')
def test_fetch_theme_detail_page_returns_html(mock_get):
    """fetch_theme_detail_page() returns HTML string."""
    mock_response = MagicMock()
    mock_response.text = "<html><body>Theme Detail</body></html>"
    mock_get.return_value = mock_response

    html = fetch_theme_detail_page(178)
    assert isinstance(html, str)
    assert "Theme Detail" in html


@pytest.mark.unit
@patch('backend.services.naver_theme.crawler.requests.Session.get')
def test_fetch_theme_detail_page_calls_correct_url(mock_get):
    """fetch_theme_detail_page() calls the correct URL with theme_id parameter."""
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_get.return_value = mock_response

    fetch_theme_detail_page(178)

    called_url = mock_get.call_args[0][0]
    assert "no=178" in called_url or "178" in called_url


@pytest.mark.slow
@patch('backend.services.naver_theme.crawler.requests.Session.get')
@patch('backend.services.naver_theme.crawler.time.sleep')
def test_fetch_includes_crawl_delay(mock_sleep, mock_get):
    """Fetch functions call time.sleep(CRAWL_DELAY)."""
    mock_response = MagicMock()
    mock_response.text = "<html></html>"
    mock_get.return_value = mock_response

    fetch_theme_list_page(1)

    # Should have called sleep(0.7)
    mock_sleep.assert_called()
    # Get the actual sleep duration
    sleep_call_args = mock_sleep.call_args[0][0]
    assert sleep_call_args == 0.7
