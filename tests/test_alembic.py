"""Alembic migration konfigurasyonu testleri.

Veritabani baglantisi gerektirmeden Alembic yapilandirmasini dogrular.
"""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.database import Base


# Proje kok dizini
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestAlembicConfig:
    """Alembic yapilandirma testleri."""

    def test_alembic_ini_exists(self) -> None:
        assert (PROJECT_ROOT / "alembic.ini").exists()

    def test_env_py_exists(self) -> None:
        assert (PROJECT_ROOT / "alembic" / "env.py").exists()

    def test_versions_dir_exists(self) -> None:
        assert (PROJECT_ROOT / "alembic" / "versions").is_dir()

    def test_script_mako_exists(self) -> None:
        assert (PROJECT_ROOT / "alembic" / "script.py.mako").exists()


class TestAlembicMigrations:
    """Migration dosyalari testleri."""

    def test_script_directory_loads(self) -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        scripts = ScriptDirectory.from_config(cfg)
        assert scripts is not None

    def test_has_initial_migration(self) -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        scripts = ScriptDirectory.from_config(cfg)
        revisions = list(scripts.walk_revisions())
        assert len(revisions) >= 1

    def test_initial_revision_is_head(self) -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        scripts = ScriptDirectory.from_config(cfg)
        head = scripts.get_current_head()
        assert head == "b2c3d4e5f6g7"

    def test_initial_revision_has_no_parent(self) -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        scripts = ScriptDirectory.from_config(cfg)
        rev = scripts.get_revision("a1b2c3d4e5f6")
        assert rev is not None
        assert rev.down_revision is None

    def test_revision_chain_is_linear(self) -> None:
        cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        scripts = ScriptDirectory.from_config(cfg)
        heads = scripts.get_heads()
        assert len(heads) == 1, "Birden fazla head revision olmamali"


class TestModelsRegistered:
    """SQLAlchemy modellerinin Base.metadata'ya kayitli oldugunu dogrular."""

    def test_tasks_table_registered(self) -> None:
        assert "tasks" in Base.metadata.tables

    def test_agent_logs_table_registered(self) -> None:
        assert "agent_logs" in Base.metadata.tables

    def test_decisions_table_registered(self) -> None:
        assert "decisions" in Base.metadata.tables

    def test_table_count(self) -> None:
        assert len(Base.metadata.tables) >= 3
