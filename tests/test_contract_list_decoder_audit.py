from scripts.audit_contract_list_decoder import recover_payload_candidates


def test_payload_candidates_do_not_use_expected_payload_oracle() -> None:
    payloads, limited, size = recover_payload_candidates([(1, 2), (3,)], 0, 10)
    assert payloads == {b"\x01\x03", b"\x02\x03"}
    assert not limited and size == 2


def test_payload_candidate_limit_is_explicit() -> None:
    payloads, limited, size = recover_payload_candidates([(1, 2), (3, 4)], 0, 3)
    assert not payloads and limited and size == 4
