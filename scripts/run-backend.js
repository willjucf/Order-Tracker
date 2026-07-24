// Dev backend launcher.
//
// Why this exists: on some Windows setups (including the primary dev machine),
// the bare `python` / `python3` commands are intercepted by the Windows Store
// "App execution alias" stubs, which print "Python was not found" and exit
// instead of running Python. When that happens `npm run dev:backend` silently
// fails, uvicorn never binds port 8420, and the Electron frontend ends up
// talking to whatever else is on that port (e.g. a stale installed main.exe).
//
// This launcher probes a list of candidate interpreters, verifies each one
// actually runs Python (not an alias stub), and then execs uvicorn with the
// first working one. Run from the `backend/` directory (see package.json).

const { spawnSync, spawn } = require('child_process');

// Candidate interpreters, most-specific first.
const CANDIDATES = [
  // Known-good absolute path on the primary dev machine (documented in CLAUDE.md).
  'C:\\Users\\wwj3d\\AppData\\Local\\Python\\bin\\python3.exe',
  // Windows Python launcher — bypasses the Store aliases.
  { cmd: 'py', preArgs: ['-3'] },
  'python3',
  'python',
];

function works(cmd, preArgs) {
  try {
    const res = spawnSync(cmd, [...preArgs, '-c', 'import sys; print(sys.executable)'], {
      encoding: 'utf8',
      timeout: 8000,
    });
    // Alias stubs exit non-zero and/or print nothing useful to stdout.
    return res.status === 0 && res.stdout && res.stdout.trim().length > 0;
  } catch {
    return false;
  }
}

function resolvePython() {
  for (const c of CANDIDATES) {
    const cmd = typeof c === 'string' ? c : c.cmd;
    const preArgs = typeof c === 'string' ? [] : c.preArgs || [];
    if (works(cmd, preArgs)) {
      return { cmd, preArgs };
    }
  }
  return null;
}

const py = resolvePython();
if (!py) {
  console.error(
    '[run-backend] No working Python interpreter found.\n' +
      '  Tried: ' +
      CANDIDATES.map((c) => (typeof c === 'string' ? c : `${c.cmd} ${c.preArgs.join(' ')}`)).join(', ') +
      '\n  Install Python or fix the Windows Store "App execution aliases" (Settings > Apps > Advanced app settings > App execution aliases).'
  );
  process.exit(1);
}

const args = [
  ...py.preArgs,
  '-m',
  'uvicorn',
  'main:app',
  '--host',
  '127.0.0.1',
  '--port',
  '8420',
  '--reload',
];

console.log(`[run-backend] Using interpreter: ${py.cmd} ${py.preArgs.join(' ')}`.trim());

const child = spawn(py.cmd, args, { stdio: 'inherit' });

// Forward termination so Ctrl+C / concurrently shutdown kills uvicorn cleanly
// (prevents the orphaned-backend-on-8420 problem this launcher guards against).
const forward = (sig) => {
  if (!child.killed) child.kill(sig);
};
process.on('SIGINT', () => forward('SIGINT'));
process.on('SIGTERM', () => forward('SIGTERM'));

child.on('exit', (code) => process.exit(code == null ? 1 : code));
