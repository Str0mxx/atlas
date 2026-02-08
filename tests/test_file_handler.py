"""FileHandler unit testleri.

CSV, Excel ve PDF dosya uretimi davranislari test edilir.
"""

import csv
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.tools.file_handler import FileHandler, FileResult


# === Fixture'lar ===


@pytest.fixture
def handler(tmp_path) -> FileHandler:
    """Gecici dizinli FileHandler."""
    return FileHandler(output_dir=str(tmp_path))


@pytest.fixture
def mock_openpyxl_available(monkeypatch):
    """openpyxl mock'u sys.modules'a ekler ve _OPENPYXL_AVAILABLE'i True yapar."""

    class MockWorksheet:
        """Basit worksheet mock'u."""

        def __init__(self, title: str = "Sheet1") -> None:
            self.title = title
            self._cells: dict = {}
            self.column_dimensions = MagicMock()
            self.columns: list = []

        def cell(self, row: int = 1, column: int = 1, value: object = None) -> MagicMock:
            """Hucre olusturur."""
            mock_cell = MagicMock()
            mock_cell.value = value
            mock_cell.column_letter = chr(64 + column)
            self._cells[(row, column)] = mock_cell
            return mock_cell

    class MockWorkbook:
        """Basit workbook mock'u — save ile gercek dosya yazar."""

        def __init__(self) -> None:
            self._active = MockWorksheet()
            self._sheets: list = [self._active]

        @property
        def active(self) -> MockWorksheet:
            return self._active

        def create_sheet(self, title: str = "Sheet") -> MockWorksheet:
            ws = MockWorksheet(title=title)
            self._sheets.append(ws)
            return ws

        def remove(self, ws: object) -> None:
            self._sheets = [s for s in self._sheets if s is not ws]

        def save(self, path: str) -> None:
            Path(path).write_bytes(b"MOCK_XLSX_CONTENT")

    mock_mod = MagicMock()
    mock_mod.Workbook = MockWorkbook
    mock_mod.utils.get_column_letter = lambda x: chr(64 + x)

    mock_styles = MagicMock()

    monkeypatch.setitem(sys.modules, "openpyxl", mock_mod)
    monkeypatch.setitem(sys.modules, "openpyxl.styles", mock_styles)
    monkeypatch.setitem(sys.modules, "openpyxl.utils", mock_mod.utils)
    monkeypatch.setattr("app.tools.file_handler._OPENPYXL_AVAILABLE", True)

    return mock_mod


@pytest.fixture
def mock_reportlab_available(monkeypatch):
    """reportlab mock'u sys.modules'a ekler ve _REPORTLAB_AVAILABLE'i True yapar."""

    class MockCanvas:
        """Basit canvas mock'u — save ile gercek dosya yazar."""

        def __init__(self, path: str, pagesize: tuple | None = None) -> None:
            self._path = path
            self._page = 1

        def setFont(self, name: str, size: float) -> None:
            pass

        def drawString(self, x: float, y: float, text: str) -> None:
            pass

        def drawCentredString(self, x: float, y: float, text: str) -> None:
            pass

        def setLineWidth(self, w: float) -> None:
            pass

        def line(self, x1: float, y1: float, x2: float, y2: float) -> None:
            pass

        def showPage(self) -> None:
            self._page += 1

        def getPageNumber(self) -> int:
            return self._page

        def save(self) -> None:
            Path(self._path).write_bytes(b"MOCK_PDF_CONTENT")

    mock_pagesizes = MagicMock()
    mock_pagesizes.A4 = (595.276, 841.89)
    mock_units = MagicMock()
    mock_units.cm = 28.346
    mock_canvas_mod = MagicMock()
    mock_canvas_mod.Canvas = MockCanvas

    # Parent moduller — alt modulleri attribute olarak bagla
    # (Python import sistemi hasattr ile kontrol eder)
    mock_lib = MagicMock()
    mock_lib.pagesizes = mock_pagesizes
    mock_lib.units = mock_units
    mock_pdfgen = MagicMock()
    mock_pdfgen.canvas = mock_canvas_mod
    mock_reportlab = MagicMock()
    mock_reportlab.lib = mock_lib
    mock_reportlab.pdfgen = mock_pdfgen

    monkeypatch.setitem(sys.modules, "reportlab", mock_reportlab)
    monkeypatch.setitem(sys.modules, "reportlab.lib", mock_lib)
    monkeypatch.setitem(sys.modules, "reportlab.lib.pagesizes", mock_pagesizes)
    monkeypatch.setitem(sys.modules, "reportlab.lib.units", mock_units)
    monkeypatch.setitem(sys.modules, "reportlab.pdfgen", mock_pdfgen)
    monkeypatch.setitem(sys.modules, "reportlab.pdfgen.canvas", mock_canvas_mod)
    monkeypatch.setattr("app.tools.file_handler._REPORTLAB_AVAILABLE", True)

    return mock_canvas_mod


