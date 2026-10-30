## Citation Verification

**Never cite what you haven't verified.**

1. **Author Names**: Verify exact author names from the actual paper PDF or official publication page. Do not guess or hallucinate author names based on similar-sounding names.
2. **Publication Venue**: Confirm the exact venue (conference/journal) and year. Papers may be submitted to one venue but published at another (e.g., ICLR submission → ICRA publication).
3. **Paper Title**: Use the exact title from the published version, not preprint titles which may differ.
4. **Cited Claims**: Every specific claim attributed to a paper (e.g., "9% improvement on Synthia", "4.7% on OpenImages") must be verifiable in the actual paper text. If a number cannot be confirmed, use qualitative language instead (e.g., "significant improvements").
5. **BibTeX Keys**: When updating citation keys, search for ALL references to the old key and update them consistently.

**Verification Process**:

- Use web search to find the official publication page (not just preprints)
- Cross-reference author names with the paper's author list
- DBLP is the authoritative source for CS publication metadata
- For specific numerical claims, locate the exact quote or table in the paper
- When uncertain, flag the citation for manual verification rather than guessing
- After adding citations into md or bibtex entries into biblio.bib, fact check all fields from web. Even if you performed fact check before, always do it again after writing the citation in the document.

Ask yourself: "Can I point to the exact page where this claim appears?"
