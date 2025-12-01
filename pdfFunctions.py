
### Google adk specific imports
from google.adk.tools import ToolContext

### Misc. imports
from io import BytesIO
from pypdf import PdfReader
from pathlib import Path



async def get_bytes_from_artifact(
     filename: str, 
     tool_context: ToolContext
     ) -> bytes:
    """
    Loads a specific PDF from saved artifacts and returns its byte content
    Args:
        filename: Name of PDF artifact file to load
        tool_context: context object provided by ADK framework
    Returns:
        Byte content the file
    Raises:
        ValueError: If the artifact is not found or is not a PDF
        RuntimeError: For unexpected storage or other errors
    """
    try:
        pdf_artifact = await tool_context.load_artifact(filename=filename)

        if (pdf_artifact and hasattr(pdf_artifact, 'inline_data') and pdf_artifact.inline_data):
            if pdf_artifact.inline_data.mime_type == "application/pdf":
                return pdf_artifact.inline_data.data
            else:
                raise ValueError(f"'{filename}' is not a PDF.")
        else:
            raise ValueError(f"'{filename}' not found or is empty.")
        
    except ValueError as e:
        raise e
    
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred: '{e}'")



def get_text_from_bytes(
     bytes: bytes
    ) -> str:
    """
    Gets the text from the byte content of a pdf file.

    Args:
        bytes: Content to be read

    Returns:
        Text content inside the file

    Raises:
        Exception: Any exception raised by the BytesIO or PdfReader modules
    """
    try:
        pdf_bytes = BytesIO(bytes)
        reader = PdfReader(pdf_bytes)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        raise Exception(e)
    

    
async def get_pdf_text_from_artifact(filename: str, 
     tool_context: ToolContext
    ) -> dict:
    """
    This tool returns the text found in the pdf artifact with the given filename.

    Args:
        filename: The name of the file. It needs to be a .pdf file.

    Returns:
        Dictionary with status and results.

        Success: {"status": "success", "result": results of the text}

        Error: {"status": "error", "error_message": message of any exception}
    """
    try:
        pdf_bytes = await get_bytes_from_artifact(filename=filename, tool_context=tool_context)
        text = get_text_from_bytes(pdf_bytes)
        return {"status":"success", "result": text}
    except Exception as exc:
        return {"status":"error", "error_message": str(exc)}