from __future__ import annotations

from collections import Counter
from statistics import fmean

from src.models.document import Document
from src.models.document_profile import (
    DocumentProfile,
)
from src.models.page_profile import (
    ConversionMode,
    PageProfile,
    PageType,
)


class DocumentProfileAnalyzer:
    """
    Summarizes page-level profiles into one document-level
    profile.

    The document profile does not force every page to use the
    same conversion strategy. Each page keeps its own
    recommended mode.
    """

    PAGE_SIZE_ABSOLUTE_TOLERANCE = 1.0
    PAGE_SIZE_RELATIVE_TOLERANCE = 0.002

    SQUARE_PAGE_RATIO_TOLERANCE = 0.03

    @classmethod
    def analyze(
        cls,
        document: Document,
    ) -> DocumentProfile:
        """
        Build and attach a new DocumentProfile.

        A new profile is created on every call so old counts,
        warnings and confidence values cannot remain from a
        previous analysis.
        """

        profile = DocumentProfile()

        document.profile = profile

        page_profiles = [
            page.profile
            for page in document.pages
            if page.profile is not None
        ]

        profile.page_count = len(
            page_profiles
        )

        if not page_profiles:
            profile.add_warning(
                "The document contains no analyzed pages."
            )

            profile.add_reason(
                "No page profiles were available."
            )

            return profile

        cls._calculate_page_category_counts(
            profile=profile,
            page_profiles=page_profiles,
        )

        cls._calculate_feature_flags(
            profile=profile,
            page_profiles=page_profiles,
        )

        cls._calculate_page_size_information(
            profile=profile,
            page_profiles=page_profiles,
        )

        cls._calculate_type_and_mode_counts(
            profile=profile,
            pages=document.pages,
        )

        profile.dominant_page_type = (
            cls._resolve_dominant_page_type(
                profile.page_type_counts
            )
        )

        profile.recommended_mode = (
            cls._resolve_document_mode(
                profile.mode_counts
            )
        )

        profile.requires_hybrid_conversion = (
            cls._requires_hybrid_conversion(
                profile=profile,
            )
        )

        cls._calculate_confidence_scores(
            profile=profile,
            page_profiles=page_profiles,
        )

        cls._add_explanations(
            profile=profile,
        )

        return profile

    @staticmethod
    def _calculate_page_category_counts(
        profile: DocumentProfile,
        page_profiles: list[PageProfile],
    ) -> None:
        """
        Calculate document-level page category counts.
        """

        profile.scanned_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.page_type
                == PageType.SCANNED
                or page_profile.requires_ocr
            )
        )

        profile.digital_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.has_extractable_text
                and not page_profile.requires_ocr
            )
        )

        profile.mixed_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.page_type
                == PageType.MIXED
            )
        )

        profile.simple_text_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.page_type
                == PageType.SIMPLE_TEXT
            )
        )

        profile.multi_column_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.page_type
                in {
                    PageType.MULTI_COLUMN,
                    PageType.MAGAZINE,
                }
            )
        )

        profile.designed_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.page_type
                in {
                    PageType.DESIGNED_COVER,
                    PageType.MAGAZINE,
                }
            )
        )

        profile.table_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.table_count > 0
                or page_profile.page_type
                == PageType.TABLE_DOMINANT
            )
        )

        profile.chart_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.chart_count > 0
                or page_profile.page_type
                == PageType.CHART_DOMINANT
            )
        )

        profile.form_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.form_field_count > 0
                or page_profile.page_type
                == PageType.FORM
            )
        )

        profile.image_dominant_page_count = sum(
            1
            for page_profile in page_profiles
            if (
                page_profile.page_type
                in {
                    PageType.IMAGE_DOMINANT,
                    PageType.SCANNED,
                }
            )
        )

    @staticmethod
    def _calculate_feature_flags(
        profile: DocumentProfile,
        page_profiles: list[PageProfile],
    ) -> None:
        """
        Set document feature flags from all page profiles.
        """

        profile.contains_tables = any(
            page_profile.table_count > 0
            or page_profile.page_type
            == PageType.TABLE_DOMINANT
            for page_profile in page_profiles
        )

        profile.contains_charts = any(
            page_profile.chart_count > 0
            or page_profile.page_type
            == PageType.CHART_DOMINANT
            for page_profile in page_profiles
        )

        profile.contains_forms = any(
            page_profile.form_field_count > 0
            or page_profile.page_type
            == PageType.FORM
            for page_profile in page_profiles
        )

        profile.contains_scanned_pages = any(
            page_profile.requires_ocr
            or page_profile.page_type
            == PageType.SCANNED
            for page_profile in page_profiles
        )

        profile.contains_digital_pages = any(
            page_profile.has_extractable_text
            and not page_profile.requires_ocr
            for page_profile in page_profiles
        )

        profile.contains_headers = any(
            page_profile.has_header
            for page_profile in page_profiles
        )

        profile.contains_footers = any(
            page_profile.has_footer
            for page_profile in page_profiles
        )

        profile.contains_watermarks = any(
            page_profile.has_watermark
            for page_profile in page_profiles
        )

        profile.requires_ocr = any(
            page_profile.requires_ocr
            for page_profile in page_profiles
        )

    @classmethod
    def _calculate_page_size_information(
        cls,
        profile: DocumentProfile,
        page_profiles: list[PageProfile],
    ) -> None:
        """
        Detect multiple page sizes and orientations.

        Small floating-point differences are ignored. For
        example, 612.0 × 792.0 and 612.001 × 792.002 are
        treated as the same page size.
        """

        valid_sizes = [
            (
                page_profile.page_width,
                page_profile.page_height,
            )
            for page_profile in page_profiles
            if (
                page_profile.page_width > 0.0
                and page_profile.page_height > 0.0
            )
        ]

        size_groups = cls._group_page_sizes(
            valid_sizes
        )

        profile.contains_multiple_page_sizes = (
            len(size_groups) > 1
        )

        orientations = {
            cls._resolve_orientation(
                width=width,
                height=height,
            )
            for width, height in valid_sizes
        }

        profile.contains_multiple_orientations = (
            len(orientations) > 1
        )

    @staticmethod
    def _calculate_type_and_mode_counts(
        profile: DocumentProfile,
        pages,
    ) -> None:
        """
        Store page-type and resolved conversion-mode counts.
    
        The final ConversionPolicy mode is preferred. The
        PageProfile recommendation is used as a fallback.
        """
    
        analyzed_pages = [
            page
            for page in pages
            if getattr(
                page,
                "profile",
                None,
            ) is not None
        ]
    
        page_type_counter = Counter(
            page.profile.page_type.value
            for page in analyzed_pages
        )
    
        mode_counter = Counter()
    
        for page in analyzed_pages:
            conversion_policy = getattr(
                page,
                "conversion_policy",
                None,
            )
    
            if conversion_policy is not None:
                mode_value = (
                    conversion_policy.mode.value
                )
            else:
                mode_value = (
                    page
                    .profile
                    .recommended_mode
                    .value
                )
    
            mode_counter[
                mode_value
            ] += 1
    
        profile.page_type_counts = dict(
            sorted(
                page_type_counter.items()
            )
        )
    
        profile.mode_counts = dict(
            sorted(
                mode_counter.items()
            )
        )

    @staticmethod
    def _resolve_dominant_page_type(
        page_type_counts: dict[str, int],
    ) -> PageType:
        """
        Determine the dominant page type.

        When multiple page types have the same highest count,
        the document is classified as MIXED rather than
        selecting one arbitrarily.
        """

        if not page_type_counts:
            return PageType.UNKNOWN

        maximum_count = max(
            page_type_counts.values()
        )

        dominant_values = [
            page_type_value
            for (
                page_type_value,
                count,
            ) in page_type_counts.items()
            if count == maximum_count
        ]

        if len(dominant_values) != 1:
            return PageType.MIXED

        try:
            return PageType(
                dominant_values[0]
            )

        except ValueError:
            return PageType.UNKNOWN

    @staticmethod
    def _resolve_document_mode(
        mode_counts: dict[str, int],
    ) -> ConversionMode:
        """
        Determine the document-level recommended mode.

        This is a summary only. Individual pages continue to
        use their own recommended modes.
        """

        active_modes = [
            mode_value
            for (
                mode_value,
                count,
            ) in mode_counts.items()
            if count > 0
        ]

        if not active_modes:
            return ConversionMode.HYBRID

        if len(active_modes) > 1:
            return ConversionMode.HYBRID

        try:
            return ConversionMode(
                active_modes[0]
            )

        except ValueError:
            return ConversionMode.HYBRID

    @staticmethod
    def _requires_hybrid_conversion(
        profile: DocumentProfile,
    ) -> bool:
        """
        Return True when the complete document cannot safely
        use one uniform editable or fixed strategy.
        """

        active_mode_count = sum(
            1
            for count in profile.mode_counts.values()
            if count > 0
        )

        if active_mode_count > 1:
            return True

        if (
            profile.recommended_mode
            == ConversionMode.HYBRID
        ):
            return True

        if any([
            profile.contains_tables,
            profile.contains_charts,
            profile.contains_forms,
            profile.contains_scanned_pages
            and profile.contains_digital_pages,
            profile.contains_multiple_page_sizes,
            profile.contains_multiple_orientations,
        ]):
            return True

        return False

    @staticmethod
    def _calculate_confidence_scores(
        profile: DocumentProfile,
        page_profiles: list[PageProfile],
    ) -> None:
        """
        Calculate average page confidence scores.

        These are baseline averages. Later regression testing
        may introduce weighted confidence calculations.
        """

        profile.editable_confidence = fmean(
            page_profile.editable_confidence
            for page_profile in page_profiles
        )

        profile.fixed_confidence = fmean(
            page_profile.fixed_confidence
            for page_profile in page_profiles
        )

        profile.hybrid_confidence = fmean(
            page_profile.hybrid_confidence
            for page_profile in page_profiles
        )

        profile.ocr_confidence = fmean(
            page_profile.ocr_confidence
            for page_profile in page_profiles
        )

    @classmethod
    def _group_page_sizes(
        cls,
        sizes: list[
            tuple[float, float]
        ],
    ) -> list[
        list[tuple[float, float]]
    ]:
        """
        Group approximately equal page sizes.
        """

        groups: list[
            list[tuple[float, float]]
        ] = []

        for size in sizes:
            matching_group = None

            for group in groups:
                reference_size = group[0]

                if cls._page_sizes_match(
                    first=size,
                    second=reference_size,
                ):
                    matching_group = group
                    break

            if matching_group is None:
                groups.append(
                    [size]
                )
            else:
                matching_group.append(
                    size
                )

        return groups

    @classmethod
    def _page_sizes_match(
        cls,
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> bool:
        """
        Compare page dimensions using absolute and relative
        tolerances.
        """

        return (
            cls._dimension_matches(
                first[0],
                second[0],
            )
            and cls._dimension_matches(
                first[1],
                second[1],
            )
        )

    @classmethod
    def _dimension_matches(
        cls,
        first: float,
        second: float,
    ) -> bool:
        tolerance = max(
            cls.PAGE_SIZE_ABSOLUTE_TOLERANCE,
            max(
                abs(first),
                abs(second),
            )
            * cls.PAGE_SIZE_RELATIVE_TOLERANCE,
        )

        return (
            abs(first - second)
            <= tolerance
        )

    @classmethod
    def _resolve_orientation(
        cls,
        width: float,
        height: float,
    ) -> str:
        """
        Return portrait, landscape or square.
        """

        maximum_dimension = max(
            width,
            height,
            1.0,
        )

        dimension_difference_ratio = (
            abs(width - height)
            / maximum_dimension
        )

        if (
            dimension_difference_ratio
            <= cls.SQUARE_PAGE_RATIO_TOLERANCE
        ):
            return "square"

        if width > height:
            return "landscape"

        return "portrait"

    @staticmethod
    def _add_explanations(
        profile: DocumentProfile,
    ) -> None:
        """
        Add document-level reasons and warnings.
        """

        profile.add_reason(
            (
                f"Analyzed {profile.page_count} "
                f"page(s)."
            )
        )

        profile.add_reason(
            (
                "Dominant page type: "
                f"{profile.dominant_page_type.value}."
            )
        )

        profile.add_reason(
            (
                "Recommended document mode: "
                f"{profile.recommended_mode.value}."
            )
        )

        if profile.contains_digital_pages:
            profile.add_reason(
                (
                    f"Detected "
                    f"{profile.digital_page_count} "
                    f"digital page(s)."
                )
            )

        if profile.contains_scanned_pages:
            profile.add_reason(
                (
                    f"Detected "
                    f"{profile.scanned_page_count} "
                    f"scanned or OCR-required page(s)."
                )
            )

            profile.add_warning(
                (
                    "At least one page requires OCR "
                    "or image fallback."
                )
            )

        if (
            profile.contains_scanned_pages
            and profile.contains_digital_pages
        ):
            profile.add_warning(
                (
                    "The document contains both digital "
                    "and scanned pages."
                )
            )

        if profile.contains_tables:
            profile.add_reason(
                (
                    f"Detected table content on "
                    f"{profile.table_page_count} page(s)."
                )
            )

        if profile.contains_charts:
            profile.add_reason(
                (
                    f"Detected chart content on "
                    f"{profile.chart_page_count} page(s)."
                )
            )

        if profile.contains_forms:
            profile.add_reason(
                (
                    f"Detected form content on "
                    f"{profile.form_page_count} page(s)."
                )
            )

        if profile.contains_multiple_page_sizes:
            profile.add_warning(
                (
                    "The document contains multiple "
                    "page sizes."
                )
            )

        if profile.contains_multiple_orientations:
            profile.add_warning(
                (
                    "The document contains multiple "
                    "page orientations."
                )
            )

        if profile.requires_hybrid_conversion:
            profile.add_reason(
                (
                    "A hybrid conversion strategy is "
                    "recommended for at least part of "
                    "the document."
                )
            )