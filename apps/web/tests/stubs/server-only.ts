// Vitest runs outside Next's Server/Client Component compiler boundary. Production code keeps the
// real server-only import; this test-only shim lets unit tests exercise server configuration.
export {};
