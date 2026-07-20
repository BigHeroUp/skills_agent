import hashlib
import json
import zipfile

import pytest

from services.domain_pack_marketplace import (
    DomainPackMarketplace,
    PackLifecycleStatus,
    check_compatibility,
)


def _create_pack(base, pack_id="retail", compatibility=""):
    directory = base / pack_id
    directory.mkdir(parents=True)
    (directory / "domain_pack.yaml").write_text(
        "\n".join([
            f"pack_id: {pack_id}",
            "name: Retail",
            "version: 1.2.0",
            "description: Retail analytics",
            compatibility,
        ]),
        encoding="utf-8",
    )
    for name in (
        "patterns.json",
        "kpi_definitions.json",
        "strategy_rules.json",
        "questions.json",
        "terminology.json",
    ):
        (directory / name).write_text("[]", encoding="utf-8")
    (directory / "report_template.md").write_text("# Retail", encoding="utf-8")
    return directory


def test_catalog_reports_installed_invalid_and_incompatible_packs(tmp_path):
    _create_pack(tmp_path, "retail")
    _create_pack(tmp_path, "future", "min_platform_version: 99.0.0")
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "domain_pack.yaml").write_text("pack_id: invalid", encoding="utf-8")

    entries = DomainPackMarketplace(tmp_path, platform_version="2.0.0").catalog()
    statuses = {item.pack_id: item.status for item in entries}

    assert statuses == {
        "future": PackLifecycleStatus.INCOMPATIBLE,
        "invalid": PackLifecycleStatus.INVALID,
        "retail": PackLifecycleStatus.INSTALLED,
    }


def test_compatibility_checks_platform_and_graph_schema():
    compatibility = check_compatibility(
        {
            "min_platform_version": "2.1.0",
            "max_platform_version": "3.0.0",
            "graph_schema_versions": [2],
        },
        platform_version="2.0.0",
        graph_schema_version=1,
    )

    assert compatibility.compatible is False
    assert len(compatibility.reasons) == 2


def test_bundle_is_reproducibly_verified_and_installed_offline(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    _create_pack(source)
    bundle = tmp_path / "retail.pack.zip"
    receipt = DomainPackMarketplace(source).build_bundle("retail", bundle)
    target_marketplace = DomainPackMarketplace(destination)

    manifest = target_marketplace.verify_bundle(bundle)
    with pytest.raises(ValueError, match="confirm_install"):
        target_marketplace.install_bundle(bundle)
    installed = target_marketplace.install_bundle(bundle, confirm_install=True)

    assert manifest["pack_id"] == "retail"
    assert receipt.checksum == installed.bundle_checksum
    assert installed.installed_path.exists()
    assert target_marketplace.catalog()[0].status == PackLifecycleStatus.INSTALLED
    with pytest.raises(FileExistsError, match="already installed"):
        target_marketplace.install_bundle(bundle, confirm_install=True)


def test_bundle_verification_rejects_checksum_mismatch(tmp_path):
    bundle = tmp_path / "tampered.zip"
    checksums = {"domain_pack.yaml": hashlib.sha256(b"original").hexdigest()}
    manifest = {
        "bundle_version": 1,
        "pack_id": "retail",
        "version": "1",
        "checksums": checksums,
    }
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("domain_pack.yaml", b"tampered")
        archive.writestr("bundle_manifest.json", json.dumps(manifest))

    with pytest.raises(ValueError, match="checksum mismatch"):
        DomainPackMarketplace(tmp_path / "packs").verify_bundle(bundle)


def test_bundle_verification_rejects_path_traversal(tmp_path):
    bundle = tmp_path / "unsafe.zip"
    payload = b"unsafe"
    manifest = {
        "bundle_version": 1,
        "pack_id": "retail",
        "version": "1",
        "checksums": {"../outside": hashlib.sha256(payload).hexdigest()},
    }
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("../outside", payload)
        archive.writestr("bundle_manifest.json", json.dumps(manifest))

    with pytest.raises(ValueError, match="unsafe bundle path"):
        DomainPackMarketplace(tmp_path / "packs").verify_bundle(bundle)
