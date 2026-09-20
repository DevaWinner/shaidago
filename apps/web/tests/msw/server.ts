import { setupServer } from "msw/node";

// Feature tests register only the deterministic handlers they need. An unhandled request must
// fail the test so an undocumented browser/API path is never silently accepted.
export const server = setupServer();
