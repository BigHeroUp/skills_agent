from validation_lab.functional_benchmark import benchmark_cases, run_functional_benchmark


def test_beta_benchmark_has_required_size_and_domain_coverage():
    cases = benchmark_cases()

    assert len(cases) == 30
    assert len({case["domain"] for case in cases}) == 6
    assert len({case["id"] for case in cases}) == 30


def test_beta_benchmark_matches_independent_expected_contracts():
    report = run_functional_benchmark()

    assert report["status"] == "passed"
    assert report["passed"] == report["total"] == 30
    assert report["failed"] == 0
