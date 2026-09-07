# Deprecated: standalone `discovery/` package

The `discovery/` Python package added earlier on this branch (`models.py`,
`services.py`, `__init__.py`, and `tests/test_discovery.py`) introduced a parallel
data model that does not match the application's actual architecture in `app.py`
and `services/case_service.py` (for example, `DocumentService`, `FactCardService`,
`ContradictionService`, and `AuditService`).

That package has been superseded by:

- `services/interrogatory_service.py`
- `services/deposition_service.py`
- `services/discovery_rules.py`
- `pages/6_Discovery_Workspace.py`

The evidence-first principles from the earlier package -- immutable originals,
source citations with page/quote references, never silently resolving conflicting
facts, and mandatory human review for uncertain values -- remain the standard. They
are now expressed through the existing `FactCardService` (`source_page`,
`source_quote`, `confidence`, multi-source strength) and `ContradictionService`
instead of a separate model.

Recommendation: delete the `discovery/` package and `tests/test_discovery.py` in a
follow-up cleanup commit once this integration is verified in the running app.
