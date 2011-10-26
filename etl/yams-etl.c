#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>

#include <hiredis/hiredis.h>

#include <json/json.h>

#include <libpq-fe.h>

#define HOSTNAME_LEN 65
#define KEY_LEN 255

#define SQL_LEN 1023

/* Max length a table name can be in PostgreSQL. */
#define TABLENAME_LEN 255

#define CONNINFO_LEN 255

#define INSERT_STATEMENT \
		"INSERT INTO %s\n" \
		"            (time, interval, host, plugin, plugin_instance,\n" \
		"             type, type_instance, dsnames, dstypes, values)\n" \
		"VALUES (TIMESTAMP WITH TIME ZONE 'EPOCH' + " \
				"%d * INTERVAL '1 SECOND',\n" \
		"        %d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');"

#define INSERT_STATEMENT_POSTGRESQL \
		"INSERT INTO %s\n" \
		"            (time, interval, host, plugin, plugin_instance,\n" \
		"             type, type_instance, dsnames, dstypes, values,\n" \
		"             database, schemaname, tablename, indexname,\n" \
		"             metric)\n " \
		"VALUES (TIMESTAMP WITH TIME ZONE 'EPOCH' + " \
				"%d * INTERVAL '1 SECOND',\n" \
		"        %d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s',\n" \
		"        '%s', '%s', '%s', '%s');"

#define SELECT_DAY0 "SELECT ((TIMESTAMP WITH TIME ZONE 'EPOCH' + %d * " \
		"INTERVAL '1 SECOND') AT TIME ZONE 'UTC')::DATE;"
#define SELECT_DAY1 "SELECT ('%s'::DATE + INTERVAL '1 DAY')::DATE;"

#define CREATE_PARTITION_TABLE \
		"CREATE TABLE %s (%s\n" \
		"    CHECK (time >= '%s'::TIMESTAMP AT TIME ZONE 'UTC'\n" \
		"       AND time < '%s'::TIMESTAMP AT TIME ZONE 'UTC')\n" \
		") INHERITS(vl_%s);"

static int verbose_flag = 0;
static int stats_flag = 0;

struct opts
{
	char *redis_server;
	int redis_port;
	char *redis_key;

	/* PostgreSQL connection string. */
	char conninfo[CONNINFO_LEN + 1];

	/* Hold some thread wide stats here too. */
	int pcount;
	int rcount;
};

inline int create_partition_index(PGconn *, const char *, char *);
int create_partition_table(PGconn *, char *, const char *, time_t, char *);
inline int do_command(PGconn *, char *);
int do_insert(PGconn *, char *);
int load(PGconn *, json_object *);
int process(PGconn *, char *);
void *thread_main(void *data);
void usage();
inline int work(struct opts *);

inline int create_partition_index(PGconn *conn, const char *plugin,
		char *tablename)
{
	char sql[SQL_LEN + 1];

	if (strcmp(plugin, "cpu") == 0)
		snprintf(sql, SQL_LEN,
				"CREATE INDEX ON %s (time, host, type_instance, " \
				"plugin_instance);", tablename);
	else if (strcmp(plugin, "memory") == 0 || strcmp(plugin, "vmem") == 0)
		snprintf(sql, SQL_LEN, "CREATE INDEX ON %s (time, host);", tablename);
	else
		snprintf(sql, SQL_LEN, "CREATE INDEX ON %s (time, host);", tablename);

	if (do_command(conn, sql) != 0)
		return 1;
	return 0;
}

