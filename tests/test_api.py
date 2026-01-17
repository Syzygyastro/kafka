"""Tests for the API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for the health endpoint."""

    def test_health_check(self, client):
        """Test health check returns OK."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "components" in data


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "docs" in data


class TestScrapeEndpoint:
    """Tests for the scrape endpoint."""

    def test_scrape_simple(self, client):
        """Test simple scraping."""
        response = client.post(
            "/api/v1/scrape",
            json={
                "url": "https://httpbin.org/html",
                "strategy": "simple",
                "output_format": "html",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["content"] is not None

    def test_scrape_with_selectors(self, client):
        """Test scraping with CSS selectors."""
        response = client.post(
            "/api/v1/scrape",
            json={
                "url": "https://httpbin.org/html",
                "strategy": "simple",
                "selectors": {"heading": "h1"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["extracted_data"] is not None

    def test_scrape_invalid_url(self, client):
        """Test scraping with invalid URL."""
        response = client.post(
            "/api/v1/scrape",
            json={
                "url": "not-a-valid-url",
                "strategy": "simple",
            },
        )

        # Should return validation error
        assert response.status_code == 422


class TestStatsEndpoint:
    """Tests for the stats endpoint."""

    def test_get_stats(self, client):
        """Test getting statistics."""
        response = client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "uptime_seconds" in data


class TestProxyStatsEndpoint:
    """Tests for the proxy stats endpoint."""

    def test_get_proxy_stats(self, client):
        """Test getting proxy statistics."""
        response = client.get("/api/v1/proxy/stats")

        assert response.status_code == 200
        data = response.json()
        assert "proxies" in data
        assert "total_active" in data
