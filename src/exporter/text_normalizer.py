from __future__ import annotations


class TextNormalizer:
    """
    Converts PDF-specific glyphs into reliable Unicode text
    before exporting to Word.
    """

    BULLET_REPLACEMENTS: dict[str, str] = {
        "\uf0b7": "\u2022",  # Wingdings private-use bullet
        "\uf0a7": "\u25aa",  # Wingdings square bullet
        "\uf0d8": "\u25ba",  # Wingdings right arrow
        "\u2023": "\u2022",  # Triangular bullet
        "\u2043": "\u2022",  # Hyphen bullet
        "\u2219": "\u2022",  # Bullet operator
        "\u25cf": "\u2022",  # Black circle
    }

    BULLET_CHARACTERS: set[str] = {
        "\u2022",  # •
        "\u25e6",  # ◦
        "\u25aa",  # ▪
        "\u25ab",  # ▫
        "\u25a0",  # ■
        "\u25a1",  # □
        "\u25cb",  # ○
        "\u25cf",  # ●
        "\u2023",  # ‣
    }

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize PDF-specific characters into portable
        Unicode equivalents.
        """

        if not text:
            return ""

        normalized = text

        for source, replacement in (
            TextNormalizer.BULLET_REPLACEMENTS.items()
        ):
            normalized = normalized.replace(
                source,
                replacement,
            )

        return normalized

    @staticmethod
    def contains_bullet(text: str) -> bool:
        """
        Return True when text contains a known bullet glyph.
        """

        normalized = TextNormalizer.normalize(text)

        return any(
            character in TextNormalizer.BULLET_CHARACTERS
            for character in normalized
        )

    @staticmethod
    def is_bullet_only(text: str) -> bool:
        """
        Return True when the visible span contains only a
        bullet and optional whitespace.
        """

        normalized = TextNormalizer.normalize(
            text
        ).strip()

        return (
            len(normalized) == 1
            and normalized
            in TextNormalizer.BULLET_CHARACTERS
        )