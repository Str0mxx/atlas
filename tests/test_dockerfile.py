"""Dockerfile ve docker yapilandirma testleri."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestDockerFiles:
    """Docker dosya varlik testleri."""

    def test_dockerfile_exists(self) -> None:
        """Dockerfile mevcut olmali."""
        assert (PROJECT_ROOT / "docker" / "Dockerfile").exists()

    def test_docker_compose_exists(self) -> None:
        """docker-compose.yml mevcut olmali."""
        assert (PROJECT_ROOT / "docker-compose.yml").exists()

    def test_dockerfile_has_from(self) -> None:
        """Dockerfile FROM ifadesi icermeli."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert "FROM python:3.11" in content

    def test_dockerfile_has_workdir(self) -> None:
        """Dockerfile WORKDIR /app tanimlamali."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert "WORKDIR /app" in content

    def test_dockerfile_has_expose(self) -> None:
        """Dockerfile port 8000 acmali."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert "EXPOSE 8000" in content

    def test_dockerfile_has_healthcheck(self) -> None:
        """Dockerfile healthcheck tanimlamali."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert "HEALTHCHECK" in content

    def test_dockerfile_has_cmd(self) -> None:
        """Dockerfile uvicorn CMD icermeli."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert "uvicorn" in content
        assert "app.main:app" in content

    def test_dockerfile_non_root_user(self) -> None:
        """Dockerfile root olmayan kullanici kullanmali."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert "USER atlas" in content

    def test_dockerfile_multi_stage(self) -> None:
        """Dockerfile multi-stage build kullanmali."""
        content = (PROJECT_ROOT / "docker" / "Dockerfile").read_text()
        assert content.count("FROM ") >= 2

    def test_docker_compose_has_postgres(self) -> None:
        """docker-compose.yml PostgreSQL servisi icermeli."""
        content = (PROJECT_ROOT / "docker-compose.yml").read_text()
        assert "postgres" in content

    def test_docker_compose_has_redis(self) -> None:
        """docker-compose.yml Redis servisi icermeli."""
        content = (PROJECT_ROOT / "docker-compose.yml").read_text()
        assert "redis" in content
