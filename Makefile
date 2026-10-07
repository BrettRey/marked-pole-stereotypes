# Makefile for LaTeX paper compilation

# Configuration
LATEX = xelatex
BIBER = biber
MAIN = marked-pole-stereotypes
PDF_BASENAME ?= $(MAIN)
SUBMISSION_PDF = $(PDF_BASENAME).pdf
OUTDIR = .

# Targets
.PHONY: all quick refresh-submission-pdf clean distclean view help test

# Default target: build the PDF, plus a renamed copy only when PDF_BASENAME differs
# (with equal names a copy rule would override the build rule and make would build nothing)
all: $(MAIN).pdf
ifneq ($(SUBMISSION_PDF),$(MAIN).pdf)
all: $(SUBMISSION_PDF)
$(SUBMISSION_PDF): $(MAIN).pdf
	@$(MAKE) --no-print-directory refresh-submission-pdf
endif

# Full build sequence with bibliography
$(MAIN).pdf: $(MAIN).tex references.bib $(wildcard references-local.bib) $(wildcard sections/*.tex) $(wildcard figures/*.pdf)
	@echo "==> First LaTeX pass..."
	$(LATEX) -output-directory=$(OUTDIR) $(MAIN).tex
	@echo "==> Running Biber..."
	$(BIBER) $(MAIN)
	@echo "==> Second LaTeX pass..."
	$(LATEX) -output-directory=$(OUTDIR) $(MAIN).tex
	@echo "==> Third LaTeX pass (finalizing)..."
	$(LATEX) -output-directory=$(OUTDIR) $(MAIN).tex
	@echo "==> Build complete: $(MAIN).pdf"

refresh-submission-pdf:
	@if [ "$(SUBMISSION_PDF)" != "$(MAIN).pdf" ]; then \
		cp -f "$(MAIN).pdf" "$(SUBMISSION_PDF)"; \
	fi
	@echo "==> Submission/preprint PDF ready: $(SUBMISSION_PDF)"

# Quick build (single pass, no bibliography update)
quick: $(MAIN).tex
	@echo "==> Quick build (single pass)..."
	$(LATEX) -output-directory=$(OUTDIR) $(MAIN).tex
	@$(MAKE) --no-print-directory refresh-submission-pdf

# Use LuaLaTeX instead of XeLaTeX (not recommended - breaks PDF text layer)
lualatex: LATEX = lualatex
lualatex: all

# Clean build artifacts (keep PDF)
clean:
	@echo "==> Cleaning build artifacts..."
	rm -f $(MAIN).aux $(MAIN).bbl $(MAIN).bcf $(MAIN).blg $(MAIN).log
	rm -f $(MAIN).out $(MAIN).run.xml $(MAIN).toc $(MAIN).fdb_latexmk
	rm -f $(MAIN).fls $(MAIN).synctex.gz
	@echo "==> Clean complete"

# Clean everything including PDF
distclean: clean
	@echo "==> Removing PDF..."
	rm -f "$(MAIN).pdf"
	@if [ "$(SUBMISSION_PDF)" != "$(MAIN).pdf" ]; then \
		rm -f "$(SUBMISSION_PDF)"; \
	fi
	@echo "==> Deep clean complete"

# Open named submission/preprint PDF viewer (macOS)
view: $(SUBMISSION_PDF)
	@echo "==> Opening PDF..."
	open "$(SUBMISSION_PDF)"

# Test the Python specification
test:
	@echo "==> Testing theoretical specification..."
	cd src && python typology.py

# Show available targets
help:
	@echo "Available targets:"
	@echo "  make          - Build $(MAIN).pdf (plus a renamed copy if PDF_BASENAME is set)"
	@echo "  make quick    - Quick build (single pass) and refresh named PDF"
	@echo "  make lualatex - Build using LuaLaTeX (not recommended)"
	@echo "  make clean    - Remove build artifacts (keep PDF)"
	@echo "  make distclean- Remove everything including PDF"
	@echo "  make view     - Open named submission/preprint PDF (macOS only)"
	@echo "  make test     - Run Python specification tests"
	@echo "  make help     - Show this help message"
	@echo ""
	@echo "Configuration:"
	@echo "  PDF_BASENAME  - File-safe basename for an upload copy (default: same as the manuscript)"