# === Init testleri ===


class TestFileHandlerInit:
    """FileHandler baslatma testleri."""

    def test_default_output_dir(self) -> None:
        """Varsayilan cikti dizini."""
        handler = FileHandler()
        assert handler.output_dir == "output"

    def test_custom_output_dir(self, tmp_path) -> None:
        """Ozel cikti dizini."""
        handler = FileHandler(output_dir=str(tmp_path / "custom"))
        assert "custom" in handler.output_dir


# === CSV testleri ===


class TestCreateCsv:
    """CSV olusturma testleri."""

    def test_create_csv_basic(self, handler, tmp_path) -> None:
        """Temel CSV olusturma."""
        data = [
            ["Fatih", "Istanbul", 100],
            ["Ali", "Ankara", 200],
        ]

        result = handler.create_csv(data, filename="test.csv")

        assert result.success is True
        assert result.file_type == "csv"
        assert result.file_size > 0
        assert os.path.exists(result.file_path)

        # Icerigi dogrula
        with open(result.file_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert rows[0] == ["Fatih", "Istanbul", "100"]

    def test_create_csv_with_headers(self, handler) -> None:
        """Header'li CSV olusturma."""
        data = [["A", 1], ["B", 2]]
        headers = ["Ad", "Deger"]

        result = handler.create_csv(data, filename="headers.csv", headers=headers)

        assert result.success is True

        with open(result.file_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert rows[0] == ["Ad", "Deger"]
        assert len(rows) == 3

    def test_create_csv_empty_data(self, handler) -> None:
        """Bos veri ile CSV."""
        result = handler.create_csv([], filename="empty.csv")

        assert result.success is True
        assert os.path.exists(result.file_path)

    def test_create_csv_creates_output_dir(self, tmp_path) -> None:
        """Cikti dizini yoksa olusturulur."""
        nested_dir = str(tmp_path / "a" / "b" / "c")
        handler = FileHandler(output_dir=nested_dir)

        result = handler.create_csv([["test"]], filename="nested.csv")

        assert result.success is True
        assert os.path.exists(nested_dir)

    def test_create_csv_unicode(self, handler) -> None:
        """Unicode karakterli CSV."""
        data = [["Turk lirasi", "₺100"], ["Euro", "€50"]]

        result = handler.create_csv(data, filename="unicode.csv")

        assert result.success is True
        with open(result.file_path, encoding="utf-8") as f:
            content = f.read()
        assert "₺100" in content


# === Excel testleri ===


class TestCreateExcel:
    """Excel olusturma testleri."""

    def test_create_excel_basic(
        self, handler, mock_openpyxl_available,
    ) -> None:
        """Temel Excel olusturma."""
        data = [["Fatih", 100], ["Ali", 200]]
        headers = ["Ad", "Deger"]

        result = handler.create_excel(
            data, filename="test.xlsx", headers=headers,
        )

        assert result.success is True
        assert result.file_type == "xlsx"
        assert result.file_size > 0
        assert os.path.exists(result.file_path)

    def test_create_excel_no_headers(
        self, handler, mock_openpyxl_available,
    ) -> None:
        """Header'siz Excel olusturma."""
        data = [["A", 1], ["B", 2]]

        result = handler.create_excel(data, filename="no_headers.xlsx")

        assert result.success is True

    def test_create_excel_custom_sheet_name(
        self, handler, mock_openpyxl_available,
    ) -> None:
        """Ozel sayfa adli Excel."""
        data = [["test"]]

        result = handler.create_excel(
            data, filename="custom_sheet.xlsx", sheet_name="Veriler",
        )

        assert result.success is True

    def test_create_excel_with_column_widths(
        self, handler, mock_openpyxl_available,
    ) -> None:
        """Ozel sutun genislikli Excel."""
        data = [["Short", "A very long column value"]]
        headers = ["Kisa", "Uzun"]

        result = handler.create_excel(
            data,
            filename="widths.xlsx",
            headers=headers,
            column_widths=[10, 30],
        )

        assert result.success is True

    @patch("app.tools.file_handler._OPENPYXL_AVAILABLE", False)
    def test_create_excel_not_available(self, handler) -> None:
        """openpyxl yoksa RuntimeError."""
        with pytest.raises(RuntimeError, match="openpyxl"):
            handler.create_excel([["data"]], filename="fail.xlsx")


# === PDF testleri ===


class TestCreatePdf:
    """PDF olusturma testleri."""

    def test_create_pdf_basic(
        self, handler, mock_reportlab_available,
    ) -> None:
        """Temel PDF olusturma."""
        content = [
            "Birinci satir",
            "Ikinci satir",
            "Ucuncu satir",
        ]

        result = handler.create_pdf(
            title="Test Rapor",
            content_lines=content,
            filename="test.pdf",
        )

        assert result.success is True
        assert result.file_type == "pdf"
        assert result.file_size > 0
        assert os.path.exists(result.file_path)

    def test_create_pdf_custom_author(
        self, handler, mock_reportlab_available,
    ) -> None:
        """Ozel yazarli PDF."""
        result = handler.create_pdf(
            title="Rapor",
            content_lines=["Icerik"],
            filename="author.pdf",
            author="Fatih",
        )

        assert result.success is True

    def test_create_pdf_empty_content(
        self, handler, mock_reportlab_available,
    ) -> None:
        """Bos icerikli PDF."""
        result = handler.create_pdf(
            title="Bos Rapor",
            content_lines=[],
            filename="empty.pdf",
        )

        assert result.success is True

    def test_create_pdf_long_content(
        self, handler, mock_reportlab_available,
    ) -> None:
        """Uzun icerikli PDF (sayfa gecisi)."""
        content = [f"Satir {i}" for i in range(100)]

        result = handler.create_pdf(
            title="Uzun Rapor",
            content_lines=content,
            filename="long.pdf",
        )

        assert result.success is True
        assert result.file_size > 0

    @patch("app.tools.file_handler._REPORTLAB_AVAILABLE", False)
    def test_create_pdf_not_available(self, handler) -> None:
        """reportlab yoksa RuntimeError."""
        with pytest.raises(RuntimeError, match="reportlab"):
            handler.create_pdf(
                title="Fail",
                content_lines=["test"],
                filename="fail.pdf",
            )


# === CreateReport testleri ===


class TestCreateReport:
    """Rapor olusturma testleri."""

    def test_create_report_xlsx(
        self, handler, mock_openpyxl_available,
    ) -> None:
        """Excel rapor olusturma."""
        sections = [
            {
                "title": "Kampanyalar",
                "headers": ["Ad", "Harcama", "ROAS"],
                "data": [
                    ["Kampanya A", 100, 3.5],
                    ["Kampanya B", 200, 2.1],
                ],
            },
            {
                "title": "Kelimeler",
                "headers": ["Kelime", "CTR"],
                "data": [
                    ["sac ekimi", 4.2],
                ],
            },
        ]

        result = handler.create_report(
            title="Marketing Raporu",
            sections=sections,
            filename="marketing.xlsx",
            file_type="xlsx",
        )

        assert result.success is True
        assert result.file_type == "xlsx"

    def test_create_report_pdf(
        self, handler, mock_reportlab_available,
    ) -> None:
        """PDF rapor olusturma."""
        sections = [
            {
                "title": "Ozet",
                "headers": ["Metrik", "Deger"],
                "data": [
                    ["Toplam Harcama", "₺1500"],
                    ["ROAS", "3.2"],
                ],
            },
        ]

        result = handler.create_report(
            title="Performans Raporu",
            sections=sections,
            filename="performans.pdf",
            file_type="pdf",
        )

        assert result.success is True
        assert result.file_type == "pdf"

    def test_create_report_auto_filename(
        self, handler, mock_openpyxl_available,
    ) -> None:
        """Otomatik dosya adi."""
        sections = [{"title": "Test", "data": [["a", "b"]]}]

        result = handler.create_report(
            title="Auto",
            sections=sections,
        )

        assert result.success is True
        assert "rapor_" in result.file_path

    @patch("app.tools.file_handler._OPENPYXL_AVAILABLE", False)
    def test_create_report_xlsx_not_available(self, handler) -> None:
        """Excel rapor, openpyxl yoksa RuntimeError."""
        with pytest.raises(RuntimeError, match="openpyxl"):
            handler.create_report(
                title="Fail",
                sections=[{"title": "T", "data": []}],
                file_type="xlsx",
            )


# === FileResult modeli testleri ===


class TestFileResult:
    """FileResult model testleri."""

    def test_default_values(self) -> None:
        """Varsayilan degerler."""
        result = FileResult()
        assert result.file_path == ""
        assert result.success is True
        assert result.error == ""

    def test_error_result(self) -> None:
        """Hata iceren sonuc."""
        result = FileResult(
            file_path="/tmp/fail.csv",
            file_type="csv",
            success=False,
            error="Permission denied",
        )
        assert result.success is False
        assert result.error == "Permission denied"
