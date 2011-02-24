name=yams-user-guide

all: $(name).pdf

$(name).pdf: $(name).tex Makefile
	-rm $@
	latex --output-format=pdf $<
	latex --output-format=pdf $<

clean:
	rm -f $(name)*.log $(name)*.aux $(name).pdf
