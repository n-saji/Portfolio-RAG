# C++ Chat Application

## 1) Purpose and high-level behavior
This project is a terminal-based, real-time chat system implemented in C++ using POSIX sockets. It uses a single executable (`assignment1`) that can be launched in two modes:

- Server mode: accepts multiple client connections, maintains client state, and relays messages.
- Client mode: connects to a server, sends commands, receives messages, and renders status in the terminal.

The implementation uses blocking `select()` over file descriptors to multiplex STDIN and network sockets. There is no thread-per-client model; all concurrency is handled via `select()`.

## 2) Repository layout
- `src/assignment1.cpp`: program entry point; selects server or client mode based on CLI args.
- `src/server.cpp`: core server implementation (accept, relay, list, stats, block/blocked, buffering).
- `src/client.cpp`: core client implementation (user CLI, login, send, receive, block/refresh).
- `src/logger.cpp`: logging functions used across the app (stdout + logfile).
- `include/structures.h`: all shared data structures used for client/server state.
- `include/client.h`, `include/server.h`: minimal class wrappers for client/server.
- `include/logger.h`, `include/global.h`: logger API and constants.
- `Makefile`: builds all sources into the `assignment1` binary.
- `assignment1_package.sh`: packaging script for course submission.
- `logs/`: runtime log output; cleaned by `make clean`.
- `object/`: build artifacts.

## 3) Build and clean
The project is built with `g++` using C++11:

- Compile flags: `-g -I./include -std=c++11`
- Output binary: `assignment1`
- Object files are placed in `object/`

`make` builds the binary; `make clean` removes object files, the binary, editor backups in include, and log files in `logs/`.

## 4) Entry point and runtime selection
`src/assignment1.cpp` performs the following:

- Initializes logging with `cse4589_init_log(argv[2])`.
- Clears the log file by opening `LOGFILE` in write mode.
- Dispatches by the first CLI argument:
  - `argv[1] == "s"` -> start server (`server s(argv[2]);`).
  - `argv[1] == "c"` -> start client (`client c(argv[2]);`).
- Any other value prints `Invalid Argument`.

Important: the code assumes `argv[1]` and `argv[2]` exist. There is no argument count validation.

## 5) Shared data structures
The core runtime state is defined in `include/structures.h`:

- `blocked_clients`: minimal record of a blocked peer (hostname, IP, listening port).
- `buffer_info`: buffered message record (sender IP, destination IP, message text).
- `socket_info`: per-client state on the server side, including:
  - `fd` (socket descriptor), `port_number`, `host_name`, `ip_address`, `status`.
  - `message_count_sent`, `received_message_count` for statistics.
  - `blocked_clients_list` (per-client block list).
  - `buffer` (queue of pending messages for offline recipients).
- `network_info`: aggregate state for client or server:
  - `clients` (list of `socket_info`).
  - `block_list` (client-side block list used for local validation).
  - local `ip_address`, `port_number`, `listener_number`.

## 6) Logging behavior
`src/logger.cpp` implements two logging functions:

- `cse4589_init_log(port)`: constructs a log file path based on hostname and port.
- `cse4589_print_and_log(format, ...)`: writes formatted output to both stdout and the log file.

The log path is stored in a global `LOGFILE` buffer. The implementation expects `/proc/self/exe` to exist to locate the executable directory, which is Linux-specific. On macOS this path does not exist unless provided via compatibility layers. This is an environment constraint to note if running locally on macOS.

## 7) Server design and flow
### 7.1 Initialization
The server constructor in `src/server.cpp` performs:

- Hostname/IP discovery via `gethostname` + `gethostbyname`.
- TCP socket creation, bind to `INADDR_ANY:port`, and `listen()`.
- `select()` setup with two sources:
  - STDIN (commands like LIST, STATISTICS)
  - the listening socket (for incoming client connections)

### 7.2 Accepting new clients
When a new connection arrives:

- The server `accept()`s and adds the client fd to the master fd set.
- IP is extracted from the remote address.
- The server checks if the IP already exists in `info_struct.clients`:
  - If yes, the client is marked `logged-in` and fd is updated.
  - If no, a new `socket_info` is created and appended.
- The client sends its listening port immediately after connect; the server `recv()`s and stores it.

### 7.3 Login payload and buffered delivery
Immediately after accepting a client, the server builds a `LOGIN` payload that includes:

- A list of currently logged-in clients: `host_name ip port` repeated.
- Zero or more buffered messages (if any) for that IP.
  - Each buffered message is encoded as `BUFFER <from> <len> <message>`.

The server sends this payload to the newly connected client. It also logs buffered messages as `RELAYED` during this delivery.

### 7.4 Server-side command handling (STDIN)
The server listens for local commands on STDIN:

- `AUTHOR`: prints authorship message.
- `IP`: prints server IP.
- `PORT`: prints server port.
- `LIST`: prints list of logged-in clients sorted by port.
- `STATISTICS`: prints all clients sorted by port, including message counts and status.
- `BLOCKED <ip>`: prints block list for the client with the given IP; if IP not found or invalid, prints error.

### 7.5 Client message handling
For messages coming from connected clients, the server parses a string command and handles:

