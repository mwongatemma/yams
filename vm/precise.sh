#!/bin/sh

POSTGRES_VER=9.2

DONEFILE="/root/.done"

if [ ! -f "${DONEFILE}" ]; then
	# http://wiki.postgresql.org/wiki/Apt
	wget -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo \
			apt-key add - || exit 1
	cp /vagrant/pgdg.list /etc/apt/sources.list.d/pgdg.list || exit 1
	cp /vagrant/pgdg.pref /etc/apt/preferences.d/pgdg.pref || exit 1

	apt-get update || exit 1

	apt-get install -y \
			git \
			screen \
			tmux \
			vim \
			emacs \
			cscope \
			exuberant-ctags \
			build-essential \
			libhiredis-dev \
			libjson0-dev \
			libfcgi-dev \
			redis-server \
			lighttpd \
			apache2 \
			libapache2-mod-wsgi \
			libtool \
			libcurl4-openssl-dev \
			flex \
			bison \
			autoconf \
			pkg-config \
			libgcrypt-dev \
			postgresql-$POSTGRES_VER \
			postgresql-client-$POSTGRES_VER \
			postgresql-contrib-$POSTGRES_VER \
			postgresql-server-dev-$POSTGRES_VER \
			python-dev \
			python-pip || exit 1

	# Build collectd with db metadata patch
	git clone git://github.com/mwongatemma/collectd.git \
			/usr/local/src/collectd || exit 1
	(cd /usr/local/src/collectd && git checkout staging) || exit 1
	(cd /usr/local/src/collectd && sh build.sh && ./configure && make && \
			make install) || exit 1
	cp -p /vagrant/collectd.conf /opt/collectd/etc/collectd.conf || exit 1

	git clone git://github.com/mwongatemma/yams.git \
			/usr/local/src/yams || exit 1
	(cd /usr/local/src/yams && git checkout staging) || exit 1
	cp -p /usr/local/src/yams/examples/collectd/types.db.postgresql \
			/opt/collectd/etc/types.db.postgresql || exit 1

	export CFLAGS=-I/usr/include/postgresql
	(cd /usr/local/src/yams/etl && make install) || exit 1
	(cd /usr/local/src/yams/yams-wui && python setup.py install) || exit 1

	# Database setup
	cp -p /vagrant/pg_hba.conf /etc/postgresql/9.2/main/pg_hba.conf || exit 1
	chown postgres:postgres /etc/postgresql/9.2/main/pg_hba.conf || exit 1
	service postgresql reload || exit 1
	pip install pgxnclient || exit 1
	pgxn install json_enhancements || exit 1
	su - postgres -c /usr/local/src/yams/pg/create-database.sh || exit 1
	su - postgres -c "psql -d collectd -c \"CREATE EXTENSION json_enhancements;\"" || exit 1

	# Set up FastCGI program under lighttpd
	lighttpd-enable-mod fastcgi || exit 1
	cp -p /vagrant/lighttpd.conf /etc/lighttpd/lighttpd.conf || exit 1
	cp -p /vagrant/10-fastcgi.conf \
			/etc/lighttpd/conf-available/10-fastcgi.conf || exit 1
	service lighttpd restart || exit 1

	# Set up WUI under apache
	cp -p /vagrant/pyramid.wsgi /usr/local/bin/pyramid.wsgi | exit 1
	cp -p /vagrant/default /etc/apache2/sites-available/default || exit 1
	service apache2 restart || exit 1
fi

touch ${DONEFILE}

# Start YAMS etl and collectd by hand.
nohup yams-etl --pguser collectd >> /var/log/yams-etl.log &
/opt/collectd/sbin/collectd || exit 1
