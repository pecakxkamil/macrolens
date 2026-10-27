// Preload only for tests. Dependency installation and the app are unaffected.
const net = require("node:net");
const dns = require("node:dns");
const tls = require("node:tls");

let attempted = false;
function blocked() {
  attempted = true;
  process.exitCode = 1;
  // Avoid URLs/arguments, which could include secrets.
  throw new Error("Real network access is forbidden in tests; mock the request.");
}

net.Socket.prototype.connect = blocked;
dns.lookup = blocked;
tls.connect = blocked;
globalThis.fetch = blocked;

// A caught request error must still fail the test worker/process.
process.on("exit", () => {
  if (attempted) process.exitCode = 1;
});
