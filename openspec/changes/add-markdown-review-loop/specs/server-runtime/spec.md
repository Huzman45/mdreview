## ADDED Requirements

### Requirement: Loopback-only binding
The service SHALL bind exclusively to the loopback interface. It MUST NOT listen on
a routable address, because it carries no authentication of any kind.

#### Scenario: Server binds to loopback
- **WHEN** the server starts with default configuration
- **THEN** it listens on `127.0.0.1` at the configured port
- **AND** it does not accept connections addressed to any other local interface

#### Scenario: Non-loopback host is refused
- **WHEN** the server is asked to bind to a host that is not a loopback address
- **THEN** startup fails with an explanatory error
- **AND** no socket is opened

### Requirement: Persistent local storage
The service SHALL persist all state in a single SQLite database in the user's data
directory, so that state survives process restarts.

#### Scenario: Database is created on first run
- **WHEN** the server starts and no database file exists
- **THEN** the parent directory is created if absent
- **AND** an empty database is initialised at `~/.local/share/mdreview/db.sqlite`

#### Scenario: Write-ahead logging is enabled
- **WHEN** the server opens the database
- **THEN** the journal mode is set to WAL
- **AND** foreign key enforcement is enabled

#### Scenario: State outlives the process
- **WHEN** a document has been submitted and the server is then restarted
- **THEN** the document and all of its versions and comments are still readable

### Requirement: Schema migration on startup
The service SHALL version its schema using `PRAGMA user_version` and apply any
outstanding migration steps in order at startup, without an external migration tool.

#### Scenario: Fresh database is migrated to current schema
- **WHEN** the server starts against a database whose `user_version` is 0
- **THEN** every migration step is applied in order
- **AND** `user_version` equals the number of defined steps

#### Scenario: Already-current database is untouched
- **WHEN** the server starts against a database already at the current version
- **THEN** no migration step is executed

#### Scenario: Partially migrated database is brought forward
- **WHEN** the server starts against a database at an older version
- **THEN** only the steps after that version are applied, in order

### Requirement: On-demand server start
The CLI SHALL start the server itself when no server is reachable, so that the user
never has to install or manage a background service.

#### Scenario: CLI starts a server when none is running
- **WHEN** a CLI command needs the API and the connection is refused
- **THEN** the CLI spawns a detached server process
- **AND** waits until the health endpoint responds before continuing
- **AND** completes the original command successfully

#### Scenario: CLI reuses a running server
- **WHEN** a CLI command needs the API and a server is already reachable
- **THEN** no additional server process is spawned

#### Scenario: Unstartable server reports clearly
- **WHEN** the CLI spawns a server and the health endpoint does not respond within
  the startup timeout
- **THEN** the command fails with a message naming the port and the log file location

### Requirement: Health endpoint
The service SHALL expose an unauthenticated health endpoint used to detect readiness.

#### Scenario: Health check reports readiness
- **WHEN** a client requests the health endpoint on a started server
- **THEN** the response status is 200
- **AND** the body reports the application version and the schema version
