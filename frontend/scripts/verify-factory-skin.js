const assert = require('assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const manifestPath = path.resolve(__dirname, '../public/orb-skins/factory-orb-v1.manifest.json');
const registryPath = path.resolve(__dirname, '../public/orb-skins/registry.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const assetPath = path.resolve(__dirname, `../public${manifest.path}`);
const asset = fs.readFileSync(assetPath);
const signature = asset.subarray(0, 8).toString('hex');
const sha256 = crypto.createHash('sha256').update(asset).digest('hex');

assert.equal(signature, '89504e470d0a1a0a', 'Factory asset must be a PNG');
assert.equal(sha256, manifest.sha256, 'Factory asset SHA-256 does not match its immutable manifest');
assert.equal(asset.readUInt32BE(16), manifest.width, 'Factory asset width does not match its manifest');
assert.equal(asset.readUInt32BE(20), manifest.height, 'Factory asset height does not match its manifest');
assert.equal(asset[24], 8, 'Factory asset must use 8-bit channels');
assert.equal(asset[25], 6, 'Factory asset must use PNG RGBA color type');
assert.equal(manifest.skin_id, 'orb_factory_default_v1');
assert.equal(manifest.display_name, 'O.R.B.S. Factory Default');
assert.equal(manifest.path, '/orb-skins/tuxorb.png');
assert.equal(manifest.mime_type, 'image/png');
assert.equal(manifest.color, 'RGBA, 8-bit');
assert.equal(manifest.provenance, 'Tuxedo Factory ORB asset supplied by the owner');
assert.equal(manifest.owner_editable, false);
assert.equal(manifest.immutable_default, true);
assert.equal(manifest.fallback_enabled, true);
assert.equal(registry.default_skin_id, manifest.skin_id);
assert.equal(registry.skins[manifest.skin_id].immutable, true);
assert.equal(registry.skins[manifest.skin_id].fallback, true);
assert.equal(registry.skins[manifest.skin_id].owner_editable, false);
assert.equal(registry.skins[manifest.skin_id].asset_path, manifest.path);
assert.equal(registry.skins[manifest.skin_id].display_name, manifest.display_name);

console.log(JSON.stringify({
  status: 'verified',
  skin_id: manifest.skin_id,
  sha256,
  dimensions: `${manifest.width}x${manifest.height}`,
  bytes: asset.length,
}, null, 2));
