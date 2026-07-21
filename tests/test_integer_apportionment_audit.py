from scripts.audit_integer_apportionment import analyze


def test_apportionment_audit_counts_contracts_and_reports_bound() -> None:
    report = {
        "rows": [
            {
                "reference_contracts": [
                    {
                        "counts": [40_000, 25_536],
                        "quantization_tv": 0.01,
                        "contract_truncation_kl_nats": 0.2,
                    },
                    {
                        "counts": [32_768, 32_768],
                        "quantization_tv": 0.02,
                        "contract_truncation_kl_nats": 0.3,
                    },
                ]
            }
        ]
    }

    result = analyze(report)

    assert result["trials"] == 1
    assert result["contracts"] == 2
    assert result["candidate_counts"] == [2]
    assert result["mass_bits"] == [16]
    assert result["apportionment"]["max_tv_upper_bound"] == 1 / 32768
    assert result["context"]["mean_full_logit_quantization_tv"] == 0.015
