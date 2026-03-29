import pandas as pd
from google.genai import types


async def process_document(file_bytes: bytes, mime_type: str, file_name: str):
    """
    Парсим документы для Gemini.
    PDF кидаем байтами (Gemini Flash хавает напрямую).
    Excel/CSV перегоняем в Markdown.

    Возвращает: (part_or_text, description_str)
    """
    if mime_type == 'application/pdf':
        part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        return part, f"[User sent a PDF: {file_name}]"

    if mime_type in (
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/csv',
    ):
        try:
            import io
            if mime_type == 'text/csv':
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))

            md_table = df.to_markdown(index=False)
            text = f"\n\nDOCUMENT DATA ({file_name}):\n{md_table}\n"
            return text, f"[User sent a Spreadsheet: {file_name}]"
        except Exception as e:
            error_text = f"\n\n[Error parsing spreadsheet {file_name}: {e}]\n"
            return error_text, "[User sent a broken Spreadsheet]"

    # Текстовые форматы — читаем как plain text
    if mime_type.startswith('text/'):
        try:
            text_content = file_bytes.decode('utf-8', errors='replace')
            text = f"\n\nDOCUMENT DATA ({file_name}):\n{text_content}\n"
            return text, f"[User sent a text file: {file_name}]"
        except Exception as e:
            return f"\n\n[Error reading text file {file_name}: {e}]\n", "[User sent an unreadable text file]"

    # Неизвестный тип — возвращаем пустышку, не падаем
    return None, f"[User sent an unsupported file type: {mime_type}, name: {file_name}]"