int create_partition_table(PGconn *conn, char *tablename, const char *plugin,
		time_t timet, char *metric)
{
	PGresult *res;
	char sql[SQL_LEN + 1];
	char day0_str[11];
	char day1_str[11];

	if (do_command(conn, "BEGIN;") != 0)
		exit(1);

	snprintf(sql, SQL_LEN, SELECT_DAY0, (int) timet);
	res = PQexec(conn, sql);
	if (PQresultStatus(res) != PGRES_TUPLES_OK) {
		fprintf(stderr, "SELECT_DAY0 command failed: %s %s",
				PQresultErrorField(res, PG_DIAG_SQLSTATE),
				PQerrorMessage(conn));
		return 1;
	}
	strcpy(day0_str,  PQgetvalue(res, 0, 0));
	PQclear(res);

	snprintf(sql, SQL_LEN, SELECT_DAY1, day0_str);
	res = PQexec(conn, sql);
	if (PQresultStatus(res) != PGRES_TUPLES_OK) {
		fprintf(stderr, "SELECT_DAY1 command failed: %s %s",
				PQresultErrorField(res, PG_DIAG_SQLSTATE),
				PQerrorMessage(conn));
		return 1;
	}
	strcpy(day1_str,  PQgetvalue(res, 0, 0));
	PQclear(res);

	if (strcmp(plugin, "postgresql") == 0) {
		char extra_check[64];
		snprintf(extra_check, 63, "\n    CHECK (metric = '%s'),", metric);
		snprintf(sql, SQL_LEN, CREATE_PARTITION_TABLE, tablename, extra_check,
				day0_str, day1_str, plugin);
	} else
		snprintf(sql, SQL_LEN, CREATE_PARTITION_TABLE, tablename, "",
				day0_str, day1_str, plugin);

	if (do_command(conn, sql) != 0)
		return 1;

	create_partition_index(conn, plugin, tablename);

	if (do_command(conn, "COMMIT;") != 0)
		return 1;

	return 0;
}

inline int do_command(PGconn *conn, char *sql)
{
	PGresult *res = PQexec(conn, sql);
	if (PQresultStatus(res) != PGRES_COMMAND_OK) {
		fprintf(stderr, "command failed: %s %s\n",
				PQresultErrorField(res, PG_DIAG_SQLSTATE),
				PQerrorMessage(conn));
		return 1;
	}
	PQclear(res);
	return 0;
}

int do_insert(PGconn *conn, char *sql)
{
	PGresult *res;

	res = PQexec(conn, sql);
	if (PQresultStatus(res) != PGRES_COMMAND_OK) {
		if (strcmp(PQresultErrorField(res, PG_DIAG_SQLSTATE), "42P01") == 0) {
			PQclear(res);
			return 1;
		} else {
			fprintf(stderr, "INSERT command failed: %s %s",
					PQresultErrorField(res, PG_DIAG_SQLSTATE),
					PQerrorMessage(conn));
		}
	}
	PQclear(res);
	return 0;
}

