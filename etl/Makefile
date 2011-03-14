PGINCLUDE := $(shell pg_config --includedir)
PGLIB := $(shell pg_config --libdir)

all: yams-etl

yams-etl: yams-etl.c Makefile
	cc -g -Wall -o $@ $< -I$(PGINCLUDE) -L$(PGLIB)

clean:
	rm yams-etl
