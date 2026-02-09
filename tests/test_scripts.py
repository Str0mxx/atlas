"""Veritabani kurulum ve seed scriptleri unit testleri."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.seed_data import seed_all, seed_notifications, seed_tasks
from scripts.setup_db import check_connection, cli, run_migrations, run_seed


class TestSetupDbCheck:
    """check_connection fonksiyonu testleri."""

    @pytest.mark.asyncio
    async def test_check_connection_success(self) -> None:
        """Basarili baglanti durumunu dogrular."""
        with (
            patch("scripts.setup_db.init_db", new_callable=AsyncMock) as mock_init,
            patch("scripts.setup_db.close_db", new_callable=AsyncMock) as mock_close,
        ):
            result = await check_connection()
            assert result is True
            mock_init.assert_awaited_once()
            mock_close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_connection_failure(self) -> None:
        """Baglanti hatasi durumunda False donmesini dogrular."""
        with patch(
            "scripts.setup_db.init_db",
            new_callable=AsyncMock,
            side_effect=ConnectionError("DB baglanti hatasi"),
        ):
            result = await check_connection()
            assert result is False


class TestSetupDbMigrate:
    """run_migrations fonksiyonu testleri."""

    @pytest.mark.asyncio
    async def test_run_migrations(self) -> None:
        """Tablo olusturma akisinin dogru calismasini dogrular."""
        with (
            patch("scripts.setup_db.init_db", new_callable=AsyncMock) as mock_init,
            patch("scripts.setup_db.create_tables", new_callable=AsyncMock) as mock_create,
            patch("scripts.setup_db.close_db", new_callable=AsyncMock) as mock_close,
        ):
            await run_migrations()
            mock_init.assert_awaited_once()
            mock_create.assert_awaited_once()
            mock_close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_migrations_closes_on_error(self) -> None:
        """Hata durumunda close_db'nin yine de cagrilmasini dogrular."""
        with (
            patch("scripts.setup_db.init_db", new_callable=AsyncMock),
            patch(
                "scripts.setup_db.create_tables",
                new_callable=AsyncMock,
                side_effect=RuntimeError("create hata"),
            ),
            patch("scripts.setup_db.close_db", new_callable=AsyncMock) as mock_close,
        ):
            with pytest.raises(RuntimeError, match="create hata"):
                await run_migrations()
            mock_close.assert_awaited_once()


class TestSetupDbSeed:
    """run_seed fonksiyonu testleri."""

    @pytest.mark.asyncio
    async def test_run_seed(self) -> None:
        """seed_all fonksiyonunun cagrilmasini dogrular.

        run_seed icerisinde lazy import yapildigi icin
        scripts.seed_data.seed_all patch noktasi kullanilir.
        """
        with patch(
            "scripts.seed_data.seed_all", new_callable=AsyncMock
        ) as mock_seed_all:
            await run_seed()
            mock_seed_all.assert_awaited_once()


class TestSeedTasks:
    """seed_tasks fonksiyonu testleri."""

    @pytest.mark.asyncio
    async def test_seed_tasks_creates_records(self) -> None:
        """5 gorev kaydinin olusturulmasini dogrular."""
        mock_session = MagicMock()
        count = await seed_tasks(mock_session)
        assert count == 5
        assert mock_session.add.call_count == 5

    @pytest.mark.asyncio
    async def test_seed_tasks_returns_count(self) -> None:
        """Donen sayinin eklenen kayit sayisiyla eslesmesini dogrular."""
        mock_session = MagicMock()
        count = await seed_tasks(mock_session)
        assert isinstance(count, int)
        assert count > 0


class TestSeedNotifications:
    """seed_notifications fonksiyonu testleri."""

    @pytest.mark.asyncio
    async def test_seed_notifications_creates_records(self) -> None:
        """5 bildirim kaydinin olusturulmasini dogrular."""
        mock_session = MagicMock()
        count = await seed_notifications(mock_session)
        assert count == 5
        assert mock_session.add.call_count == 5

    @pytest.mark.asyncio
    async def test_seed_notifications_returns_count(self) -> None:
        """Donen sayinin eklenen kayit sayisiyla eslesmesini dogrular."""
        mock_session = MagicMock()
        count = await seed_notifications(mock_session)
        assert isinstance(count, int)
        assert count > 0


class TestCli:
    """CLI arguman ayristirma testleri."""

    @patch("scripts.setup_db.asyncio.run")
    @patch("sys.argv", ["setup_db", "--check"])
    def test_cli_check(self, mock_run: MagicMock) -> None:
        """--check argumaninin dogru islenmesini dogrular."""
        cli()
        mock_run.assert_called_once()

    @patch("scripts.setup_db.asyncio.run")
    @patch("sys.argv", ["setup_db", "--migrate"])
    def test_cli_migrate(self, mock_run: MagicMock) -> None:
        """--migrate argumaninin dogru islenmesini dogrular."""
        cli()
        mock_run.assert_called_once()

    @patch("scripts.setup_db.asyncio.run")
    @patch("sys.argv", ["setup_db", "--seed"])
    def test_cli_seed(self, mock_run: MagicMock) -> None:
        """--seed argumaninin dogru islenmesini dogrular."""
        cli()
        mock_run.assert_called_once()

    @patch("scripts.setup_db.asyncio.run")
    @patch("sys.argv", ["setup_db", "--all"])
    def test_cli_all(self, mock_run: MagicMock) -> None:
        """--all argumaninin dogru islenmesini dogrular."""
        cli()
        mock_run.assert_called_once()
