# DocuMind PDF Reference Corpus

This corpus is used to prevent sample-specific PDF-to-DOCX rules.

## General rules

- Do not tune alignment or layout rules for one sample PDF.
- Use geometry, typography, reading order, and structural evidence.
- Run regression tests across all corpus categories after every engine change.
- Keep fixed-layout and editable/reflow modes separate.

## Documents

### 1. spdf7.pdf
**Category:** Designed report - US Letter

- cover page
- mixed headings and body text
- bullets and numbered lists
- table and charts
- US Letter page size

### 2. spdf8(4).pdf
**Category:** Designed report - custom tall page

- same logical content as spdf7
- different page aspect ratio
- layout scaling and alignment comparison

### 3. spdf9.pdf
**Category:** Long structured digital document

- 50 pages
- table of contents
- headings
- lists
- tables
- links
- headers and footers

### 4. spdf10.pdf
**Category:** Large image-only PDF

- 100 scanned/image pages
- OCR routing
- memory and batch-processing
- cover-page alignment

### 5. spdf11.pdf
**Category:** Form-style document

- labels and input areas
- checkbox/radio-style controls
- form layout reconstruction

### 6. spdf12.pdf
**Category:** Feature-rich developer sample

- styled text
- bullet and numbered lists
- tables
- images
- hyperlinks
- headers and footers

### 7. spdf13(1).pdf
**Category:** Small-page text and watermark sample

- non-standard page size
- dense paragraphs
- watermark-related content

### 8. spdf1(8).pdf
**Category:** Long-form simple text

- multi-page paragraphs
- basic heading
- reflow accuracy

### 9. spdf2(2).pdf
**Category:** Single-page dense text

- simple typography
- paragraph reconstruction
- line wrapping

### 10. spdf3(3).pdf
**Category:** Bookmark and form-layout sample

- header/footer
- bookmarks
- structured labels
- mixed page content

### 11. spdf4(7).pdf
**Category:** Mixed document with charts and bullets

- paragraphs
- bullet lists
- charts
- table-like data

### 12. spdf5(1).pdf
**Category:** Accessible and complex tables

- 11 pages
- row and column headers
- financial tables
- footnotes
- irregular table structures

### 13. spdf6.pdf
**Category:** Dense project-estimate document

- tables
- emoji and symbols
- numbered sections
- mixed typography

### 14. I40_RTC 1.pdf
**Category:** Legal response document

- mixed portrait and landscape pages
- headers and footers
- numbered comment responses
- narrow columns

### 15. i40Today-MediaKit-2023 1 (1).pdf
**Category:** Magazine and media-kit layout

- square pages
- multi-column text
- large typography
- full-page graphics
- marketing layout

### 16. QR code printer setup (1).pdf
**Category:** Screenshot/instruction PDF

- image-heavy instructions
- minimal parsed text
- OCR and image placement

### 17. 20150805-Model MDO Contract (3).pdf
**Category:** Large legal contract

- 220 pages
- scanned cover plus digital text
- table of contents
- nested numbering
- mixed page sizes
- headers and footers

### 18. Class-4-Print31 1.pdf
**Category:** Educational textbook

- 51 pages
- decorative cover
- images
- colored text
- tables and teaching content

### 19. guidelineforpreparationproject-estimatesforrivervalleyprojects (1).pdf
**Category:** Historical scanned/hybrid technical manual

- 141 pages
- scanned and OCR text
- old typography
- photographs
- variable page dimensions