int load(PGconn *conn, json_object *jsono)
{
	int i;

	struct json_object *jo_t;

	const char *plugin = NULL;
	const char *plugin_instance = NULL;
	const char *type = NULL;
	const char *type_instance = NULL;
	const char *dsnames = NULL;
	const char *dstypes = NULL;
	const char *values = NULL;
	const char *host = NULL;
	time_t timet;
	int interval;
	struct tm gmtm;

	char sql[SQL_LEN + 1];
	char partition_table[TABLENAME_LEN + 1];

	/*
	 * This is hard coded to 65 to match the max length (including termination)
	 * of the type_instance value from collectd.
	 */
	char metric[65] = "";

	jo_t = json_object_object_get(jsono, "plugin");
	plugin = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "plugin_instance");
	plugin_instance = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "type");
	type = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "type_instance");
	type_instance = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "dsnames");
	dsnames = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "dstypes");
	dstypes = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "values");
	values = json_object_get_string(jo_t);

	jo_t = json_object_object_get(jsono, "time");
	timet = (time_t) json_object_get_int(jo_t);
	gmtime_r(&timet, &gmtm);

	jo_t = json_object_object_get(jsono, "interval");
	interval = json_object_get_int(jo_t);

	jo_t = json_object_object_get(jsono, "host");
	host = json_object_get_string(jo_t);

	if (strcmp(plugin, "postgresql") == 0) {
		const char *database = NULL;
		const char *schemaname = NULL;
		const char *tablename = NULL;
		const char *indexname = NULL;

		char *tmp = strstr(type_instance, "-");
		int length = tmp - type_instance;

		jo_t = json_object_object_get(jsono, "database");
		database = json_object_get_string(jo_t);

		jo_t = json_object_object_get(jsono, "schema");
		schemaname = json_object_get_string(jo_t);

		jo_t = json_object_object_get(jsono, "table");
		tablename = json_object_get_string(jo_t);

		jo_t = json_object_object_get(jsono, "index");
		indexname = json_object_get_string(jo_t);

		strncpy(metric, type_instance, length);
		metric[length] = '\0';

		snprintf(partition_table, TABLENAME_LEN, "vl_%s_%d%02d%02d_%s", plugin,
				gmtm.tm_year + 1900, gmtm.tm_mon + 1, gmtm.tm_mday, metric);
		snprintf(sql, SQL_LEN, INSERT_STATEMENT_POSTGRESQL, partition_table,
				(int) timet, interval, host, plugin, plugin_instance, type,
				type_instance, dsnames, dstypes, values, database, schemaname,
				tablename, indexname, metric);

	} else {
		snprintf(partition_table, TABLENAME_LEN, "vl_%s_%d%02d%02d", plugin,
				gmtm.tm_year + 1900, gmtm.tm_mon + 1, gmtm.tm_mday);
		snprintf(sql, SQL_LEN, INSERT_STATEMENT, partition_table, (int) timet,
				interval, host, plugin, plugin_instance, type, type_instance,
				dsnames, dstypes, values);
	}

	/*
	 * It may be more efficient to append the strings manually and converts the
	 * []'s to {}'s than to use snprintf().
	 */
	for (i = 203; i < strlen(sql); i++) {
		if (sql[i] == '[')
			sql[i] = '{';
		else if (sql[i] == ']')
			sql[i] = '}';
	}

	i = do_insert(conn, sql);
	if (i != 0) {
		/* The partition table does not exist, create it. */
		i = create_partition_table(conn, partition_table, plugin, timet,
				metric);
		if (i == 0) {
			i = do_insert(conn, sql);
			if (i != 0) {
				fprintf(stderr, "second insert attempt failed\n");
				return 1;
			}
		} else {
			do_command(conn, "ROLLBACK;");
			/*
			 * Assume the CREATE TABLE failed because another threads is in the
			 * middle of creating that table.  Wait a few seconds and tgry the
			 * insert again.
			 */
			sleep(3);
			if (do_insert(conn, sql) != 0)
				fprintf(stderr, "unexpected second insert failure\n");
			return 1;
		}
	}

	return 0;
}

int process(PGconn *conn, char *json_str)
{
	struct json_object *jsono;

	jsono = json_tokener_parse(json_str);
	load(conn, jsono);
	/* json_object_put() releases memory? */
	json_object_put(jsono);

	return 0;
}

void *thread_main(void *data)
{
	work((struct opts *) data);
	return NULL;
}

void usage()
{
	printf("usage: yams-etl --help|-?\n");
	printf("       yams-etl [--pgdatabase <PGDATABASE>]\n");
	printf("                [--pghost <PGHOST>]\n");
	printf("                [--pgport <PGPORT>]\n");
	printf("                [--pgusername <PGUSER>]\n");
	printf("                [--redis-key <key>] (default: yamsetl)\n");
	printf("                [--redis-port <port>] (default: 6379)\n");
	printf("                [--redis-server <host>] (default: localhost)\n");
	printf("                [--verbose]\n");
	printf("                [--stats]\n");
	printf("                [--workers <threads>|-w <threads>]\n");
}

inline int work(struct opts *options)
{
	redisContext *redis;
	redisReply *reply;

	PGconn *conn;

	char *p1, *p2;
	int bcount = 0;

	/*
	 * Open a connection to Redis once the FastCGI service starts for
	 * the life of the service.
	 */
	redis = redisConnect(options->redis_server, options->redis_port);
	if (redis->err) {
		printf("yams-etl error: %s\n", redis->errstr);
		exit(1);
	}

	/*
	 * Open a connection to the PostgreSQL data warehouse.
	 */
	conn = PQconnectdb(options->conninfo);
	if (PQstatus(conn) != CONNECTION_OK) {
		fprintf(stderr, "Connection to database failed: %s",
				PQerrorMessage(conn));
		exit(1);
	}

	while (1) {
		/* Pop the POST data from Redis. */
		/* Why doesn't BLPOP return any data? */
		reply = redisCommand(redis, "BLPOP %s 0", options->redis_key);
		if (stats_flag)
			++options->rcount;
		if (reply->elements != 2 || reply->element[1]->str == NULL)
			continue;

		/*
		 * collectd doesn't actually create 100% compliant JSON objects.  Need to
		 * manually break out the individual JSON objects from an array type
		 * structure before we can actually process the data.
		 */
		p1 = reply->element[1]->str;
		while (*p1 != '\0') {
			if (*p1 == '{') {
				++bcount;
				p2 = p1 + 1;
				while (bcount > 0) {
					if (*p2 == '{')
						++bcount;
					else if (*p2 == '}')
						--bcount;
					++p2;
				}
				*p2 = '\0';
				process(conn, p1);
				if (stats_flag)
					++options->pcount;
				p1 = p2 + 1;
			} else {
				++p1;
			}
		}
		freeReplyObject(reply);
	}

	return 0;
}

