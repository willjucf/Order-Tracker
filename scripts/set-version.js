/**
 * Version bump script — updates the version number everywhere in one command.
 *
 * Usage:
 *   node scripts/set-version.js 1.2.0
 *   npm run version:set 1.2.0
 *
 * Updates:
 *   - package.json
 *   - backend/utils/config.py  (APP_VERSION)
 *   - build.bat                (installer filename in echo)
 *   - README.md                (title + installer filename)
 */

const fs = require('fs')
const path = require('path')

const newVersion = process.argv[2]

if (!newVersion || !/^\d+\.\d+\.\d+$/.test(newVersion)) {
  console.error('Usage: node scripts/set-version.js <major.minor.patch>')
  console.error('Example: node scripts/set-version.js 1.2.0')
  process.exit(1)
}

const root = path.join(__dirname, '..')

// Display version strips patch if it's 0: 1.2.0 -> 1.2, 1.2.3 -> 1.2.3
const parts = newVersion.split('.')
const displayVersion = parts[2] === '0' ? `${parts[0]}.${parts[1]}` : newVersion

let updated = []

// 1. package.json
const pkgPath = path.join(root, 'package.json')
const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'))
pkg.version = newVersion
fs.writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + '\n')
updated.push('package.json')

// 2. backend/utils/config.py
const configPath = path.join(root, 'backend', 'utils', 'config.py')
let config = fs.readFileSync(configPath, 'utf8')
config = config.replace(/APP_VERSION = "[^"]*"/, `APP_VERSION = "${newVersion}"`)
fs.writeFileSync(configPath, config)
updated.push('backend/utils/config.py')

// 3. build.bat
const batPath = path.join(root, 'build.bat')
let bat = fs.readFileSync(batPath, 'utf8')
bat = bat.replace(/Order Tracker Setup \d+\.\d+\.\d+\.exe/g, `Order Tracker Setup ${newVersion}.exe`)
fs.writeFileSync(batPath, bat)
updated.push('build.bat')

// 4. README.md
const readmePath = path.join(root, 'README.md')
let readme = fs.readFileSync(readmePath, 'utf8')
readme = readme.replace(/# Order Tracker v[\d.]+/, `# Order Tracker v${displayVersion}`)
readme = readme.replace(/Order Tracker Setup \d+\.\d+\.\d+\.exe/g, `Order Tracker Setup ${newVersion}.exe`)
fs.writeFileSync(readmePath, readme)
updated.push('README.md')

console.log(`\nVersion set to ${newVersion} (display: v${displayVersion})\n`)
updated.forEach(f => console.log(`  ✓ ${f}`))
console.log('\nFrontend components read from package.json automatically via Vite.')
console.log('Run npm run dev or build.bat to apply.\n')
