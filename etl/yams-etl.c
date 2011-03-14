#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <getopt.h>
#include <netdb.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <string.h>
/*
#include <pthread.h>
*/
#include <time.h>

#define BUFFER_SIZE 8192
#define RESPONSE "HTTP/1.1 200 OK\nContent-Length: 0\nConnection: Close\r\n"

static int verbose_flag = 0;
static int stats_flag = 0;
static time_t last_time;

int get_request(int, char *);
/*
void *http_worker(void *);
*/
int run(unsigned short);
int start_listener(unsigned short);

int get_request(int socket, char *buffer)
{
	static int count = 0;
	time_t this_time;

	int received;
/*
	char *tmp1, *tmp2;
	int content_length;
*/
	int response_length = strlen(RESPONSE);

	do {
		++count;
		this_time = time(NULL);
		if (this_time - last_time >= 60) {
			char *time_str = ctime(&this_time);

			time_str[strlen(time_str) - 1] = '\0';
			printf("%s %d %0.1f requests per min\n", time_str, count,
					(double) count / ((double) (this_time - last_time) / 60.0));
			last_time = this_time;
			count = 0;
		}

		received = recv(socket, buffer, BUFFER_SIZE, 0);
		if (received == -1) {
			perror("recv");
			break;
		} else if (received == 0) {
			break;
		} else if (received <= BUFFER_SIZE) {
			if (verbose_flag)
				printf("%s\n", buffer);

			send(socket, RESPONSE, response_length, 0);

/*
			if (strstr(buffer, "Connection: Close") != NULL) {
				if (verbose_flag)
					printf("HTTP connection closed\n");
*/
				close(socket);
				break;
/*
			}
*/
		}
	} while (1);

	/* Get the Content-Length. */
/*
	tmp1 = strstr(buffer, "Content-Length: ") + 16;
	tmp2 = strstr(tmp1, "\n");
	*tmp2 = '\0';
	content_length = atoi(tmp1);
	printf("%d\n", content_length);
*/

	/* Get the entity body. */
/*
	tmp1 = strstr(tmp2 + 1, "\r\n") + 2;
	printf("%s\n", tmp1);
*/
	return 0;
}

/*
void *http_worker(void *data)
{
	int *socket = (int *) data;
	char buffer[BUFFER_SIZE + 1];

	memset(&buffer, 0, BUFFER_SIZE + 1);
	get_request(*socket, buffer);
	close(*socket);

	pthread_exit(NULL);

	return NULL;
}
*/

int run(unsigned short port)
{
	int listener_socket;
	socklen_t addrlen;
/*
	int rc;
*/

	listener_socket = start_listener(port);
	if (listener_socket < 1)
		return 1;

	addrlen = sizeof(struct sockaddr_in);
	while (1) {
		int socket;
		struct sockaddr_in sa;
		char buffer[BUFFER_SIZE + 1];
/*
		pthread_t tid;
*/

		socket = accept(listener_socket, (struct sockaddr *) &sa, &addrlen);
		if (socket == -1) {
			perror("accept");
			return 1;
		}

/*
		rc = pthread_create(&tid, NULL, &http_worker, &socket);
		if (rc != 0)
			perror("pthread_create");
*/

		memset(&buffer, 0, BUFFER_SIZE + 1);
		get_request(socket, buffer);
	}
	return 0;
}

int start_listener(unsigned short port)
{
	struct sockaddr_in sa;
	int listener_socket;
	int val = 1;
	struct protoent *protocol;

	printf("listening on port %d\n", port);

	memset(&sa, 0, sizeof(struct sockaddr_in));

	sa.sin_family = AF_INET;
	sa.sin_addr.s_addr = INADDR_ANY;
	sa.sin_port = htons(port);

	protocol = getprotobyname("TCP");
	if (!protocol)
		return -1;

	listener_socket = socket(PF_INET, SOCK_STREAM, protocol->p_proto);
	if (listener_socket < 0) {
		perror("socket");
		return -1;
	}

	setsockopt(listener_socket, SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val));

	if (bind(listener_socket, (struct sockaddr *) &sa,
			sizeof(struct sockaddr_in)) < 0) {
		perror("bind");
		return -1;
	}

	if (listen(listener_socket, 1) < 0) {
		perror("listen");
		return -1;
	}

	return listener_socket;
}

int main(int argc, char *argv[])
{
	int c;

	unsigned short port = 8888;

	printf("yams etl\n");

	while (1) {
		int option_index = 0;
		static struct option long_options[] = {
			{"stats", no_argument, &stats_flag, 1},
			{"verbose", no_argument, &verbose_flag, 1},
			{0, 0, 0, 0}
		};
		c = getopt_long(argc, argv, "l:sv", long_options, &option_index);
		if (c == -1)
			break;

		switch (c) {
		case 'l':
			port = (unsigned short) atoi(optarg);
			break;
		case 's':
			stats_flag = 1;
			break;
		case 'v':
			verbose_flag = 1;
			break;
		}
	}

	/* Start the listener. */
	last_time = time(NULL);
	run(port);

	return 0;
}