- `SEND <dest_ip> <message>`:
  - Uses sender fd to determine sender IP.
  - Checks whether the destination has blocked the sender.
  - If the destination is logged in and not blocking: forward immediately.
  - If the destination is logged out and not blocking: enqueue in destination buffer.
  - Updates message counters and logs `RELAYED` for immediate delivery.

- `BROADCAST <message>`:
  - Relays to all clients except sender.
  - Respects each recipient's block list; blocked recipients do not receive the broadcast.
  - If a recipient is logged out and not blocking, the message is buffered for them.
  - Logs `RELAYED` with the broadcast target as `255.255.255.255`.

- `REFRESH <client_ip>`:
  - Sends a fresh list of currently logged-in clients back to the requester.

- `BLOCK <ip>` / `UNBLOCK <ip>`:
  - Updates the block list belonging to the requesting client on the server.
  - The server uses these lists to filter `SEND` and `BROADCAST` delivery.

### 7.6 Disconnect behavior
If `recv()` returns 0 (connection closed):

- The server marks that client as `logged-out`, keeps the record, and closes the socket.
- The client remains in the server's list for statistics and buffering.

## 8) Client design and flow
### 8.1 Initialization
The client constructor in `src/client.cpp` performs:

- Hostname/IP discovery via `gethostname` + `gethostbyname`.
- Creates a TCP socket and `bind()`s it to the client listen port passed on the command line.
- Enters a command-processing loop that reads from STDIN.

### 8.2 Client commands (pre-login)
Before `LOGIN`, the client accepts:

- `AUTHOR`: prints authorship message.
- `IP`: prints client IP.
- `PORT`: prints client port.
- `LIST`: prints known list of logged-in clients stored locally.
- `LOGIN <server_ip> <server_port>`: establishes server connection.
  - Validates port and IP formatting before connecting.

After `LOGIN`, the client enters a new loop that multiplexes STDIN and the server socket via `select()`.

### 8.3 Client commands (post-login)
Once logged in, the client supports:

- `AUTHOR`, `IP`, `PORT`, `LIST`: same as pre-login; list is local cache.
- `REFRESH`: asks server for updated list of logged-in clients.
- `SEND <dest_ip> <message>`: sends a direct message.
- `BROADCAST <message>`: sends to all clients via server.
- `BLOCK <ip>`: locally tracks blocked IPs and asks server to enforce blocking.
- `UNBLOCK <ip>`: removes local block and asks server to update server-side list.
- `LOGOUT`: closes the server connection and returns to pre-login loop.
- `EXIT`: terminates the client process.

### 8.4 Receiving server messages
The client handles server payloads as follows:

- `SEND <from_ip> <to_ip> <message>`: printed as `RECEIVED` with sender info.
- `BROADCAST <from_ip> <message>`: printed as `RECEIVED` from sender.
- `LOGIN ...`: treated as a login response containing:
  - Optional buffered messages encoded as `BUFFER` segments.
  - A list of logged-in clients that is parsed into local cache.
- `REFRESH ...`: updates local cache of logged-in clients.

## 9) Message protocol summary
This protocol is a line-oriented plain-text protocol exchanged between client and server.

Client to server:
- `LOGIN <server_ip> <server_port>` is a local CLI command (network handshake occurs via `connect()` and then sending the client port).
- `REFRESH <client_ip>`
- `SEND <dest_ip> <message>`
- `BROADCAST <message>`
- `BLOCK <ip>` / `UNBLOCK <ip>`

Server to client:
- `LOGIN <host ip port> ... [BUFFER <from> <len> <message>] ...`
- `REFRESH <host ip port> ...`
- `SEND <from_ip> <to_ip> <message>`
- `BROADCAST <from_ip> <message>`

All parsing uses `strtok` and fixed-size buffers; messages are assumed to fit within 1KB or 4KB buffers depending on context.

## 10) Blocking and buffering semantics
- Blocking is enforced server-side based on per-client `blocked_clients_list`.
- Clients also keep a local `block_list` to validate commands, but the server is authoritative.
- Messages to logged-out clients are queued in the recipient's buffer and delivered on next login.

## 11) Packaging script
`assignment1_package.sh` is a course packaging helper. It expects the code to be located under `./pa1` and:

- Verifies `src/assignment1.c` or `src/assignment1.cpp` exists and contains `main()`.
- Verifies a `Makefile` exists in `./pa1`.
- Creates a tarball `TEAMNAME_pa1.tar` excluding the `logs` directory.

This script is not used in runtime execution but is part of the submission workflow.

## 12) Known constraints and assumptions
- Uses IPv4 only (AF_INET, `inet_pton`, `inet_ntoa`).
- Uses fixed-size buffers (1024 and 4096 bytes) without robust bounds checks for oversized input.
- Uses blocking `select()` and synchronous event handling; no threading.
- `logger.cpp` uses `/proc/self/exe`, which is Linux-specific.
- `assignment1.cpp` does not validate argument count; incorrect usage can cause undefined behavior.

## 13) Typical runtime usage (examples)
- Start server: `./assignment1 s 5000`
- Start client: `./assignment1 c 5001`
- Client login: `LOGIN 127.0.0.1 5000`
- Send: `SEND 127.0.0.1 hello`
- Broadcast: `BROADCAST hello everyone`

These commands map directly to the message protocol and server handling described above.
