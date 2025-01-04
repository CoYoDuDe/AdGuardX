import gzip
from io import BytesIO

def gzip_response(content):
    """Komprimiert den Inhalt mit Gzip."""
    buffer = BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb") as gz:
        gz.write(content)
    return buffer.getvalue()
