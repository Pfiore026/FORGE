from discovery.models import ExtractedField, FactAssertion
from discovery.services import detect_conflicts, field_review_task, inspect_upload

def test_native_pdf_is_routed_to_native_text_first():
    result = inspect_upload(b"%PDF-1.7 /Font /ToUnicode BT", "record.pdf", "application/pdf")
    assert result.recommended_route == "native_text_then_layout"

def test_field_without_citation_requires_review():
    field = ExtractedField(document_id="doc_a", field_name="incident_date", raw_value="2023-08-14", citations=[])
    task = field_review_task("case_a", field)
    assert task is not None
    assert task.priority == "high"

def test_conflicts_are_preserved_not_resolved():
    first = FactAssertion("case_a", "incident", "time", "21:42", ["field_a"])
    second = FactAssertion("case_a", "incident", "time", "22:17", ["field_b"])
    assert detect_conflicts([first, second]) == [(first, second)]
