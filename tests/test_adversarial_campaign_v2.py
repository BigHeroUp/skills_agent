from validation_lab.adversarial_campaign_v2 import run_adversarial_campaign_v2

def test_second_adversarial_campaign_passes_all_20_contracts():
    report=run_adversarial_campaign_v2()
    assert report["status"]=="passed"
    assert report["passed"]==report["total"]==20
    assert report["failed"]==0
