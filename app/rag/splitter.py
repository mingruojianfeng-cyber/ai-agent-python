from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    index: int
    content: str
    start_char: int
    end_char: int


class TextSplitter:
    """按字符切分文本；优先在段落或句子边界处分割。"""

    def __init__(
        self,
        max_chunk_chars: int = 1000,
        overlap_chars: int = 150,
    ) -> None:
        if max_chunk_chars < 1:
            raise ValueError("max_chunk_chars must be positive.")
        if overlap_chars < 0 or overlap_chars >= max_chunk_chars:
            raise ValueError("overlap_chars must be between 0 and max_chunk_chars.")

        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def split(self, text: str) -> list[TextChunk]:
        normalized_text = text.strip()
        if not normalized_text:
            return []

        chunks: list[TextChunk] = []
        start = 0
        index = 0

        while start < len(normalized_text):
            candidate_end = min(
                start + self.max_chunk_chars,
                len(normalized_text),
            )
            end = self._find_boundary(
                text=normalized_text,
                start=start,
                candidate_end=candidate_end,
            )

            content = normalized_text[start:end].strip()
            if content:
                chunks.append(
                    TextChunk(
                        index=index,
                        content=content,
                        start_char=start,
                        end_char=end,
                    )
                )
                index += 1

            if end >= len(normalized_text):
                break

            start = max(end - self.overlap_chars, start + 1)

        return chunks

    @staticmethod
    def _find_boundary(text: str, start: int, candidate_end: int) -> int:
        if candidate_end == len(text):
            return candidate_end

        search_start = max(start + 1, candidate_end - 200)

        for separator in ("\n\n", "\n", "。", "！", "？", "；", " "):
            position = text.rfind(separator, search_start, candidate_end)
            if position != -1:
                return position + len(separator)

        return candidate_end