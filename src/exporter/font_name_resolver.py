from __future__ import annotations

import re


class FontNameResolver:
    """
    Converts PDF/PostScript font names into font-family
    names that Microsoft Word is more likely to recognize.
    """

    FONT_ALIASES: dict[str, str] = {
        "ArialMT": "Arial",
        "Arial-BoldMT": "Arial",
        "Arial-ItalicMT": "Arial",
        "Arial-BoldItalicMT": "Arial",
        
        "Helvetica": "Arial",
        "Helvetica-Bold": "Arial",
        "Helvetica-Oblique": "Arial",
        "Helvetica-BoldOblique": "Arial",

        "HelveticaNeue": "Arial",
        "HelveticaNeue-Light": "Arial",
        "HelveticaNeue-UltraLight": "Arial",
        "HelveticaNeue-Italic": "Arial",
        "HelveticaNeue-LightItalic": "Arial",
        "HelveticaNeue-LightItali": "Arial",
        "HelveticaNeue-Bold": "Arial",
        "HelveticaNeue-BoldItalic": "Arial",
        "HelveticaNeue-Medium": "Arial",

        "Calibri": "Calibri",
        "Calibri-Bold": "Calibri",
        "Calibri-Italic": "Calibri",
        "Calibri-BoldItalic": "Calibri",

        "CenturySchoolbook": "Century Schoolbook",
        "CenturySchoolbook-Bold": "Century Schoolbook",
        "CenturySchoolbook-Italic": "Century Schoolbook",
        "CenturySchoolbook-BoldItalic": "Century Schoolbook",

        "CourierNewPSMT": "Courier New",
        "CourierNewPS-BoldMT": "Courier New",
        "CourierNewPS-ItalicMT": "Courier New",
        "CourierNewPS-BoldItalicMT": "Courier New",

        "TimesNewRomanPSMT": "Times New Roman",
        "TimesNewRomanPS-BoldMT": "Times New Roman",
        "TimesNewRomanPS-ItalicMT": "Times New Roman",
        "TimesNewRomanPS-BoldItalicMT": "Times New Roman",

        "Helvetica": "Arial",
        "Helvetica-Bold": "Arial",
        "Helvetica-Oblique": "Arial",
        "Helvetica-BoldOblique": "Arial",

        "Times-Roman": "Times New Roman",
        "Times-Bold": "Times New Roman",
        "Times-Italic": "Times New Roman",
        "Times-BoldItalic": "Times New Roman",
        
        "DMSans": "DM Sans",
        "DMSans-Regular": "DM Sans",
        "DMSans-Medium": "DM Sans",
        "DMSans-SemiBold": "DM Sans",
        "DMSans-Bold": "DM Sans",
        "DMSans-ExtraBold": "DM Sans",
        "DMSans-Italic": "DM Sans",
        "DMSans-BoldItalic": "DM Sans",
        
        "DM Sans": "DM Sans",
        "DM Sans Regular": "DM Sans",
        "DM Sans Medium": "DM Sans",
        "DM Sans Bold": "DM Sans",

        "Repo-ExtraBold": "Arial Black",
        "RepoExtraBold": "Arial Black",
        "Repo": "Arial Black",
    }

    STYLE_SUFFIXES: tuple[str, ...] = (
        "-BoldItalic",
        "-BoldOblique",
        "-Bold",
        "-Italic",
        "-Oblique",
        ",BoldItalic",
        ",Bold",
        ",Italic",
        "-ExtraBoldItalic",
        "-ExtraBold",
        "-SemiBoldItalic",
        "-SemiBold",
        "-MediumItalic",
        "-Medium",
        "-Regular",
        "-LightItalic",
        "-Light",
    )

    @staticmethod
    def resolve(pdf_font_name: str) -> str:
        """
        Resolve a PDF font name to a Word-compatible family.

        Examples:
            ABCDEF+CenturySchoolbook-Bold
                -> Century Schoolbook

            TimesNewRomanPSMT
                -> Times New Roman
        """

        if not pdf_font_name:
            return "Arial"

        cleaned_name = FontNameResolver._remove_subset_prefix(
            pdf_font_name.strip()
        )

        alias = FontNameResolver.FONT_ALIASES.get(
            cleaned_name
        )

        if alias:
            return alias

        family_name = FontNameResolver._remove_style_suffix(
            cleaned_name
        )

        alias = FontNameResolver.FONT_ALIASES.get(
            family_name
        )

        if alias:
            return alias

        return FontNameResolver._make_readable(
            family_name
        )

    @staticmethod
    def _remove_subset_prefix(
        font_name: str,
    ) -> str:
        """
        Remove embedded subset prefixes such as ABCDEF+.
        """

        return re.sub(
            r"^[A-Z]{6}\+",
            "",
            font_name,
        )

    @staticmethod
    def _remove_style_suffix(
        font_name: str,
    ) -> str:
        """
        Remove bold/italic suffixes because those properties
        are already represented separately in TextRun.
        """

        for suffix in FontNameResolver.STYLE_SUFFIXES:
            if font_name.endswith(suffix):
                return font_name[
                    : -len(suffix)
                ]

        return font_name

    @staticmethod
    def _make_readable(
        font_name: str,
    ) -> str:
        """
        Convert common PostScript naming into a readable
        family name without damaging unknown font names.
        """

        font_name = font_name.replace(
            "_",
            " ",
        )

        font_name = re.sub(
            r"(?<=[a-z])(?=[A-Z])",
            " ",
            font_name,
        )

        return font_name.strip()