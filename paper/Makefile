PDF = more-code-is-not-progress.pdf
TEX = more-code-is-not-progress.tex

.PHONY: all clean

all: $(PDF)

$(PDF): $(TEX)
	tectonic $(TEX)

clean:
	rm -f *.aux *.bbl *.bcf *.blg *.fls *.log *.out *.run.xml *.synctex.gz *.toc $(PDF)
