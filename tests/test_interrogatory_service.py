from services.interrogatory_service import InterrogatoryService, MissingDiscoveryVariableError
from services.deposition_service import DepositionTopicService
from services.discovery_rules import get_rule, rule_status, all_verified_keys


def test_topic_requires_target_party():
    svc = InterrogatoryService()
    try:
        svc.propose_topic("case_a", "user_a", target_party="", category="date_or_sequence",
                           factual_topic="When did the repair occur?", source_fact_ids=["fact_1"])
        assert False, "expected MissingDiscoveryVariableError"
    except MissingDiscoveryVariableError:
        pass


def test_topic_requires_source_fact():
    svc = InterrogatoryService()
    try:
        svc.propose_topic("case_a", "user_a", target_party="Acme Corp", category="date_or_sequence",
                           factual_topic="When did the repair occur?", source_fact_ids=[])
        assert False, "expected MissingDiscoveryVariableError"
    except MissingDiscoveryVariableError:
        pass


def test_subpart_count_accumulates_per_target():
    svc = InterrogatoryService()
    svc.propose_topic("case_a", "user_a", "Acme Corp", "date_or_sequence", "topic one", ["fact_1"], discrete_subpart_count=3)
    svc.propose_topic("case_a", "user_a", "Acme Corp", "communication", "topic two", ["fact_2"], discrete_subpart_count=4)
    assert svc.subpart_count("case_a", "Acme Corp") == 7


def test_deposition_topic_links_back_to_interrogatory():
    int_svc = InterrogatoryService()
    dep_svc = DepositionTopicService()
    topic = int_svc.propose_topic("case_a", "user_a", "Acme Corp", "identity_of_person",
                                   "who performed the repair", ["fact_1"])
    dep_topic = dep_svc.add_topic("case_a", "user_a", "Repair technician", ["fact_1"])
    int_svc.link_deposition_topic(topic.id, dep_topic.id)
    dep_svc.link_interrogatory_topic(dep_topic.id, topic.id)
    assert dep_topic.id in int_svc.get(topic.id).related_deposition_topic_ids
    assert topic.id in dep_svc.get(dep_topic.id).related_interrogatory_topic_ids


def test_verified_rule_is_quoted_with_source():
    text = get_rule("FRCP 33(a)(1)")
    assert "25 written interrogatories" in text
    assert "law.cornell.edu" in text
    assert rule_status("FRCP 33(a)(1)") == "verified_excerpt"


def test_deposition_rules_are_verified():
    assert rule_status("FRCP 30(d)(1)") == "verified_excerpt"
    assert rule_status("FRCP 30(a)(2)(A)(i)") == "verified_excerpt"
    assert "1 day of 7 hours" in get_rule("FRCP 30(d)(1)")
    assert "10 depositions" in get_rule("FRCP 30(a)(2)(A)(i)")


def test_production_and_admission_rules_are_verified():
    assert rule_status("FRCP 34(b)(2)(A)") == "verified_excerpt"
    assert rule_status("FRCP 36(a)(3)") == "verified_excerpt"
    assert "30 days" in get_rule("FRCP 34(b)(2)(A)")
    assert "30 days" in get_rule("FRCP 36(a)(3)")


def test_unverified_local_rules_decline_to_guess():
    text = get_rule("D.Me. Local Rules")
    assert "I do not have a verified excerpt" in text
    assert rule_status("D.Me. Local Rules") == "not_yet_verified"


def test_all_verified_keys_returns_only_verified_entries():
    keys = all_verified_keys()
    assert "FRCP 33(a)(1)" in keys
    assert "D.Me. Local Rules" not in keys
