"""Local-only catalog, packaging, verification, and installation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from services.domain_pack_loader import DomainPackLoader

from .compatibility import check_compatibility
from .contracts import (
    BundleReceipt,
    InstallReceipt,
    MarketplaceEntry,
    PackLifecycleStatus,
)


BUNDLE_MANIFEST = "bundle_manifest.json"


class DomainPackMarketplace:
    def __init__(
        self,
        base_path: str | Path,
        *,
        platform_version: str = "2.0.0",
        graph_schema_version: int = 1,
    ):
        self.base_path = Path(base_path)
        self.loader = DomainPackLoader(self.base_path)
        self.platform_version = platform_version
        self.graph_schema_version = graph_schema_version

    def catalog(self) -> tuple[MarketplaceEntry, ...]:
        entries = []
        for available in self.loader.list_available_packs():
            pack_id = str(available["pack_id"])
            validation = self.loader.validate_pack(str(available["directory"]))
            manifest: dict[str, Any] = {}
            if validation["valid"]:
                manifest = self.loader.load_pack(str(available["directory"]))["manifest"]
            compatibility = check_compatibility(
                manifest,
                platform_version=self.platform_version,
                graph_schema_version=self.graph_schema_version,
            )
            if not validation["valid"]:
                status = PackLifecycleStatus.INVALID
            elif not compatibility.compatible:
                status = PackLifecycleStatus.INCOMPATIBLE
            else:
                status = PackLifecycleStatus.INSTALLED
            entries.append(MarketplaceEntry(
                pack_id=pack_id,
                name=str(available.get("name") or pack_id),
                version=str(available.get("version") or "0"),
                status=status,
                path=self.base_path / str(available["directory"]),
                compatibility=compatibility,
                validation_errors=tuple(validation["errors"]),
            ))
        return tuple(sorted(entries, key=lambda item: item.pack_id))

    def build_bundle(self, pack_id: str, output_path: str | Path) -> BundleReceipt:
        validation = self.loader.validate_pack(pack_id)
        if not validation["valid"]:
            raise ValueError("cannot bundle invalid Domain Pack: " + "; ".join(validation["errors"]))
        pack = self.loader.load_pack(pack_id)
        source = self.base_path / pack_id
        files = tuple(sorted(path for path in source.rglob("*") if path.is_file()))
        checksums = {
            path.relative_to(source).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }
        manifest = {
            "bundle_version": 1,
            "checksums": checksums,
            "pack_id": pack["pack_id"],
            "version": str(pack["manifest"].get("version") or "0"),
        }
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in files:
                archive.writestr(path.relative_to(source).as_posix(), path.read_bytes())
            archive.writestr(
                BUNDLE_MANIFEST,
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            )
        return BundleReceipt(
            pack_id=str(pack["pack_id"]),
            version=manifest["version"],
            bundle_path=destination,
            checksum=hashlib.sha256(destination.read_bytes()).hexdigest(),
            file_count=len(files),
        )

    def verify_bundle(self, bundle_path: str | Path) -> dict[str, Any]:
        path = Path(bundle_path)
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if BUNDLE_MANIFEST not in names:
                raise ValueError("bundle manifest is missing")
            for name in names:
                pure = PurePosixPath(name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise ValueError(f"unsafe bundle path: {name}")
            manifest = json.loads(archive.read(BUNDLE_MANIFEST))
            checksums = manifest.get("checksums")
            if not isinstance(checksums, dict):
                raise ValueError("bundle checksums are missing")
            payload_names = set(names) - {BUNDLE_MANIFEST}
            if payload_names != set(checksums):
                raise ValueError("bundle file inventory does not match checksums")
            for name, expected in sorted(checksums.items()):
                actual = hashlib.sha256(archive.read(name)).hexdigest()
                if actual != expected:
                    raise ValueError(f"bundle checksum mismatch: {name}")
        return manifest

    def install_bundle(
        self,
        bundle_path: str | Path,
        *,
        confirm_install: bool = False,
    ) -> InstallReceipt:
        if not confirm_install:
            raise ValueError("installation requires confirm_install=True")
        bundle = Path(bundle_path)
        manifest = self.verify_bundle(bundle)
        pack_id = str(manifest.get("pack_id") or "")
        if not pack_id or "/" in pack_id or "\\" in pack_id or pack_id in {".", ".."}:
            raise ValueError("invalid bundle pack_id")
        destination = self.base_path / pack_id
        if destination.exists():
            raise FileExistsError(f"Domain Pack already installed: {pack_id}")
        self.base_path.mkdir(parents=True, exist_ok=True)
        staging_root = Path(tempfile.mkdtemp(prefix=".domain-pack-", dir=self.base_path))
        staging_pack = staging_root / pack_id
        staging_pack.mkdir()
        try:
            with zipfile.ZipFile(bundle) as archive:
                for name in sorted(manifest["checksums"]):
                    target = staging_pack / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
            staged_validation = DomainPackLoader(staging_root).validate_pack(pack_id)
            if not staged_validation["valid"]:
                raise ValueError(
                    "installed bundle is not a valid Domain Pack: "
                    + "; ".join(staged_validation["errors"])
                )
            os.replace(staging_pack, destination)
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)
        return InstallReceipt(
            pack_id=pack_id,
            version=str(manifest.get("version") or "0"),
            installed_path=destination,
            bundle_checksum=hashlib.sha256(bundle.read_bytes()).hexdigest(),
        )
