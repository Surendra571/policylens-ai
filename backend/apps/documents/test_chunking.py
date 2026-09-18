from apps.documents.processors.chunker import PolicyAwareChunker, detect_section_heading


class TestPolicyAwareChunking:
    """Test suite for Phase 6 policy-aware chunking service."""

    def setup_method(self):
        self.doc_id = "test-doc-uuid-1234"
        self.chunker = PolicyAwareChunker(max_chunk_size=500, chunk_overlap=100)

    def test_section_heading_detection(self):
        """Verify section detector identifies standard insurance section headers."""
        assert detect_section_heading("SECTION 1: COVERAGE & BENEFITS") == "SECTION 1: COVERAGE & BENEFITS"
        assert detect_section_heading("Exclusions:") == "Exclusions"
        assert detect_section_heading("WAITING PERIODS") == "WAITING PERIODS"
        assert detect_section_heading("Part B: Terms and Conditions") == "Part B: Terms and Conditions"
        assert detect_section_heading("This is just regular policy sentence.") is None

    def test_section_boundaries_preserved(self):
        """Verify chunks transition their section metadata when a new section header appears."""
        page_text = (
            "SECTION 1: BENEFITS\n"
            "In-patient hospitalization expenses are covered up to the Sum Insured.\n\n"
            "EXCLUSIONS\n"
            "Any treatment received outside the geographical scope of India is excluded."
        )

        chunks, _ = self.chunker.chunk_single_page(
            document_id=self.doc_id,
            page_number=1,
            text=page_text,
        )

        assert len(chunks) == 2
        assert chunks[0]["metadata"]["section"] == "SECTION 1: BENEFITS"
        assert "In-patient hospitalization" in chunks[0]["content"]

        assert chunks[1]["metadata"]["section"] == "EXCLUSIONS"
        assert "outside the geographical scope" in chunks[1]["content"]

    def test_page_number_and_metadata_schema(self):
        """
        Verify every chunk contains the exact metadata schema:
        {
            "document_id": "...",
            "page_number": 18,
            "section": "Exclusions",
            "chunk_index": 4
        }
        """
        text = "EXCLUSIONS\nInvestigation and evaluation purposes only are not covered."
        chunks, _ = self.chunker.chunk_single_page(
            document_id="doc-777",
            page_number=18,
            text=text,
            start_chunk_index=4,
        )

        assert len(chunks) == 1
        chunk = chunks[0]
        meta = chunk["metadata"]

        assert meta["document_id"] == "doc-777"
        assert meta["page_number"] == 18
        assert meta["section"] == "EXCLUSIONS"
        assert meta["chunk_index"] == 4

    def test_overlapping_chunks_on_long_section(self):
        """Verify long sections are divided into chunks that preserve configured overlap."""
        chunker = PolicyAwareChunker(max_chunk_size=150, chunk_overlap=40)
        long_paragraph = (
            "EXCLUSIONS\n"
            "Clause A: Dental treatment or surgery of any kind unless requiring hospitalization. "
            "Clause B: Convalescence, general debility, cure, rest cure, and run-down condition. "
            "Clause C: Intentional self-injury, suicide, or attempted suicide."
        )

        chunks, _ = chunker.chunk_single_page(
            document_id=self.doc_id,
            page_number=5,
            text=long_paragraph,
        )

        assert len(chunks) >= 2
        # Verify overlap between chunk 0 and chunk 1
        chunk0_end = chunks[0]["content"][-30:]
        assert any(word in chunks[1]["content"] for word in chunk0_end.split() if len(word) > 4)

    def test_very_short_section_handling(self):
        """Very short sections (e.g. heading + short sentence) are cleanly preserved as intact chunks."""
        short_text = "REDRESSAL OF GRIEVANCES\nFor grievances, contact gro@insurer.com."
        chunks, _ = self.chunker.chunk_single_page(
            document_id=self.doc_id,
            page_number=12,
            text=short_text,
        )

        assert len(chunks) == 1
        assert chunks[0]["metadata"]["section"] == "REDRESSAL OF GRIEVANCES"
        assert "gro@insurer.com" in chunks[0]["content"]
        assert chunks[0]["metadata"]["page_number"] == 12

    def test_very_long_section_splitting(self):
        """A lengthy section with extensive text is partitioned into manageable chunks respecting max_chunk_size."""
        chunker = PolicyAwareChunker(max_chunk_size=200, chunk_overlap=50)
        repetitive_exclusions = (
            "WAITING PERIODS\n"
            + "Treatment for cataract has a waiting period of 24 consecutive months. " * 8
        )

        chunks, _ = chunker.chunk_single_page(
            document_id=self.doc_id,
            page_number=3,
            text=repetitive_exclusions,
        )

        assert len(chunks) >= 3
        for idx, ch in enumerate(chunks):
            assert len(ch["content"]) <= 250  # within margin of max_chunk_size
            assert ch["metadata"]["section"] == "WAITING PERIODS"
            assert ch["metadata"]["page_number"] == 3
            assert ch["metadata"]["chunk_index"] == idx

    def test_multi_page_section_inheritance(self):
        """Verify section context is carried across page transitions without crossing page boundaries."""
        pages = [
            {"page_number": 1, "extracted_text": "EXCLUSIONS\nItem 1: Cosmetic surgery."},
            {"page_number": 2, "extracted_text": "Item 2: Stem cell therapy is excluded."},
        ]

        chunks = self.chunker.chunk_document(document_id=self.doc_id, pages=pages)

        assert len(chunks) == 2
        # Page 1 chunk
        assert chunks[0]["metadata"]["page_number"] == 1
        assert chunks[0]["metadata"]["section"] == "EXCLUSIONS"

        # Page 2 chunk carries forward "EXCLUSIONS" section while retaining page_number 2
        assert chunks[1]["metadata"]["page_number"] == 2
        assert chunks[1]["metadata"]["section"] == "EXCLUSIONS"
        assert chunks[1]["metadata"]["chunk_index"] == 1
