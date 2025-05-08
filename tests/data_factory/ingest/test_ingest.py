import pytest
import os
from pathlib import Path
from src.starfish.data_factory.data_ingest.ingest import determine_parser, process_file
from src.starfish.data_factory.data_ingest.parsers import PDFParser, WordDocumentParser, PPTParser, TXTParser, ExcelParser, HTMLDocumentParser, YouTubeParser

# Test data paths
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
INPUT_DIR = TEST_DATA_DIR / "input"
OUTPUT_DIR = TEST_DATA_DIR / "output"

# Test files
TEST_FILES = {
    "pdf": INPUT_DIR / "test.pdf",
    "docx": INPUT_DIR / "test.docx",
    "pptx": INPUT_DIR / "test.pptx",
    "txt": INPUT_DIR / "test.txt",
    "xlsx": INPUT_DIR / "test.xlsx",
    "html": INPUT_DIR / "test.html",
}

# Test URLs
TEST_URLS = {
    "youtube": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "html": "https://example.com",
}


@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    yield
    # Teardown: Clean up output files
    for file in OUTPUT_DIR.iterdir():
        file.unlink()


# @pytest.mark.asyncio
async def test_determine_parser_file_types():
    """Test determine_parser with different file types"""
    # Test supported file types
    assert isinstance(determine_parser(str(TEST_FILES["pdf"]), {}), PDFParser)
    assert isinstance(determine_parser(str(TEST_FILES["docx"]), {}), WordDocumentParser)
    assert isinstance(determine_parser(str(TEST_FILES["pptx"]), {}), PPTParser)
    assert isinstance(determine_parser(str(TEST_FILES["txt"]), {}), TXTParser)
    assert isinstance(determine_parser(str(TEST_FILES["xlsx"]), {}), ExcelParser)
    assert isinstance(determine_parser(str(TEST_FILES["html"]), {}), HTMLDocumentParser)

    # Test unsupported file type
    with pytest.raises(ValueError):
        determine_parser(str(INPUT_DIR / "test.unsupported"), {})


def test_determine_parser_urls():
    """Test determine_parser with different URL types"""
    # Test YouTube URL
    assert isinstance(determine_parser(TEST_URLS["youtube"], {}), YouTubeParser)

    # Test HTML URL
    assert isinstance(determine_parser(TEST_URLS["html"], {}), HTMLDocumentParser)


def test_process_file_output():
    """Test process_file creates correct output files"""
    # Test with PDF file
    output_path = process_file(str(TEST_FILES["pdf"]), str(OUTPUT_DIR))
    assert os.path.exists(output_path)
    assert output_path.endswith("test.txt")

    # Test with custom output name
    custom_name = "custom_output.txt"
    output_path = process_file(str(TEST_FILES["docx"]), str(OUTPUT_DIR), custom_name)
    assert os.path.exists(output_path)
    assert output_path.endswith(custom_name)


def test_process_file_urls():
    """Test process_file with URLs"""
    # Test YouTube URL
    output_path = process_file(TEST_URLS["youtube"], str(OUTPUT_DIR))
    assert os.path.exists(output_path)
    assert "youtube_dQw4w9WgXcQ.txt" in output_path

    # Test HTML URL
    output_path = process_file(TEST_URLS["html"], str(OUTPUT_DIR))
    assert os.path.exists(output_path)
    assert "example_com.txt" in output_path


def test_process_file_nonexistent_file():
    """Test process_file with non-existent file"""
    with pytest.raises(FileNotFoundError):
        process_file(str(INPUT_DIR / "nonexistent.file"), str(OUTPUT_DIR))


def test_process_file_output_dir_creation():
    """Test process_file creates output directory if it doesn't exist"""
    new_output_dir = OUTPUT_DIR / "new_dir"
    output_path = process_file(str(TEST_FILES["txt"]), str(new_output_dir))
    assert os.path.exists(new_output_dir)
    assert os.path.exists(output_path)
