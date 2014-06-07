name=lisa2011-yams
images=collectd-c10-cpu-00.png collectd-c10-cpu-01.png \
		collectd-c10-cpu-02.png collectd-c10-cpu-03.png \
		collectd-c10-cpu-04.png collectd-c10-cpu-05.png \
		collectd-c10-cpu-06.png collectd-c10-cpu-07.png \
		collectd-c10-cpu-all.png collectd-c10-eth0.png \
		collectd-c10-lo.png collectd-c10-memory.png collectd-c10-paging.png \
		collectd-c9-eth0.png etl-c10-cpu-00.png etl-c10-cpu-01.png \
		etl-c10-cpu-02.png etl-c10-cpu-03.png etl-c10-cpu-04.png \
		etl-c10-cpu-05.png etl-c10-cpu-06.png etl-c10-cpu-07.png \
		etl-c10-cpu-all.png etl-c10-eth0.png etl-c10-lo.png \
		etl-c10-memory.png etl-c10-paging.png etl-c6-cpu-00.png \
		etl-c6-cpu-01.png etl-c6-cpu-02.png etl-c6-cpu-03.png \
		etl-c6-cpu-04.png etl-c6-cpu-05.png etl-c6-cpu-06.png \
		etl-c6-cpu-07.png etl-c6-cpu-all.png etl-c6-disk-c0d1-iops.png \
		etl-c6-disk-c0d1-octets.png etl-c6-disk-c0d2-iops.png \
		etl-c6-disk-c0d2-octets.png etl-c6-disk-c0d5-iops.png \
		etl-c6-disk-c0d5-octets.png etl-c6-disk-c0d6-iops.png \
		etl-c6-disk-c0d6-octets.png etl-c6-eth0.png etl-c6-lo.png \
		etl-c6-memory.png etl-c6-paging.png

all: $(name).pdf

$(name).pdf: $(name).tex Makefile bibliography.bib $(images)
	-rm $@
	latex -output-format=pdf $<
	bibtex $(name)
	latex -output-format=pdf $<
	latex --output-format=pdf $<

clean:
	rm -f $(name).log $(name).toc $(name).nav $(name).snm \
			$(name).out $(name).dvi $(name).aux $(name).blg $(name).bbl \
			$(name).vrb texput.log $(name).pdf
