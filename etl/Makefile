PREFIX= /usr/local
INSTALL_BIN= $(PREFIX)/bin
INSTALL= cp -p

all: yams-etl yams-etl-fcgi

yams-etl: yams-etl.c Makefile
	cc -g -Wall ${CFLAGS} -o $@ $< -lfcgi -lhiredis -ljson -lpq -lpthread

yams-etl-fcgi: yams-etl-fcgi.c Makefile
	cc -g -Wall -o $@ $< -lfcgi -lhiredis

clean:
	rm -f yams-etl yams-etl-fcgi

install: all
	mkdir -p $(INSTALL_BIN)
	$(INSTALL) yams-etl-fcgi $(INSTALL_BIN)
	$(INSTALL) yams-etl $(INSTALL_BIN)
