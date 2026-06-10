"""veridoc-audit database migrations (Alembic revisions).

0001_audit_log creates the append-only ``audit_log`` table (D-06 columns incl. nullable
agent_decision/agent_confidence), the BEFORE UPDATE OR DELETE immutability trigger, and a
least-privilege grant comment. Each revision also exposes ``apply(connection)`` /
``revert(connection)`` so tests (and tooling without a full Alembic env) can run the DDL
directly against a SQLAlchemy connection.
"""
