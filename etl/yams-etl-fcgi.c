#include <fcgi_stdio.h>

#include <stdlib.h>
#include <string.h>
#include <syslog.h>

#include <hiredis/hiredis.h>

#define BUFFER_SIZE 8191
#define HOSTNAME_LEN 255
#define KEY_LEN 255

int main()
{
	int i;
	char *str;
	int content_length;
	char buffer[BUFFER_SIZE + 1];

	/* Default values for Redis connection information. */
	char redis_server[HOSTNAME_LEN + 1] = "localhost";
	int redis_port = 6379;
	char redis_key[KEY_LEN + 1] = "yamsetl";

	redisContext *c;
	redisReply *reply;

	str = getenv("REDIS_SERVER");
	if (str != NULL)
		strncpy(redis_server, str, HOSTNAME_LEN);

	str = getenv("REDIS_PORT");
	if (str != NULL)
		redis_port = atoi(str);

	str = getenv("REDIS_KEY");
	if (str != NULL)
		strncpy(redis_key, str, KEY_LEN);

	/*
	 * Open a connection to Redis once the FastCGI service starts for
	 * the life of the service.
	 */
	c = redisConnect(redis_server, redis_port);
	if (c->err) {
		printf("yams-etl-fastcgi error: %s\n", c->errstr);
		return 1;
	}

	while (FCGI_Accept() >= 0) {
		/* Create a minimal HTTP response. */
		printf("\r\n");

		if (strcmp(getenv("REQUEST_METHOD"), "POST") == 0) {
			/* Get the POST data. */
			str = getenv("CONTENT_LENGTH");
			if (str != NULL)
				content_length = atoi(str);
			else
				content_length = -1;

			i = 0;
			while (i < content_length && i < BUFFER_SIZE)
				buffer[i++] = getchar();
			buffer[i] = '\0';

			/* Push the POST data to Redis. */
			reply = redisCommand(c, "LPUSH %s \"%s\"", redis_key, buffer);
			/* TODO: Handle failed LPUSH. */
			freeReplyObject(reply);
		}
	}

	return 0;
}
