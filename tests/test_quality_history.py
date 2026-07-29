from services.platform.persistence import PlatformRepository

def test_quality_snapshots_are_tenant_scoped_and_ordered(tmp_path):
    repo=PlatformRepository(f"sqlite:///{tmp_path/'quality.db'}")
    first=repo.create_tenant_with_admin("First","a@a.test","hash")
    second=repo.create_tenant_with_admin("Second","b@b.test","hash")
    repo.record_quality_snapshot(first["tenant_id"],{"passed":9})
    repo.record_quality_snapshot(first["tenant_id"],{"passed":10})
    repo.record_quality_snapshot(second["tenant_id"],{"passed":1})
    assert [x["payload"]["passed"] for x in repo.list_quality_snapshots(first["tenant_id"])]==[10,9]
