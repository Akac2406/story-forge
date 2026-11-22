# v57: optional OpenCode key sync

- Settings > Sync between devices: new switch "Also sync my OpenCode key", off by default.
  When on, the key rides inside the existing sync payload, encrypted with the sync passphrase
  (AES-GCM, PBKDF2) before it leaves the device. A new device needs only the connector address
  and the passphrase.
- Newest choice wins across devices (keysAt timestamp): turning the switch off anywhere removes the key
  from the connector at the next sync; keys already on a device stay. Changing the key while the switch
  is on updates the other devices.
- The OpenRouter key never syncs.
- Backups now also leave out the sync passphrase and connector address; restoring a backup keeps this
  device's passphrase, connector, key and switch.
- VER 57, cache sf-v57.

Tests: tests/sync_keys_v57.py (two simulated devices, fake connector, no real key): 12 checks pass,
including "key never appears readable in any upload" and "wrong passphrase gets nothing". Full suite: 33 pass,
4 skipped (need screenshot/EPUB fixtures). No model calls. Not deployed.
