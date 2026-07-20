# Offline Domain Pack Marketplace

Milestone 11 provides a local catalog and an offline distribution lifecycle for
Domain Packs. It does not contact a registry or download packages.

## Catalog and compatibility

Catalog entries are deterministically classified as `installed`, `invalid`, or
`incompatible`. Compatibility metadata can declare minimum and maximum platform
versions and supported Knowledge Graph schema versions. Existing packs without
these optional fields remain compatible.

## Bundles

A bundle is a ZIP containing all required pack files plus
`bundle_manifest.json`. The manifest records pack id, version, exact file
inventory, and SHA-256 checksum for every file. Verification rejects missing or
extra files, checksum mismatches, and absolute or traversing paths.

## Installation safety

Installation is local and requires `confirm_install=True`. Files are written to
a staging directory, validated through the existing `DomainPackLoader`, and
atomically moved into the catalog. Existing packs are never overwritten.

Updates and removals remain separate future lifecycle actions rather than
implicit install behavior.
