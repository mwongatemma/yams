#!/bin/sh

if [ $# -ne 1 ]; then
	echo "usage: $0 <# of tables to generate>"
	exit 1
fi

NUM=$1

for id in `seq 1 ${NUM}`; do
	psql -q -c "CREATE TABLE t${id} (an INTEGER);"
done
