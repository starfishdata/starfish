import pytest
import os
from pathlib import Path
from src.starfish.data_ingest.ingest import determine_parser, generate_input_data, process_file
from src.starfish.data_ingest.parsers import (
    PDFParser,
    WordDocumentParser,
    PPTParser,
    TXTParser,
    ExcelParser,
    HTMLDocumentParser,
    YouTubeParser,
    WebParser,
)
from starfish.data_factory.factory import data_factory

from starfish.data_ingest.formatter.template_format import QAGenerationPrompt
from starfish.data_ingest.splitter.token_splitter import TokenTextSplitter
from starfish.data_ingest.utils.util import async_read_file
from starfish.llm.structured_llm import StructuredLLM
import nest_asyncio

from starfish.data_factory.factory import data_factory, resume_from_checkpoint
from starfish.common.env_loader import load_env_file

nest_asyncio.apply()
load_env_file()

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "test_data"
INPUT_DIR = TEST_DATA_DIR / "input"
OUTPUT_DIR = TEST_DATA_DIR / "output"

# Test files
TEST_FILES = {
    "pdf": INPUT_DIR / "ECE_598_PV_course_notes8_v2.pdf",
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
gina_api_key = os.environ.get("JINA_AI_API_KEY", "")
gina_pdf_url = "https://arxiv.org/pdf/2303.08774.pdf"

# @pytest.fixture(autouse=True)
# def setup_teardown():
#     # Setup: Create output directory
#     OUTPUT_DIR.mkdir(exist_ok=True)
#     yield
#     # Teardown: Clean up output files
#     for file in OUTPUT_DIR.iterdir():
#         file.unlink()


@pytest.mark.skip()
def test_determine_parser_file_types():
    """Test determine_parser with different file types"""
    # Test supported file types
    assert isinstance(determine_parser(str(TEST_FILES["pdf"])), PDFParser)
    # assert isinstance(determine_parser(str(TEST_FILES["docx"])), WordDocumentParser)
    # assert isinstance(determine_parser(str(TEST_FILES["pptx"])), PPTParser)
    # assert isinstance(determine_parser(str(TEST_FILES["txt"])), TXTParser)
    # assert isinstance(determine_parser(str(TEST_FILES["xlsx"])), ExcelParser)
    # assert isinstance(determine_parser(str(TEST_FILES["html"])), HTMLDocumentParser)

    # Test unsupported file type
    with pytest.raises(ValueError):
        determine_parser(str(INPUT_DIR / "test.unsupported"))


@pytest.mark.skip()
def test_process_file():
    process_file(str(TEST_FILES["pdf"]), OUTPUT_DIR)
    # parser = determine_parser(str(TEST_FILES["pdf"]))
    # parser.parse(str(TEST_FILES["pdf"]))


@pytest.mark.skip(reason="not support UnstructuredParser to avoid too many package dependencies")
def test_unstructured_parser():
    """Test UnstructuredParser with a PDF file"""
    parser = UnstructuredParser()
    content = parser.parse(str(TEST_FILES["pdf"]))
    assert content is not None
    assert len(content) > 0  # Ensure content was extracted
    assert isinstance(content, str)  # Verify content is a string


@pytest.mark.asyncio
@pytest.mark.skip()
async def test_process_file_gina_ai():
    gina_ai_parser = WebParser(gina_api_key)
    content = await gina_ai_parser.parse_async(gina_pdf_url)
    gina_ai_parser.save(content=content, output_path=OUTPUT_DIR / "gina_ai.txt")


@pytest.mark.asyncio
@pytest.mark.skip()
async def test_ingest_input_data():
    @data_factory(max_concurrency=10)
    async def test_ingest_pdf(prompt_msg: str):
        structured_llm = StructuredLLM(
            model_name="openai/gpt-4o-mini",
            prompt="{{prompt_msg}}",
            output_schema=[{"name": "question", "type": "str"}, {"name": "answer", "type": "str"}],
            model_kwargs={"temperature": 0.7},
        )
        output = await structured_llm.run(prompt_msg=prompt_msg)
        return output.data

    content = await async_read_file(file_path=OUTPUT_DIR / "gina_ai.txt")
    all_messages = generate_input_data(content, TokenTextSplitter(), QAGenerationPrompt())

    result = await test_ingest_pdf.run(prompt_msg=all_messages)
    assert len(result) == 4


@pytest.mark.asyncio
async def test_tiktoken_spiter():
    content = await async_read_file(file_path=OUTPUT_DIR / "gina_ai.txt")
    all_messages = TokenTextSplitter().split_text(content)

    assert len(all_messages) == 195


def test_determine_parser_urls():
    """Test determine_parser with different URL types"""
    # Test YouTube URL
    assert isinstance(determine_parser(TEST_URLS["youtube"]), YouTubeParser)

    # Test HTML URL
    assert isinstance(determine_parser(TEST_URLS["html"]), HTMLDocumentParser)


@pytest.mark.skip()
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


@pytest.mark.skip()
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


@pytest.mark.skip()
def test_process_file_output_dir_creation():
    """Test process_file creates output directory if it doesn't exist"""
    new_output_dir = OUTPUT_DIR / "new_dir"
    output_path = process_file(str(TEST_FILES["txt"]), str(new_output_dir))
    assert os.path.exists(new_output_dir)
    assert os.path.exists(output_path)
