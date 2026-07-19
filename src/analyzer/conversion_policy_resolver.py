from __future__ import annotations

from src.models.conversion_policy import (
    ConversionPolicy,
)
from src.models.page import Page
from src.models.page_profile import (
    ConversionMode,
    PageProfile,
    PageType,
)
from src.utils.rectangle_union import (
    RectangleUnion,
)


class ConversionPolicyResolver:
    """
    Converts a PageProfile into an actionable page-level
    conversion policy.

    This resolver must not contain:

        filename-specific rules
        page-number-specific rules
        sample-PDF-specific rules
    """

    MINIMUM_EDITABLE_CONFIDENCE = 0.55
    MINIMUM_HYBRID_CONFIDENCE = 0.40
    MINIMUM_OCR_CONFIDENCE = 0.50

    @classmethod
    def resolve(
        cls,
        page: Page,
    ) -> ConversionPolicy:
        """
        Create and attach a fresh conversion policy.

        Re-running the resolver replaces the previous policy
        so stale warnings and options are not retained.
        """

        profile = getattr(
            page,
            "profile",
            None,
        )

        if profile is None:
            policy = ConversionPolicy(
                page_number=page.number,

                mode=(
                    ConversionMode.HYBRID
                ),

                export_text_as_paragraphs=False,

                export_lists_as_word_lists=False,

                export_tables_as_word_tables=False,

                export_forms_as_controls=False,

                export_images_as_images=True,

                export_vectors_as_images=True,

                export_charts_as_images=True,

                use_full_page_image=True,

                allow_region_image_fallback=True,

                confidence=0.0,

                reason=(
                    "No page profile was available."
                ),
            )

            policy.add_warning(
                (
                    "The page requires a visual "
                    "fallback because profiling was "
                    "not completed."
                )
            )

            page.conversion_policy = policy

            return policy

        policy = ConversionPolicy(
            page_number=page.number
        )

        page_type = profile.page_type

        if page_type == PageType.SIMPLE_TEXT:
            cls._configure_simple_text(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.MULTI_COLUMN:
            cls._configure_multi_column(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.DESIGNED_COVER:
            cls._configure_designed_cover(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.TABLE_DOMINANT:
            cls._configure_table_dominant(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.CHART_DOMINANT:
            cls._configure_chart_dominant(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.FORM:
            cls._configure_form(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.IMAGE_DOMINANT:
            cls._configure_image_dominant(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.SCANNED:
            cls._configure_scanned(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.MAGAZINE:
            cls._configure_magazine(
                profile=profile,
                policy=policy,
            )

        elif page_type == PageType.MIXED:
            cls._configure_mixed(
                profile=profile,
                policy=policy,
            )

        else:
            cls._configure_unknown(
                profile=profile,
                policy=policy,
            )

        cls._apply_content_presence_rules(
            profile=profile,
            policy=policy,
        )

        cls._apply_confidence_rules(
            profile=profile,
            policy=policy,
        )

        policy.confidence = (
            cls._resolve_policy_confidence(
                profile=profile,
                mode=policy.mode,
            )
        )

        page.conversion_policy = policy

        return policy

    # ---------------------------------------------------------
    # Page-type policies
    # ---------------------------------------------------------

    @staticmethod
    def _configure_simple_text(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.EDITABLE
        )

        policy.export_text_as_paragraphs = True
        policy.export_lists_as_word_lists = True
        policy.export_tables_as_word_tables = True

        policy.export_images_as_images = True

        policy.export_vectors_as_images = (
            profile.vector_count > 0
        )

        policy.export_charts_as_images = True

        policy.export_forms_as_controls = False

        policy.run_ocr = False
        policy.include_ocr_text = False

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Digital text page suitable for editable "
            "Word paragraphs."
        )

    @staticmethod
    def _configure_multi_column(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = True
        policy.export_lists_as_word_lists = True
        policy.export_tables_as_word_tables = True

        policy.export_images_as_images = True
        policy.export_vectors_as_images = (
            profile.vector_count > 0
        )
        policy.export_charts_as_images = True

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Multi-column page requires editable text "
            "with layout-aware visual fallback."
        )

        policy.add_warning(
            (
                "Final reading order depends on the "
                "dedicated column and container engine."
            )
        )

    @staticmethod
    def _configure_designed_cover(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = (
            profile.has_extractable_text
        )

        policy.export_lists_as_word_lists = True
        policy.export_tables_as_word_tables = True

        policy.export_images_as_images = True
        policy.export_vectors_as_images = True
        policy.export_charts_as_images = True

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Designed page requires editable text where "
            "safe and visual preservation for artwork."
        )

        policy.add_warning(
            (
                "Decorative graphics may require a "
                "background or region-image fallback."
            )
        )

    @staticmethod
    def _configure_table_dominant(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = True
        policy.export_lists_as_word_lists = True

        policy.export_tables_as_word_tables = True

        policy.export_images_as_images = True
        policy.export_vectors_as_images = (
            profile.vector_count > 0
        )
        policy.export_charts_as_images = True

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Table-dominant page should use editable "
            "Word tables with visual fallback."
        )

        policy.add_warning(
            (
                "Low-confidence or irregular tables "
                "must be exported as images."
            )
        )

    @staticmethod
    def _configure_chart_dominant(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = True
        policy.export_lists_as_word_lists = True
        policy.export_tables_as_word_tables = True

        policy.export_images_as_images = True
        policy.export_vectors_as_images = True

        policy.export_charts_as_images = True

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Chart page should preserve surrounding text "
            "and export charts visually."
        )

        policy.add_warning(
            (
                "Charts will remain images until reliable "
                "native chart reconstruction is available."
            )
        )

    @staticmethod
    def _configure_form(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = True
        policy.export_lists_as_word_lists = True
        policy.export_tables_as_word_tables = True

        policy.export_forms_as_controls = True

        policy.export_images_as_images = True
        policy.export_vectors_as_images = True
        policy.export_charts_as_images = True

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Form page requires editable labels and "
            "Word-compatible form controls where possible."
        )

        policy.add_warning(
            (
                "Unsupported form controls must use a "
                "visual fallback."
            )
        )

    @staticmethod
    def _configure_image_dominant(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.FIXED
        )

        policy.export_text_as_paragraphs = False
        policy.export_lists_as_word_lists = False
        policy.export_tables_as_word_tables = False
        policy.export_forms_as_controls = False

        policy.export_images_as_images = True
        policy.export_vectors_as_images = True
        policy.export_charts_as_images = True

        policy.run_ocr = False
        policy.include_ocr_text = False

        policy.use_full_page_image = True

        policy.allow_region_image_fallback = (
            False
        )

        policy.reason = (
            "Image-dominant page is safest as a "
            "full-page visual representation."
        )

    @staticmethod
    def _configure_scanned(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.OCR
        )

        # Text paragraphs can be produced after OCR.
        policy.export_text_as_paragraphs = True

        # List and table semantics must be detected from the
        # OCR result later.
        policy.export_lists_as_word_lists = False
        policy.export_tables_as_word_tables = False
        policy.export_forms_as_controls = False

        policy.export_images_as_images = True
        policy.export_vectors_as_images = False
        policy.export_charts_as_images = False

        policy.run_ocr = True
        policy.include_ocr_text = True

        # Preserve the page image even when OCR succeeds.
        policy.use_full_page_image = True

        policy.allow_region_image_fallback = (
            False
        )

        policy.reason = (
            "Scanned page requires OCR and full-page "
            "visual preservation."
        )

    @staticmethod
    def _configure_magazine(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = True
        policy.export_lists_as_word_lists = True
        policy.export_tables_as_word_tables = True

        policy.export_images_as_images = True
        policy.export_vectors_as_images = True
        policy.export_charts_as_images = True

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Magazine-style page requires container-aware "
            "text and visual-region preservation."
        )

        policy.add_warning(
            (
                "Complex columns, sidebars and artwork "
                "require the container engine."
            )
        )

    @staticmethod
    def _configure_mixed(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = (
            profile.has_extractable_text
        )

        policy.export_lists_as_word_lists = (
            profile.has_extractable_text
        )

        policy.export_tables_as_word_tables = (
            profile.table_count > 0
        )

        policy.export_forms_as_controls = (
            profile.form_field_count > 0
        )

        policy.export_images_as_images = True

        policy.export_vectors_as_images = (
            profile.vector_count > 0
        )

        policy.export_charts_as_images = (
            profile.chart_count > 0
        )

        policy.use_full_page_image = False

        policy.allow_region_image_fallback = (
            True
        )

        policy.reason = (
            "Mixed-content page requires independent "
            "policies for text and visual regions."
        )

    @staticmethod
    def _configure_unknown(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        policy.mode = (
            ConversionMode.HYBRID
        )

        policy.export_text_as_paragraphs = (
            profile.has_extractable_text
        )

        policy.export_lists_as_word_lists = (
            profile.has_extractable_text
        )

        policy.export_tables_as_word_tables = (
            profile.table_count > 0
        )

        policy.export_forms_as_controls = (
            profile.form_field_count > 0
        )

        policy.export_images_as_images = True

        policy.export_vectors_as_images = (
            profile.vector_count > 0
        )

        policy.export_charts_as_images = (
            profile.chart_count > 0
        )

        policy.use_full_page_image = (
            not profile.has_extractable_text
            and (
                profile.image_count > 0
                or profile.vector_count > 0
            )
        )

        policy.allow_region_image_fallback = (
            not policy.use_full_page_image
        )

        policy.reason = (
            "Unknown page structure requires a safe "
            "hybrid policy."
        )

        policy.add_warning(
            (
                "The page structure could not be "
                "classified confidently."
            )
        )

    # ---------------------------------------------------------
    # General finalization
    # ---------------------------------------------------------

    @staticmethod
    def _apply_content_presence_rules(
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        """
        Disable semantic text conversion when no text exists,
        unless OCR is explicitly requested.
        """

        if (
            not profile.has_extractable_text
            and not policy.run_ocr
        ):
            policy.export_text_as_paragraphs = (
                False
            )

            policy.export_lists_as_word_lists = (
                False
            )

        if profile.table_count <= 0:
            # Keep this True only for page types that were
            # explicitly classified as table-dominant.
            if (
                profile.page_type
                != PageType.TABLE_DOMINANT
            ):
                policy.export_tables_as_word_tables = (
                    False
                )

        if profile.form_field_count <= 0:
            if profile.page_type != PageType.FORM:
                policy.export_forms_as_controls = (
                    False
                )

        if profile.chart_count <= 0:
            if (
                profile.page_type
                != PageType.CHART_DOMINANT
            ):
                policy.export_charts_as_images = (
                    False
                )

        if profile.vector_count <= 0:
            policy.export_vectors_as_images = (
                False
            )

    @classmethod
    def _apply_confidence_rules(
        cls,
        profile: PageProfile,
        policy: ConversionPolicy,
    ) -> None:
        """
        Apply safe fallback rules when the preferred
        conversion confidence is low.
        """

        if (
            policy.mode
            == ConversionMode.EDITABLE
            and profile.editable_confidence
            < cls.MINIMUM_EDITABLE_CONFIDENCE
        ):
            policy.mode = (
                ConversionMode.HYBRID
            )

            policy.reason = (
                "Editable confidence is low; use editable "
                "content with visual fallback."
            )

            policy.add_warning(
                (
                    "The page was downgraded from editable "
                    "to hybrid because editable confidence "
                    "was below the safety threshold."
                )
            )

        if (
            policy.mode
            == ConversionMode.HYBRID
            and profile.hybrid_confidence
            < cls.MINIMUM_HYBRID_CONFIDENCE
        ):
            policy.add_warning(
                (
                    "Hybrid confidence is low; visual "
                    "fallback should be preferred for "
                    "uncertain regions."
                )
            )

        if (
            policy.mode
            == ConversionMode.OCR
            and profile.ocr_confidence
            < cls.MINIMUM_OCR_CONFIDENCE
        ):
            policy.add_warning(
                (
                    "OCR confidence is low; preserve the "
                    "original page image."
                )
            )

            policy.use_full_page_image = True

    @staticmethod
    def _resolve_policy_confidence(
        profile: PageProfile,
        mode: ConversionMode,
    ) -> float:
        """
        Select the confidence associated with the resolved
        page mode.
        """

        if mode == ConversionMode.EDITABLE:
            confidence = (
                profile.editable_confidence
            )

        elif mode == ConversionMode.FIXED:
            confidence = (
                profile.fixed_confidence
            )

        elif mode == ConversionMode.OCR:
            confidence = (
                profile.ocr_confidence
            )

        elif mode == ConversionMode.IMAGE_FALLBACK:
            confidence = (
                profile.fixed_confidence
            )

        else:
            confidence = (
                profile.hybrid_confidence
            )

        return RectangleUnion.clamp_ratio(
            confidence
        )