int main(int argc, char *argv[])
{
	int c;

	pthread_t *threads;
	int workers = 1;

	/* Default values for Redis connection information. */
	const char redis_server[HOSTNAME_LEN + 1] = "localhost";
	const int redis_port = 6379;
	const char redis_key[KEY_LEN + 1] = "yamsetl";

	struct opts options;

	options.rcount = 0;
	options.pcount = 0;
	options.conninfo[0] = '\0';
	options.redis_server = (char *) redis_server;
	options.redis_port = redis_port;
	options.redis_key = (char *) redis_key;

	time_t thistime, lasttime;

	while (1) {
		int option_index = 0;
		static struct option long_options[] = {
			{"help", no_argument, NULL, '?'},
			{"pgdatabase", required_argument, NULL, 'D'},
			{"pghost", required_argument, NULL, 'H'},
			{"pgport", required_argument, NULL, 'P'},
			{"pgusername", required_argument, NULL, 'U'},
			{"redis-key", required_argument, NULL, 'd'},
			{"redis-port", required_argument, NULL, 'p'},
			{"redis-server", required_argument, NULL, 'h'},
			{"verbose", no_argument, &verbose_flag, 1},
			{"stats", no_argument, &stats_flag, 'v'},
			{"workers", required_argument, NULL, 'w'},
			{0, 0, 0, 0}
		};
		c = getopt_long(argc, argv, "?D:d:H:h:P:p:U:vw:", long_options,
				&option_index);
		if (c == -1)
			break;

		switch (c) {
		case '?':
			usage();
			exit(0);
		case 'D':
			if (strlen(options.conninfo) > 0)
				strncat(options.conninfo, " ",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, "dbname=",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, optarg,
						CONNINFO_LEN - strlen(options.conninfo));
			break;
		case 'H':
			if (strlen(options.conninfo) > 0)
				strncat(options.conninfo, " ",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, "host=",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, optarg,
						CONNINFO_LEN - strlen(options.conninfo));
			break;
		case 'P':
			if (strlen(options.conninfo) > 0)
				strncat(options.conninfo, " ",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, "port=",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, optarg,
						CONNINFO_LEN - strlen(options.conninfo));
			break;
		case 'U':
			if (strlen(options.conninfo) > 0)
				strncat(options.conninfo, " ",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, "user=",
						CONNINFO_LEN - strlen(options.conninfo));
			strncat(options.conninfo, optarg,
						CONNINFO_LEN - strlen(options.conninfo));
			break;
		case 'd':
			options.redis_key = optarg;
			break;
		case 'p':
			options.redis_port = atoi(optarg);
			break;
		case 's':
			options.redis_server =  optarg;
			break;
		case 'v':
			verbose_flag = 1;
			break;
		case 'w':
			workers = atoi(optarg);;
			break;
		}
	}

	threads = (pthread_t *) malloc(sizeof(pthread_t) * workers);

	for (c = 0; c < workers; c++) {
		int ret = pthread_create(&threads[c], NULL, &thread_main,
				(void *) &options);
		if (ret != 0) {
			perror("pthread_create");
			exit(1);
		}
	}

	lasttime = time(NULL);
	while (1) {
		thistime = time(NULL);

		if (stats_flag && thistime - lasttime >= 60) {
			printf("%s %d %d\n", ctime(&thistime), options.rcount,
					options.pcount);
			options.rcount = 0;
			options.pcount = 0;
			lasttime = thistime;
		}
		sleep(60);
	}

	return 0;
}
