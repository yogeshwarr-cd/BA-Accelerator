import re
from typing import List

class TextNormalizer:
    """
    Cleans, chunk-splits, and analyzes raw text strings.
    """
    
    @staticmethod
    def clean(text: str) -> str:
        """
        Strips unnecessary whitespace characters, normalizes line feeds, and filters control formatting.
        """
        if not text:
            return ""
        # Replace non-breaking spaces
        text = text.replace("\u00a0", " ")
        # Normalize double space gaps
        text = re.sub(r"[ \t]+", " ", text)
        # Normalize newlines
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Estimates text language using simple keyword heuristics to avoid heavy external language dependencies.
        Returns 'en' (English), 'es' (Spanish), or 'unknown'.
        """
        cleaned = text.lower()
        # Sample common keywords
        english_words = {"the", "and", "shall", "user", "system", "requirement", "business", "actor"}
        spanish_words = {"el", "y", "usuario", "sistema", "requisito", "negocio", "actor", "para"}

        words = set(re.findall(r"\b[a-z]{2,15}\b", cleaned[:5000]))
        if not words:
            return "en"

        en_matches = len(words.intersection(english_words))
        es_matches = len(words.intersection(spanish_words))

        if en_matches > es_matches:
            return "en"
        elif es_matches > en_matches:
            return "es"
        return "en"  # default standard fallback

    @staticmethod
    def chunk(text: str, chunk_size: int = 4000, chunk_overlap: int = 400) -> List[str]:
        """
        Splits text into chunks preserving sentences or lines where possible.
        """
        cleaned = TextNormalizer.clean(text)
        if len(cleaned) <= chunk_size:
            return [cleaned]

        chunks = []
        start = 0
        text_len = len(cleaned)

        while start < text_len:
            end = start + chunk_size
            if end >= text_len:
                chunks.append(cleaned[start:])
                break
            
            # Attemp to find nearest sentence or paragraph boundary in overlap zone
            boundary = cleaned.rfind("\n", start, end)
            if boundary == -1 or boundary < (end - chunk_overlap):
                boundary = cleaned.rfind(". ", start, end)
            
            if boundary != -1 and boundary > start:
                # Add 1 to include the separator
                chunk_end = boundary + 1
            else:
                chunk_end = end

            chunks.append(cleaned[start:chunk_end].strip())
            start = chunk_end - chunk_overlap
            if start < 0:
                start = chunk_end

        return chunks

# INTEGRATION NOTE
# Language detection outputs ('en', 'es', etc.) can be appended to prompt context metadata in agents.
