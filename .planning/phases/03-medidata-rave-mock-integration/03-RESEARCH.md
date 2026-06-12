# Phase 3: Medidata Rave Mock Integration — Research

**Researched:** 2026-06-12
**Domain:** Medidata RWS / CDISC ODM-XML / FastAPI stateful mock / HMAC webhook
**Confidence:** MEDIUM (MDRWS contract inferred from public client libs; full official API spec is behind partner wall per CON-medidata-partner)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Port (ABC) over MDRWS + single HTTP adapter (mirrors `SourceAdapter` / `KMSKeyring` idiom). Same adapter used against mock AND production (base-URL/config change only).
- **D-02:** Rave mock is a real FastAPI HTTP server emulating MDRWS over the network.
- **D-03:** Mock emulates real RWS URL conventions, HTTP Basic auth, and ODM-based error semantics — scoped to only the endpoints in use.
- **D-04:** Mock is stateful per-run (query/flag/PD state persisted so open-then-update is testable end-to-end). Exact store is discretionary.
- **D-05:** ODM-XML on the wire (faithful to MDRWS); adapter parses into typed Pydantic Rave DTOs at the boundary. ODM-XML is an adapter-internal detail — agents never see it.
- **D-06:** Rave DTOs are a distinct eCRF model, NOT normalized to FHIR.
- **D-07:** Rave `Subject` ID pseudonymized with `veridoc-pseudonym` mechanism (D-12/D-14).
- **D-08:** EMR↔Rave correlation via site-level mapping OUTSIDE agent code.
- **D-09:** Real HTTP webhook receiver in `rave-integration` service; mock POSTs as Rave would. Authenticates + audits + enqueues RQ job.
- **D-10:** Receiver maps event type → named pipeline action → typed RQ job on `rave-events` queue → stub consumer (no-op + `rave:webhook:dispatched` audit). Phase 4 replaces the stub.
- **D-11:** New `veridoc-rave` lib (Port ABC + Rave DTOs + ODM parse/serialize + HTTP adapter). New `rave-integration` service (webhook receiver + RQ worker). Rave mock as separate Helm-deployed service. Kind smoke test in CI.

### Locked project decisions carried forward
- **DEC-rq-json-serializer** — JSONSerializer only; no pickle; all job args must be JSON-serializable primitives.
- **DEC-audit-same-txn-writer** — `append_audit` joins caller's session, NEVER commits. Caller owns the commit.
- **DEC-tenancy-fail-closed** — `current_tenant()` raises `TenancyError` when unset. Services inherit this posture.
- **DEC-auth-direct-jwt** — RS256/MFA via `pyjwt[crypto]` + `jwcrypto`. `rave-integration` API surface inherits this.
- **DEC-supply-chain-gate** — every new `uv add` requires a PACKAGE-LEGITIMACY.md row approved by the human reviewer before install.

### Claude's Discretion
- Exact mock state store (in-memory dict vs lightweight persistence) — provided D-04 (stateful, per-run) holds.
- ODM-XML parse/serialize library — subject to `docs/validation/PACKAGE-LEGITIMACY.md` vetting.
- Internal module layout of `veridoc-rave`; exact DTO field sets within each typed model.
- Webhook auth detail (shared-secret HMAC vs HTTP Basic), as long as it is authenticated and audited.

### Deferred Ideas (OUT OF SCOPE)
- Production MDRWS access + Technology-Partner integration (CON-medidata-partner).
- Full query-lifecycle automation (Phase 6 Query Agent).
- Orchestrated handling of webhook events (Phase 4 replaces the stub consumer).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RAVE-01 | Medidata Rave integration against MDRWS mock behind abstraction layer: READ (subject data, CRF field values with audit trail, query status, protocol deviations, randomization, freeze/lock status), WRITE (open discrepancy notes, update query status, set per-field SDV flags, flag protocol deviations), WEBHOOKS (new data entry / SAE submission / query response triggers pipeline action). Abstraction layer isolates MDRWS contract so mock can be swapped for production. | §Standard Stack defines `veridoc-rave` lib shape. §Architecture Patterns maps each READ/WRITE/WEBHOOK operation to concrete URL + ODM payload. §Code Examples show Port ABC signature, DTO fields, ODM parse, webhook receiver. |
</phase_requirements>

---

## Summary

Phase 3 delivers a bidirectional MDRWS integration exercised against a Rave mock. The work divides cleanly into three deliverables: (1) the `veridoc-rave` shared library (Port ABC + typed Pydantic Rave DTOs + ODM-XML parse/serialize + HTTP adapter), (2) the `rave-integration` service (FastAPI webhook receiver + RQ worker with stub consumer), and (3) the Rave mock (stateful FastAPI server emulating MDRWS endpoints).

The MDRWS surface is accessible via public client library documentation (rwslib, Medidata.RWS.NET). Full official API docs are behind the Medidata Technology Partner portal (CON-medidata-partner). This is expected; the design decision (D-01/D-03) accounts for it by building the HTTP adapter against the same public surface the mock emulates, and deferring any partner-wall features to production swap. The public sources are sufficient to implement all READ/WRITE/WEBHOOK operations listed in RAVE-01 with production-faithful URL conventions, Basic auth, and ODM-1.3 payloads.

The ODM-XML parse/serialize choice is the main discretionary technical decision. After evaluating odmlib (inactive/low maintenance), xmltodict (no namespace awareness), raw lxml (verbose but stdlib-style), and `pydantic-xml` (active, 408K downloads/week, 2.21.0 released May 2026), `pydantic-xml` + `lxml` is the recommended choice: it produces typed Pydantic models directly from ODM-XML with namespace support, integrates with the existing Pydantic v2 stack, and avoids the vetting burden of `odmlib`. This satisfies D-05 cleanly and will pass the PACKAGE-LEGITIMACY.md gate.

**Primary recommendation:** Clone `ingestion-service` for `rave-integration` and for the mock service. Mirror `SourceAdapter` ABC for the Rave Port. Use `pydantic-xml` + `lxml` for ODM parsing. Use HMAC-SHA256 (shared secret, `X-Rave-Signature` header, `hmac.compare_digest`) for webhook auth.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MDRWS READ (subject/CRF/query/PD/randomization/freeze-lock) | `veridoc-rave` lib (HTTP adapter) | `rave-integration` service calls the lib | Adapter encapsulates the MDRWS HTTP + ODM details; adapter-internal, never exposed to agents |
| ODM-XML parse → typed Rave DTOs | `veridoc-rave` lib (boundary) | — | D-05: ODM is adapter-internal; agents consume typed objects only |
| MDRWS WRITE (open query, update status, SDV flag, PD flag) | `veridoc-rave` lib (HTTP adapter) | `rave-integration` service calls the lib | Same seam as READ — same adapter, same config swap |
| Subject ID pseudonymization | `veridoc-rave` lib (adapter layer) | `veridoc-pseudonym` lib | D-07: pseudonymization at the Rave boundary, same as ingestion boundary |
| Webhook receive + auth + audit + enqueue | `rave-integration` service (FastAPI endpoint) | `veridoc-audit` lib, `rq` | D-09: receiver is the HTTP seam; audit and enqueue are synchronous in the handler |
| RQ job dispatch (stub consumer) | `rave-integration` service (RQ worker) | `veridoc-audit` lib | D-10: worker is the stub Phase 4 replaces; audit confirms dispatch |
| Rave mock (stateful MDRWS emulator) | Rave mock service (separate FastAPI app) | In-memory / per-run store | D-02/D-03/D-04: mock is a real HTTP server deployed separately (not in-process) |
| Audit trail (all events) | `veridoc-audit` lib (PostgreSQL) | Caller's session | PLAT-02 / D-05: every query-lifecycle + webhook event must hit the audit chain same-transaction |
| EMR↔Rave subject correlation | Site-level mapping (config/data) | Outside agent code | D-08: not in Phase 3 scope; seam identified for Phase 5 |
| Deploy + CI smoke test | Helm chart + GitHub Actions kind | Taskfile | D-11: mirrors Phase 2 pattern exactly |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | latest (already APPROVED) | HTTP framework for `rave-integration` service + Rave mock service | Already in workspace, APPROVED Phase 1 |
| uvicorn | latest (already APPROVED) | ASGI server | Already in workspace, APPROVED Phase 1 |
| pydantic v2 | latest (already APPROVED) | Rave DTOs + service config | Already in workspace, APPROVED Phase 1 |
| pydantic-settings | latest (already APPROVED) | Settings for two new services | Already in workspace, APPROVED Phase 1 |
| sqlalchemy 2.x | latest (already APPROVED) | `rave-integration` audit DB session | Already in workspace, APPROVED Phase 1 |
| psycopg (v3) | latest (already APPROVED) | Postgres driver | Already in workspace, APPROVED Phase 1 |
| redis | latest (already APPROVED) | RQ queue connection | Already in workspace, APPROVED Phase 1 |
| rq | latest (already APPROVED) | `rave-events` job queue with JSONSerializer | Already in workspace, APPROVED Phase 2 |
| httpx | latest (already APPROVED) | HTTP adapter outbound calls to MDRWS / mock; also test transport | Already in workspace, APPROVED Phase 1 |

### New — Subject to PACKAGE-LEGITIMACY.md Vetting
| Library | Version | Purpose | Why Chosen |
|---------|---------|---------|------------|
| pydantic-xml | 2.21.0 | ODM-XML parse → typed Pydantic v2 Rave DTOs + serialize DTOs → ODM-XML for POSTs | Active (408K downloads/week, v2.21.0 May 2026). Uses lxml if installed, falls back to stdlib ElementTree. Integrates with existing Pydantic v2 stack. Handles CDISC + mdsol namespace extensions correctly when lxml is used. Lower vetting burden than odmlib. [ASSUMED — must pass PACKAGE-LEGITIMACY.md gate before `uv add`] |
| lxml | 6.1.1 | XML backend for pydantic-xml; namespace-aware XPath; required for correct mdsol namespace handling | De-facto standard C-backed Python XML library (lxml.de). Required as explicit dep when pydantic-xml must parse multi-namespace ODM (without lxml, pydantic-xml falls back to stdlib which has namespace issues). [ASSUMED — must pass PACKAGE-LEGITIMACY.md gate before `uv add`] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-xml + lxml | odmlib | odmlib is inactive/discontinued per Libraries.io; incomplete ClinicalData support per project README. Rejected. |
| pydantic-xml + lxml | xmltodict | xmltodict flattens XML to dicts, loses namespace awareness; does not produce typed Pydantic models at boundary. |
| pydantic-xml + lxml | stdlib `xml.etree.ElementTree` directly | Valid fallback; zero new dependency; more verbose hand-written parsing code in the adapter. Acceptable if pydantic-xml fails PACKAGE-LEGITIMACY.md gate. |
| HMAC-SHA256 webhook auth | HTTP Basic webhook auth | Basic is simpler but weaker; HMAC-SHA256 with `hmac.compare_digest` is the industry standard for webhook auth and matches what production Rave integrations use. |

**Fallback for ODM parsing:** If `pydantic-xml` fails the PACKAGE-LEGITIMACY.md gate, the planner must substitute hand-written `xml.etree.ElementTree` (stdlib) parsing in the adapter. `lxml` alone (no pydantic-xml) is also acceptable — same library without the Pydantic binding layer. The Port and DTO interfaces are unchanged; only the parsing implementation inside the adapter changes.

**Installation (new packages only — after PACKAGE-LEGITIMACY.md approval):**
```bash
uv add pydantic-xml lxml --package veridoc-rave
```

**Version verification:**
```bash
# Verified on 2026-06-12:
# pydantic-xml: 2.21.0 (released 2026-05-17, github.com/dapper91/pydantic-xml, ~408K downloads/week)
# lxml: 6.1.1 (released 2026-05-18, github.com/lxml/lxml, de-facto standard)
```

---

## Package Legitimacy Audit

> Required: phase installs `pydantic-xml` and `lxml` as new packages.
> slopcheck was not available in this environment — all new packages are tagged `[ASSUMED]` below.
> The planner must gate each install behind a `checkpoint:human-verify` task (PACKAGE-LEGITIMACY.md row) before `uv add` runs.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| pydantic-xml | PyPI | ~4 years (first release 2022) | ~408K/week | github.com/dapper91/pydantic-xml | [ASSUMED — slopcheck unavailable] | Flagged — planner must add checkpoint:human-verify (PACKAGE-LEGITIMACY.md row) before `uv add` |
| lxml | PyPI | ~18 years | tens of millions/week (de-facto standard) | github.com/lxml/lxml | [ASSUMED — slopcheck unavailable] | Flagged — planner must add checkpoint:human-verify (PACKAGE-LEGITIMACY.md row) before `uv add` |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable)
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. Both packages are tagged `[ASSUMED]`. The planner must gate each install behind a `checkpoint:human-verify` task (PACKAGE-LEGITIMACY.md row entry) before executing `uv add`. Note: both packages are long-established, high-download PyPI projects — slopcheck is expected to pass once available.*

---

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         PHASE 3 DATA FLOW                           │
│                                                                     │
│  ┌──────────────┐   GET /studies/{study}/subjects/{subj}/datasets   │
│  │  rave-       │──────────────────────────────────────────────────►│
│  │  integration │◄─────────────────────── ODM XML (Subject/CRF) ───│
│  │  service     │   POST /webservice.aspx?PostODMClinicalData        │
│  │              │──────────────────────────────────────────────────►│
│  │  (FastAPI    │◄───────────────────────── RWSPostResponse XML ────│
│  │   + RQ       │                                                    │
│  │   worker)    │                     ┌──────────────────────────┐   │
│  │              │◄── POST /webhook ───│     Rave Mock Service    │   │
│  │  webhook     │    (HMAC-signed)    │  (FastAPI, stateful)     │   │
│  │  receiver    │                     │  - Subjects store        │   │
│  │  endpoint    │                     │  - Queries store         │   │
│  └──────────────┘                     │  - SDV flags store       │   │
│         │                             │  - PD flags store        │   │
│         │  1. append_audit()          │  - Randomization store   │   │
│         │     (same-txn)             └──────────────────────────┘   │
│         │  2. queue.enqueue()                                        │
│         │     ("rave-events", JSONSerializer)                        │
│         ▼                                                            │
│  ┌─────────────────┐    ┌───────────────┐    ┌──────────────────┐   │
│  │  PostgreSQL      │    │  Redis        │    │  RQ Worker       │   │
│  │  (audit_log)     │    │  (rave-events │    │  (stub consumer) │   │
│  │  hash-chained    │    │   queue)      │◄───│  + audit commit  │   │
│  └─────────────────┘    └───────────────┘    └──────────────────┘   │
│                                                                     │
│  veridoc-rave lib (adapter-internal):                               │
│    RavePort ABC ──► MdrwsHttpAdapter ──► HTTP Basic auth            │
│                          │                                          │
│                     ODM-XML ◄──── lxml + pydantic-xml ────► DTOs   │
│                                                                     │
│  Typed Rave DTOs consumed by Phase 5 agents (not exposed to mock): │
│    Subject, CrfFieldValue (+ AuditRecord), QueryStatus,            │
│    ProtocolDeviation, Randomization, FreezeLockStatus              │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
libs/veridoc-rave/
├── pyproject.toml                   # workspace member; depends on veridoc-pseudonym
└── src/veridoc_rave/
    ├── __init__.py                  # exports RavePort, MdrwsHttpAdapter, RaveProfile, all DTOs
    ├── port.py                      # RavePort ABC (mirrors SourceAdapter) + RaveProfile dataclass
    ├── dtos.py                      # Pydantic v2 Rave DTOs: Subject, CrfFieldValue, QueryStatus,
    │                                #   ProtocolDeviation, Randomization, FreezeLockStatus,
    │                                #   DiscrepancyNoteWrite (write payload)
    ├── odm.py                       # ODM-XML parse (lxml + pydantic-xml) + serialize helpers
    │                                #   adapter-internal; never imported by agents
    └── adapters/
        └── mdrws_http.py            # MdrwsHttpAdapter: concrete HTTP adapter (httpx sync client)
                                     #   pointed at mock URL in tests/CI, real URL in production

services/rave-integration/
├── Dockerfile                       # clone of ingestion-service/Dockerfile (no Tesseract)
├── pyproject.toml                   # depends on veridoc-rave, veridoc-audit, veridoc-auth,
│                                    #   veridoc-tenancy, fastapi, uvicorn, rq
└── src/rave_integration/
    ├── __init__.py
    ├── config.py                    # Settings (clone of ingestion_service/config.py)
    ├── db.py                        # make_engine + make_session_factory (verbatim clone)
    ├── main.py                      # FastAPI app + lifespan (RQ queue with JSONSerializer)
    ├── worker_main.py               # rq worker rave-events --serializer JSONSerializer
    └── api/
        ├── __init__.py
        ├── auth_audit.py            # audit_login helpers (verbatim clone)
        └── webhook.py               # POST /webhook (HMAC auth + audit + enqueue)

services/rave-mock/
├── Dockerfile                       # lightweight FastAPI; no Tesseract; no external deps
├── pyproject.toml                   # depends on fastapi, uvicorn, pydantic-xml, lxml
└── src/rave_mock/
    ├── __init__.py
    ├── main.py                      # FastAPI app; in-memory state on app.state
    ├── state.py                     # MockState dataclass (subjects, queries, sdv_flags, pds)
    ├── odm_builder.py               # builds ODM-XML response strings (uses pydantic-xml or lxml)
    └── api/
        ├── subjects.py              # GET /studies/{study}/Subjects
        ├── datasets.py              # GET /studies/{study}/subjects/{subj}/datasets/regular
        ├── post_data.py             # POST /webservice.aspx?PostODMClinicalData
        └── webhooks.py              # POST /trigger-webhook (test harness — CI only)
```

### Pattern 1: RavePort ABC (mirrors SourceAdapter)

**What:** Port (ABC) over MDRWS operations, with `RaveProfile` dataclass carrying base_url + credentials + study/environment scope. Single concrete implementation `MdrwsHttpAdapter`.

**When to use:** Every agent that reads eCRF or writes queries/flags must go through the Port — never call httpx directly from agent code.

**Example:**
```python
# Source: codebase analog — libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py
import abc
from dataclasses import dataclass
from veridoc_rave.dtos import (
    Subject, CrfFieldValue, QueryStatus, ProtocolDeviation,
    Randomization, FreezeLockStatus, DiscrepancyNoteWrite,
)

@dataclass(frozen=True)
class RaveProfile:
    base_url: str          # e.g. "https://innovate.mdsol.com/RaveWebServices"
                           #       or "http://rave-mock:8001/RaveWebServices" (CI)
    username: str
    password: str
    study_oid: str
    environment: str       # e.g. "DEV", "PROD"

class RavePort(abc.ABC):
    @abc.abstractmethod
    def get_subjects(self, profile: RaveProfile) -> list[Subject]: ...

    @abc.abstractmethod
    def get_subject_data(self, profile: RaveProfile, subject_key: str) -> list[CrfFieldValue]: ...

    @abc.abstractmethod
    def get_query_status(self, profile: RaveProfile, subject_key: str) -> list[QueryStatus]: ...

    @abc.abstractmethod
    def get_protocol_deviations(self, profile: RaveProfile, subject_key: str) -> list[ProtocolDeviation]: ...

    @abc.abstractmethod
    def get_randomization(self, profile: RaveProfile, subject_key: str) -> Randomization | None: ...

    @abc.abstractmethod
    def get_freeze_lock_status(self, profile: RaveProfile, subject_key: str) -> FreezeLockStatus: ...

    @abc.abstractmethod
    def post_discrepancy_note(self, profile: RaveProfile, write: DiscrepancyNoteWrite) -> str: ...

    @abc.abstractmethod
    def update_query_status(self, profile: RaveProfile, write: DiscrepancyNoteWrite) -> str: ...

    @abc.abstractmethod
    def set_sdv_flag(self, profile: RaveProfile, subject_key: str, item_oid: str, verified: bool) -> str: ...

    @abc.abstractmethod
    def flag_protocol_deviation(self, profile: RaveProfile, write: DiscrepancyNoteWrite) -> str: ...
```

### Pattern 2: MDRWS URL Conventions and HTTP Basic Auth

**What:** The MDRWS URL pattern is `{base_url}/studies/{study_oid}({environment})/...` for data endpoints and `{base_url}/webservice.aspx?PostODMClinicalData` for writes. HTTP Basic auth (base64 of `user:pass` in `Authorization` header).

**Source:** [rwslib docs](https://rwslib.readthedocs.io/en/latest/getting_started.html), [Medidata.RWS.NET core resources](https://medidatarwsnet.readthedocs.io/en/latest/core_resources.html) [CITED]

**Verified URL patterns (public client library documentation):**

| Operation | Method | URL Pattern |
|-----------|--------|-------------|
| List subjects | GET | `{base}/studies/{study}({env})/Subjects` |
| Subject dataset (regular) | GET | `{base}/studies/{study}({env})/subjects/{subjectkey}/datasets/regular` |
| Subject dataset (raw/audit) | GET | `{base}/studies/{study}({env})/subjects/{subjectkey}/datasets/raw` |
| Filter by form | GET | above + `/{formoid}` suffix |
| Post clinical data (WRITE) | POST | `{base}/webservice.aspx?PostODMClinicalData` |
| Version info | GET | `{base}/version` |

**Auth:**
```python
# Source: rwslib docs [CITED]
import base64
credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
headers = {"Authorization": f"Basic {credentials}"}
```

**Error response** (ODM format with mdsol namespace):
```xml
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
     xmlns:mdsol="http://www.mdsol.com/ns/odm/metadata"
     FileType="Snapshot"
     mdsol:ErrorDescription="Incorrect login and password combination. [RWS00008]" />
```

**WRITE success response:**
```xml
<Response ReferenceNumber="uuid" IsTransactionSuccessful="1"
          SubjectsCreated="0" SubjectsUpdated="1" SubjectsTouched="1"
          FieldsChanged="1" />
```

### Pattern 3: ODM-XML Structure for READ and WRITE

**What:** CDISC ODM 1.3 hierarchy for clinical data. Rave extends it with the `mdsol` namespace (`xmlns:mdsol="http://www.mdsol.com/ns/odm/metadata"`) for queries, SDV flags, and protocol deviations.

**Source:** rwslib classes_builders docs, Medidata.RWS.NET builders [CITED]

**READ response structure (CRF field with audit trail):**
```xml
<ODM xmlns="http://www.cdisc.org/ns/odm/v1.3"
     xmlns:mdsol="http://www.mdsol.com/ns/odm/metadata"
     FileType="Snapshot" ODMVersion="1.3">
  <ClinicalData StudyOID="{study_oid}" MetaDataVersionOID="1">
    <SubjectData SubjectKey="{subject_key}">
      <StudyEventData StudyEventOID="{event_oid}" StudyEventRepeatKey="1">
        <FormData FormOID="{form_oid}" FormRepeatKey="1">
          <ItemGroupData ItemGroupOID="{ig_oid}">
            <ItemData ItemOID="{item_oid}" Value="{value}">
              <AuditRecord>
                <UserRef UserOID="{user_oid}"/>
                <LocationRef LocationOID="{site_oid}"/>
                <DateTimeStamp>{iso_datetime}</DateTimeStamp>
                <ReasonForChange>{reason}</ReasonForChange>
              </AuditRecord>
              <!-- Query (discrepancy note) attached to item level: -->
              <mdsol:Query QueryRepeatKey="1" Recipient="{marking_group}"
                           Status="Open" RequiresResponse="true"
                           Response="" PrecedingQueryRepeatKey="0"/>
            </ItemData>
          </ItemGroupData>
        </FormData>
      </StudyEventData>
    </SubjectData>
  </ClinicalData>
</ODM>
```

**WRITE payload (open discrepancy note):**
```xml
<ODM FileType="Transactional" ODMVersion="1.3"
     xmlns="http://www.cdisc.org/ns/odm/v1.3"
     xmlns:mdsol="http://www.mdsol.com/ns/odm/metadata"
     CreationDateTime="{iso_datetime}" Originator="veridoc">
  <ClinicalData StudyOID="{study_oid}" MetaDataVersionOID="1">
    <SubjectData SubjectKey="{subject_key}" TransactionType="Update">
      <StudyEventData StudyEventOID="{event_oid}" StudyEventRepeatKey="1" TransactionType="Update">
        <FormData FormOID="{form_oid}" TransactionType="Update">
          <ItemGroupData ItemGroupOID="{ig_oid}" TransactionType="Update">
            <!-- mdsol:Submission="SpecifiedItemsOnly" required to avoid clearing other fields -->
            <ItemData ItemOID="{item_oid}" TransactionType="Update"
                      mdsol:Submission="SpecifiedItemsOnly">
              <mdsol:Query QueryRepeatKey="1" Status="Open"
                           Recipient="{site_marking_group}"
                           RequiresResponse="true" Value="{query_text}"
                           PrecedingQueryRepeatKey="0"/>
            </ItemData>
          </ItemGroupData>
        </FormData>
      </StudyEventData>
    </SubjectData>
  </ClinicalData>
</ODM>
```

**WRITE payload (SDV flag — set Verify="true"):**
```xml
<ItemData ItemOID="{item_oid}" Value="{value}"
          mdsol:Verify="true" TransactionType="Update">
  <AuditRecord EditPoint="Monitoring">
    <UserRef UserOID="{user_oid}"/>
    <DateTimeStamp>{iso_datetime}</DateTimeStamp>
  </AuditRecord>
</ItemData>
```

**WRITE payload (protocol deviation flag):**
```xml
<ItemData ItemOID="{item_oid}" TransactionType="Update">
  <mdsol:ProtocolDeviation RepeatKey="1" Status="Minor"
                           Code="{pd_code}" Class="{pd_class}"
                           TransactionType="Insert"
                           Value="{description}"/>
</ItemData>
```

**Freeze/lock status** is an attribute on `SubjectData` / `StudyEventData` in the raw dataset (`mdsol:Frozen`, `mdsol:Locked`). [ASSUMED — exact attribute names not confirmed in public docs; infer from rwslib `ItemData` `lock`/`freeze` builder params]

### Pattern 4: Pydantic Rave DTOs (typed boundary objects)

**What:** Clean Python objects the adapter returns; ODM-XML is never exposed outside `odm.py`.

```python
# libs/veridoc-rave/src/veridoc_rave/dtos.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class RaveAuditRecord(BaseModel):
    user_oid: str
    location_oid: str
    datetime_stamp: datetime
    reason_for_change: str | None = None

class CrfFieldValue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_key: str          # pseudonymized (D-07)
    form_oid: str
    item_oid: str
    value: str | None
    audit_records: list[RaveAuditRecord] = []

class QueryStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_key: str          # pseudonymized
    item_oid: str
    query_repeat_key: int
    status: str               # "Open" | "Answered" | "Closed" | "Cancelled"
    value: str | None = None
    recipient: str | None = None

class Subject(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_key: str          # pseudonymized at adapter boundary (D-07)
    site_oid: str
    status: str | None = None

class ProtocolDeviation(BaseModel):
    subject_key: str
    item_oid: str
    repeat_key: int
    status: str
    code: str | None = None
    klass: str | None = None
    value: str | None = None

class Randomization(BaseModel):
    subject_key: str
    randomization_number: str | None = None
    arm: str | None = None

class FreezeLockStatus(BaseModel):
    subject_key: str
    frozen: bool = False
    locked: bool = False

class DiscrepancyNoteWrite(BaseModel):
    """Payload for any WRITE operation that targets a specific item."""
    subject_key: str
    study_event_oid: str
    form_oid: str
    item_group_oid: str
    item_oid: str
    query_repeat_key: int = 1
    status: str = "Open"
    value: str | None = None   # query text or PD description
    recipient: str | None = None
    requires_response: bool = True
```

### Pattern 5: Webhook Receiver (rave-integration service)

**What:** FastAPI endpoint `POST /webhook` receives Rave event payloads, authenticates via HMAC-SHA256, writes audit, enqueues typed RQ job on `rave-events` queue.

**Webhook auth pattern** (HMAC-SHA256 + `hmac.compare_digest`):
```python
# Source: industry standard pattern [CITED: hookray.com/blog/webhook-signature-verification-2026]
import hashlib, hmac
from fastapi import Request, HTTPException

async def verify_rave_signature(request: Request, secret: str) -> None:
    """Verify X-Rave-Signature header; raise 401 if invalid (fail-closed)."""
    sig = request.headers.get("X-Rave-Signature", "")
    body = await request.body()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="invalid webhook signature")
```

**RQ job envelope** (all args JSON-serializable per DEC-rq-json-serializer):
```python
# Enqueue pattern mirrors ingestion-service (must use JSON-serializable primitives only)
queue.enqueue(
    process_rave_event,
    event_type="new_data_entry",     # str
    subject_key="<pseudonym>",       # str
    study_oid="STUDY-001",           # str
    tenant_id="site-01/study-abc",   # str
    actor_id="rave-webhook",         # str
    job_timeout=300,
    result_ttl=3600,
)
```

**Stub consumer** (Phase 3 scope — Phase 4 replaces this function body):
```python
def process_rave_event(event_type: str, subject_key: str,
                       study_oid: str, tenant_id: str, actor_id: str) -> None:
    """Stub: write dispatch audit only. Phase 4 replaces with Orchestrator call."""
    from sqlalchemy import create_engine
    from veridoc_audit import AuditEvent, append_audit
    from datetime import UTC, datetime
    engine = create_engine(settings.database_url)
    with Session(engine) as session:
        append_audit(session, AuditEvent(
            actor_id=actor_id,
            actor_role="system",
            tenant_id=tenant_id,
            action="rave:webhook:dispatched",
            entity_type="rave-event",
            entity_id=event_type,
            after={"event_type": event_type, "subject_key": subject_key},
            occurred_at=datetime.now(UTC),
        ))
        session.commit()  # worker owns this commit (D-10 stub pattern)
```

### Pattern 6: Stateful Rave Mock Service

**What:** FastAPI service with per-run in-memory state (dict on `app.state`). Stateful so an opened discrepancy note can be read back by status (D-04). No external database needed for the mock.

**State design:**
```python
# services/rave-mock/src/rave_mock/state.py
from dataclasses import dataclass, field
from threading import Lock

@dataclass
class MockState:
    subjects: dict[str, dict] = field(default_factory=dict)
    crf_fields: dict[str, list[dict]] = field(default_factory=dict)  # subject_key -> fields
    queries: dict[str, dict] = field(default_factory=dict)           # query_id -> query
    sdv_flags: dict[str, bool] = field(default_factory=dict)         # "subj/item" -> verified
    protocol_deviations: dict[str, list[dict]] = field(default_factory=dict)
    randomization: dict[str, dict] = field(default_factory=dict)
    freeze_lock: dict[str, dict] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
```

**Mock POST endpoint** — parses incoming ODM-XML WRITE and mutates state, then returns `RWSPostResponse` XML:
```python
# POST /webservice.aspx?PostODMClinicalData
# Returns success if auth valid; updates state.queries / state.sdv_flags / state.pds
```

**Mock seeding endpoint** (CI only — used by smoke test setup):
```python
# POST /mock/seed  — pre-populate subjects/CRF data for the smoke test
# This endpoint is present ONLY in the mock; it has no MDRWS analog
```

**Mock webhook trigger** (CI only — used to exercise the receiver end-to-end):
```python
# POST /mock/trigger-webhook
# body: {"event_type": "new_data_entry", "subject_key": "...", "webhook_url": "http://rave-integration:8000/webhook"}
# mock POSTs the event to webhook_url with HMAC signature using the shared webhook secret
```

### Anti-Patterns to Avoid

- **Leaking ODM-XML outside the adapter:** DTOs must be the only thing that crosses the boundary from `veridoc-rave` into service code or agent code. Import `odm.py` only from within `adapters/mdrws_http.py`.
- **Passing raw bytes to RQ:** Job payloads must be JSON-serializable primitives (DEC-rq-json-serializer). Subject keys and event types are strings — never raw XML bytes in the queue.
- **Single global webhook secret:** Use per-environment secret, read from Kubernetes Secret ref at runtime (same pattern as existing KMS key). Never commit the secret value.
- **Mock state with mutable class-level variables:** Use `app.state.mock_state` (instance-level) not module-level globals. Multiple test runs in the same process could share state otherwise.
- **Committing in `append_audit`:** Never call `session.commit()` inside or after `append_audit()` on the caller's session from within the webhook handler itself. The handler calls `append_audit()` and then `session.commit()` as one atomic operation (DEC-audit-same-txn-writer).
- **Testing with in-process stub instead of real HTTP:** D-01 requires the same HTTP adapter be used against mock AND production. Never replace `MdrwsHttpAdapter` with an in-process mock in tests — always point the adapter at the running mock service URL.
- **`TransactionType` omission on WRITE:** MDRWS WRITE payloads require explicit `TransactionType="Update"` on each level of the ODM hierarchy. Missing it causes a rejected transaction with no useful error (the mock must replicate this validation).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ODM-XML namespace-aware parsing | Custom regex or string replacement | `pydantic-xml` + `lxml` | CDISC + mdsol namespace handling, AuditRecord nesting, repeated elements — all are edge cases in hand-rolled parsers. Namespace prefixes are not stable; only `{uri}localname` Clark notation is. |
| ODM-XML serialization (WRITE payloads) | f-string XML templates | `lxml.etree` builder or `pydantic-xml` serialization | XML injection, namespace declaration ordering, encoding — all standard pitfalls with string templates. |
| HMAC constant-time comparison | `sig == expected` | `hmac.compare_digest(sig, expected)` | String equality comparison leaks timing information (timing attack). |
| Webhook idempotency | Custom dedup table | Deferred to Phase 4 (stub only in Phase 3) | Phase 3 stub does not need idempotency; Phase 4 Orchestrator owns the RQ consumer and can add it. |
| Session token management for MDRWS | Custom session / cookie jar | Stateless Basic auth on every request | MDRWS is stateless REST; each request carries credentials. No session needed. |
| Audit-chain serialization | Separate commit in webhook handler | `append_audit(session, event)` then `session.commit()` | Must be atomic with the business write (DEC-audit-same-txn-writer). |

**Key insight:** ODM-XML has 20+ years of edge cases (namespace aliases, repeated elements, vendor extensions). The mdsol namespace uses Clark notation `{http://www.mdsol.com/ns/odm/metadata}Query` internally — hand-rolled string parsers break on prefix aliasing. Use a proper XML library.

---

## Runtime State Inventory

> This is NOT a rename/refactor phase. No runtime state exists yet for Phase 3 deliverables (none of the new services, queues, or Helm resources have been deployed). Section included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | None — `veridoc-rave` lib, `rave-integration` service, and Rave mock do not exist yet | none |
| Live service config | None — `rave-events` RQ queue does not exist yet | none |
| OS-registered state | None | none |
| Secrets/env vars | None — new `RAVE_WEBHOOK_SECRET` and `RAVE_BASE_URL` env vars are NEW; not currently in any secret store | Create in deploy:kind task (ephemeral) |
| Build artifacts | None | none |

---

## Common Pitfalls

### Pitfall 1: ODM Namespace Handling
**What goes wrong:** Parsing ODM-XML with stdlib `xml.etree.ElementTree` without Clark notation (`{uri}localname`) causes silent misses on all `mdsol:` attributes (queries, SDV flags, PDs), and on the default CDISC namespace elements.
**Why it happens:** ElementTree requires the full Clark name for namespaced attributes/elements. Using local names only (e.g., `item.get("mdsol:Query")`) returns `None`.
**How to avoid:** Always use Clark notation OR use `pydantic-xml` with `lxml` backend (which handles namespaces automatically). Register namespace prefixes at parse time if using ElementTree.
**Warning signs:** All `mdsol:Query` children parse as empty lists; all CDISC elements return `None`.

### Pitfall 2: RQ JSONSerializer — XML bytes in queue
**What goes wrong:** Attempting to enqueue the raw ODM-XML bytes (or a `bytes` value) as a job argument with JSONSerializer fails silently or raises `TypeError: Object of type bytes is not JSON serializable`.
**Why it happens:** JSONSerializer calls `json.dumps()` on job args; `bytes` is not JSON-serializable.
**How to avoid:** Parse ODM-XML to DTOs BEFORE enqueueing. Job payloads are always primitives (str, int, dict of str). Never pass XML across the queue boundary.
**Warning signs:** Worker raises `TypeError` or `RQJobExecutionError` on dequeue.

### Pitfall 3: Missing `TransactionType` on ODM WRITE
**What goes wrong:** MDRWS rejects a POST payload with no `TransactionType` attribute, or applies `Insert` semantics when `Update` was intended (can create duplicate records).
**Why it happens:** `TransactionType` is optional in the ODM spec but required in practice for Rave. The default is `Insert` (create new), not `Update` (modify existing).
**How to avoid:** Explicitly set `TransactionType="Update"` on every level of the ODM hierarchy (SubjectData, StudyEventData, FormData, ItemGroupData, ItemData) for WRITE operations that modify existing data. Use `TransactionType="Insert"` only for new discrepancy notes with a new `QueryRepeatKey`.
**Warning signs:** Mock returns `IsTransactionSuccessful="1"` but state shows duplicate entries.

### Pitfall 4: Mock State Shared Across Tests
**What goes wrong:** Test run A opens a query; test run B reads state and finds unexpected data, causing flaky failures.
**Why it happens:** In-memory mock state is initialized once at app startup and shared across all requests during a run. If tests reuse the same mock process, state bleeds between tests.
**How to avoid:** Add a `DELETE /mock/reset` endpoint (CI-only) that clears `app.state.mock_state`. Call it in the pytest fixture `autouse` teardown. OR seed a known initial state in fixture setup rather than relying on empty state.
**Warning signs:** Tests pass in isolation, fail when run in sequence.

### Pitfall 5: Webhook Receiver Timing — `append_audit` before `session.commit`
**What goes wrong:** Writing audit after committing the RQ enqueue (two separate transactions) means if the process crashes between them, the audit row is missing for a webhook event that was enqueued.
**Why it happens:** Forgetting that `append_audit` joins the caller's session (DEC-audit-same-txn-writer) and must be called BEFORE `session.commit()`.
**How to avoid:** In the webhook handler: (1) `append_audit(session, event)` → (2) `queue.enqueue(...)` → (3) `session.commit()`. The enqueue happens in memory first; the commit makes audit + business write atomic. If the process crashes before commit, neither is visible.
**Warning signs:** Audit rows appear after webhook events with a gap; or `KeyError` because `append_audit` tried to read the chain head from an uncommitted session.

### Pitfall 6: Mock HTTP Basic Auth — Exact Header Comparison
**What goes wrong:** Mock accepts any credential or rejects valid credentials due to header comparison bugs.
**Why it happens:** Base64 decoding of `Authorization: Basic ...` must strip whitespace; comparison must be constant-time for auth headers too.
**How to avoid:** Use `secrets.compare_digest` (or `hmac.compare_digest`) for credential comparison. Decode: `base64.b64decode(header[6:]).decode().split(":", 1)`.
**Warning signs:** Valid credentials return 401; or mock accepts empty passwords.

### Pitfall 7: `subject_key` Pseudonymization Timing
**What goes wrong:** Rave Subject ID (natural ID from Rave) is stored/returned without pseudonymization, violating GDPR Art. 9 (D-07).
**Why it happens:** Natural subject IDs come directly from the ODM-XML `SubjectKey` attribute. If the adapter returns them verbatim, agents see PHI.
**How to avoid:** At the adapter boundary (inside `MdrwsHttpAdapter`), apply `patient_pseudonym(site_id, subject_key)` from `veridoc-pseudonym` before constructing the `Subject` DTO. The natural `subject_key` never leaves the adapter.
**Warning signs:** Subject keys in DTOs contain recognizable patterns (e.g., "001-001-001" format) rather than 64-char hex strings.

### Pitfall 8: Dockerfile — no Tesseract needed
**What goes wrong:** Copy-pasting ingestion-service Dockerfile verbatim, including Tesseract OCR install.
**Why it happens:** ingestion-service Dockerfile installs `tesseract-ocr` (Pitfall 8 from Phase 2). Rave services don't need OCR.
**How to avoid:** Clone the Dockerfile but omit the `tesseract-ocr` apt block. Reduces image size and removes an unnecessary system package.
**Warning signs:** Image build log includes `tesseract-ocr` install; image is ~200MB larger than necessary.

---

## Code Examples

### Example 1: MdrwsHttpAdapter — READ subject data

```python
# libs/veridoc-rave/src/veridoc_rave/adapters/mdrws_http.py
# Source: codebase pattern analog [ASSUMED — inferred from rwslib docs + project patterns]
import base64
import httpx
from veridoc_rave.port import RavePort, RaveProfile
from veridoc_rave.dtos import Subject, CrfFieldValue, QueryStatus
from veridoc_rave.odm import parse_subjects, parse_crf_fields, parse_query_status

class MdrwsHttpAdapter(RavePort):
    """HTTP adapter over MDRWS. Pointed at mock URL in tests, real URL in production."""

    def _auth_header(self, profile: RaveProfile) -> dict[str, str]:
        credentials = base64.b64encode(
            f"{profile.username}:{profile.password}".encode()
        ).decode()
        return {"Authorization": f"Basic {credentials}"}

    def _subjects_url(self, profile: RaveProfile) -> str:
        return (
            f"{profile.base_url}/studies/{profile.study_oid}"
            f"({profile.environment})/Subjects"
        )

    def _subject_data_url(self, profile: RaveProfile, subject_key: str) -> str:
        return (
            f"{profile.base_url}/studies/{profile.study_oid}"
            f"({profile.environment})/subjects/{subject_key}/datasets/raw"
        )

    def get_subjects(self, profile: RaveProfile) -> list[Subject]:
        url = self._subjects_url(profile)
        response = httpx.get(url, headers=self._auth_header(profile), timeout=30.0)
        response.raise_for_status()
        return parse_subjects(response.text, site_id=profile.environment)

    def get_subject_data(self, profile: RaveProfile, subject_key: str) -> list[CrfFieldValue]:
        url = self._subject_data_url(profile, subject_key)
        response = httpx.get(url, headers=self._auth_header(profile), timeout=30.0)
        response.raise_for_status()
        return parse_crf_fields(response.text, site_id=profile.environment,
                                 natural_subject_key=subject_key)
```

### Example 2: ODM parsing with pydantic-xml + lxml (or stdlib fallback)

```python
# libs/veridoc-rave/src/veridoc_rave/odm.py
# Source: pydantic-xml docs (https://pydantic-xml.readthedocs.io) [CITED]
from lxml import etree  # installed as explicit dep (pydantic-xml backend)
from veridoc_rave.dtos import CrfFieldValue, RaveAuditRecord

CDISC_NS = "http://www.cdisc.org/ns/odm/v1.3"
MDSOL_NS = "http://www.mdsol.com/ns/odm/metadata"

def parse_crf_fields(odm_xml: str, site_id: str, natural_subject_key: str) -> list[CrfFieldValue]:
    """Parse ODM-XML ClinicalData response into typed CrfFieldValue DTOs.

    Pseudonymizes subject_key at the boundary (D-07).
    """
    from veridoc_pseudonym import patient_pseudonym
    tree = etree.fromstring(odm_xml.encode())
    results = []
    # Clark notation for namespaced elements — never rely on prefix aliases
    for item_data in tree.iter(f"{{{CDISC_NS}}}ItemData"):
        item_oid = item_data.get("ItemOID", "")
        value = item_data.get("Value")
        audits = []
        for ar in item_data.iterchildren(f"{{{CDISC_NS}}}AuditRecord"):
            user_ref = ar.find(f"{{{CDISC_NS}}}UserRef")
            loc_ref = ar.find(f"{{{CDISC_NS}}}LocationRef")
            dt = ar.findtext(f"{{{CDISC_NS}}}DateTimeStamp") or ""
            reason = ar.findtext(f"{{{CDISC_NS}}}ReasonForChange")
            audits.append(RaveAuditRecord(
                user_oid=user_ref.get("UserOID", "") if user_ref is not None else "",
                location_oid=loc_ref.get("LocationOID", "") if loc_ref is not None else "",
                datetime_stamp=dt,
                reason_for_change=reason,
            ))
        results.append(CrfFieldValue(
            subject_key=patient_pseudonym(site_id, natural_subject_key),  # D-07
            form_oid=_find_ancestor_oid(item_data, f"{{{CDISC_NS}}}FormData", "FormOID"),
            item_oid=item_oid,
            value=value,
            audit_records=audits,
        ))
    return results
```

### Example 3: Webhook receiver endpoint

```python
# services/rave-integration/src/rave_integration/api/webhook.py
# Source: codebase analog — services/ingestion-service/src/ingestion_service/api/ingest.py [ASSUMED]
import hashlib, hmac
from datetime import UTC, datetime
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from veridoc_audit import AuditEvent, append_audit

router = APIRouter(prefix="", tags=["webhook"])

async def _verify_signature(request: Request, secret: str) -> bytes:
    """Verify HMAC-SHA256 webhook signature; fail-closed (raise 401 on invalid)."""
    sig = request.headers.get("X-Rave-Signature", "")
    body = await request.body()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(status_code=401, detail="invalid webhook signature")
    return body

@router.post("/webhook", status_code=202)
async def receive_webhook(request: Request) -> dict:
    """Authenticate, audit, and enqueue Rave webhook events (D-09/D-10)."""
    from fastapi.concurrency import run_in_threadpool
    import json

    secret = request.app.state.settings.rave_webhook_secret
    body = await _verify_signature(request, secret)
    payload = json.loads(body)

    event_type = payload.get("event_type", "unknown")
    subject_key = payload.get("subject_key", "")
    tenant_id = payload.get("tenant_id", "")

    queue = request.app.state.rq_queue
    session_factory = request.app.state.session_factory

    def _audit_and_enqueue() -> str:
        from veridoc_ingestion.worker import process_rave_event  # stub in Phase 3
        with session_factory() as session:
            append_audit(session, AuditEvent(
                actor_id="rave-webhook",
                actor_role="system",
                tenant_id=tenant_id,
                action="rave:webhook:received",
                entity_type="rave-event",
                entity_id=event_type,
                after={"event_type": event_type, "subject_key": subject_key},
                occurred_at=datetime.now(UTC),
            ))
            job = queue.enqueue(
                process_rave_event,
                event_type=event_type,
                subject_key=subject_key,
                tenant_id=tenant_id,
                actor_id="rave-webhook",
            )
            session.commit()  # audit + enqueue atomic (DEC-audit-same-txn-writer)
            return job.id

    job_id = await run_in_threadpool(_audit_and_enqueue)
    return {"job_id": job_id}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `motor` async MongoDB driver | `pymongo.AsyncMongoClient` | 2026 (motor EOL) | motor already excluded from Phase 2 (DEC-pymongo-asyncclient); irrelevant to Phase 3 |
| pickle-based RQ serialization | JSONSerializer only | Phase 2 (DEC-rq-json-serializer) | Eliminates RCE risk; all job payloads must be JSON-serializable primitives |
| Direct ODM-XML string passing to agents | Typed Pydantic DTOs at adapter boundary | Phase 3 (D-05) | Clean separation; ODM stays internal to the adapter |
| In-process Python fakes for integration tests | Real HTTP adapter pointed at running mock service | Phase 3 (D-01) | Production HTTP path is exercised in CI; mock-to-production swap is config-only |
| MAuth (HMAC key-based) for RWS auth | HTTP Basic auth | — | MAuth is supported but requires long-term key infrastructure; Basic auth is simpler for mock/dev; production swap may add MAuth behind the same interface |

**Deprecated/outdated:**
- `odmlib` (PyPI): inactive/discontinued per Libraries.io and Snyk as of 2025. Do not install.
- RWS ODM v1.0/v1.2: only v1.3 is recommended by Medidata for current integrations. Mock must use v1.3.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rave webhooks use a POST-based push mechanism that can be emulated by having the mock call a registered URL after a WRITE event | §Architecture Patterns (Pattern 5) | Rave may use a polling model or a different push protocol in production; mock trigger endpoint is a CI-only workaround regardless |
| A2 | Freeze/lock status is represented as `mdsol:Frozen` and `mdsol:Locked` attributes on `SubjectData`/`StudyEventData` in the raw dataset response | §Pattern 3 (ODM structure) | Attribute names differ; mock emulates them wrong; swap to production requires ODM parsing fix (low impact on adapter interface, high impact on mock accuracy) |
| A3 | `mdsol:Verify="true"` on `ItemData` is the correct attribute for setting the per-field SDV flag | §Pattern 3 (WRITE payload) | Attribute name differs; SDV flag WRITE silently does nothing in production; testable against real Rave |
| A4 | The write endpoint is `POST {base}/webservice.aspx?PostODMClinicalData` for both new queries and updates | §Pattern 2 (URL table) | Separate endpoints for insert vs update; only affects adapter routing, not the Port interface |
| A5 | `pydantic-xml` 2.21.0 will pass PACKAGE-LEGITIMACY.md human review | §Package Legitimacy Audit | Must verify: maintainer identity, download count, source repo at review time |
| A6 | `lxml` 6.1.1 will pass PACKAGE-LEGITIMACY.md human review | §Package Legitimacy Audit | lxml is de-facto standard; low risk, but human gate is mandatory per DEC-supply-chain-gate |
| A7 | Production Rave webhook delivery authenticates with HMAC-SHA256 (or the shared-secret mechanism is sufficient for the mock) | §Pattern 5 (webhook auth) | Production may use client certificates or MAuth instead; webhook auth detail is discretionary (CONTEXT.md Claude's Discretion) so HMAC is acceptable as long as it is authenticated and audited |

---

## Open Questions

1. **Freeze/lock ODM attribute names**
   - What we know: rwslib `ItemData` builder exposes `lock` and `freeze` boolean params; exact ODM attribute names are not confirmed in public docs
   - What's unclear: Exact attribute path (`mdsol:Frozen` on SubjectData? or a separate endpoint?)
   - Recommendation: Implement mock with `mdsol:Frozen`/`mdsol:Locked` on `SubjectData`; flag for validation against real Rave when CON-medidata-partner clears

2. **Rave webhook push mechanism (production)**
   - What we know: Production Rave notifies third parties via configurable webhook URLs (implied by Safety Gateway docs); exact auth mechanism is partner-documented
   - What's unclear: Whether production uses HTTP Basic, HMAC, or OAuth for outbound webhook auth
   - Recommendation: Phase 3 mock uses HMAC (discretionary). Add a `RAVE_WEBHOOK_AUTH_MODE` config flag defaulting to `hmac`; production swap can change this without breaking the receiver interface

3. **`mdsol:Submission` scope requirement**
   - What we know: rwslib uses `mdsol:Submission="SpecifiedItemsOnly"` to avoid clearing other fields on WRITE
   - What's unclear: Whether it is required at `ItemGroupData` level, `FormData` level, or both
   - Recommendation: Apply it at `ItemGroupData` level (conservative); mock must validate and reject posts missing it so the adapter is correct at swap time

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All new libs/services | ✓ (workspace) | 3.12 | — |
| PostgreSQL | `rave-integration` audit writes | ✓ (testcontainer + kind) | 15+ | testcontainer in CI |
| Redis | `rave-events` RQ queue | ✓ (kind, already deployed) | 7+ | testcontainer in integration tests |
| Docker | Dockerfile builds + kind | ✓ (CI runner) | — | — |
| kind | CI smoke test | ✓ (CI, helm/kind-action) | — | — |
| lxml C library (libxml2) | `pydantic-xml` lxml backend | needs verification in CI runner | 6.1.1 | stdlib ElementTree fallback |
| Tesseract OCR | NOT needed for Phase 3 | n/a — not required | n/a | n/a |

**Missing dependencies with no fallback:** None known.
**Missing dependencies with fallback:** lxml system libraries — if unavailable in CI, pydantic-xml falls back to stdlib ElementTree (may require explicit namespace handling in `odm.py`).

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing, APPROVED) |
| Config file | none — workspace-wide `pyproject.toml` per lib/service |
| Quick run command | `uv run pytest libs/veridoc-rave/tests/ -q` |
| Full suite command | `uv run pytest libs/veridoc-rave/tests/ services/rave-integration/tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RAVE-01 SC-1 | System READs subject data, CRF fields (with audit trail), query status, PDs, randomization, freeze/lock from mock | Integration (adapter → mock) | `uv run pytest libs/veridoc-rave/tests/test_adapter_read.py -q` | ❌ Wave 0 |
| RAVE-01 SC-2 | System WRITEs discrepancy note, updates query status, sets SDV flag, flags PD against mock | Integration (adapter → mock write, then read-back) | `uv run pytest libs/veridoc-rave/tests/test_adapter_write.py -q` | ❌ Wave 0 |
| RAVE-01 SC-3 | Mock webhook triggers `rave:webhook:dispatched` audit in Postgres | Integration (webhook receiver → audit) | `uv run pytest services/rave-integration/tests/test_webhook.py -q` | ❌ Wave 0 |
| RAVE-01 SC-4 | Mock → production swap is config-only (same adapter class, different base_url) | Unit (RavePort ABC contract) | `uv run pytest libs/veridoc-rave/tests/test_port_contract.py -q` | ❌ Wave 0 |
| RAVE-01 (ODM) | ODM-XML parses correctly into typed DTOs (all 6 types) | Unit (odm.py) | `uv run pytest libs/veridoc-rave/tests/test_odm.py -q` | ❌ Wave 0 |
| RAVE-01 (auth) | Webhook receiver rejects invalid HMAC signature with 401 | Unit (webhook endpoint) | `uv run pytest services/rave-integration/tests/test_webhook_auth.py -q` | ❌ Wave 0 |
| RAVE-01 (pseudonym) | Subject ID is pseudonymized at adapter boundary | Unit (adapter + pseudonym) | included in test_adapter_read.py | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest libs/veridoc-rave/tests/ -q`
- **Per wave merge:** `uv run pytest libs/veridoc-rave/tests/ services/rave-integration/tests/ -q`
- **Phase gate:** Full suite green + kind smoke test passing before `/gsd:verify-work`

### Kind Smoke Test (CI) — end-to-end proof

The kind smoke test must exercise all 4 Success Criteria in sequence:

1. **SC-1 (READ):** Port-forward `rave-mock:8001`; call `MdrwsHttpAdapter.get_subject_data()` via the deployed service; assert typed `CrfFieldValue` objects returned.
2. **SC-2 (WRITE):** Call `MdrwsHttpAdapter.post_discrepancy_note()` against mock; call `get_query_status()` to verify the query appears with status "Open".
3. **SC-3 (WEBHOOK):** POST to mock's `/mock/trigger-webhook` → mock POSTs HMAC-signed event to `rave-integration` webhook endpoint → verify `rave:webhook:dispatched` audit row in PostgreSQL.
4. **SC-4 (swap seam):** CI instantiates `MdrwsHttpAdapter` with two different `RaveProfile.base_url` values (mock URL + a hypothetical production URL) to confirm the Port contract is satisfied with no code change.

### Wave 0 Gaps
- [ ] `libs/veridoc-rave/tests/conftest.py` — mock service fixture (testcontainer-less; `TestClient(create_mock_app())`)
- [ ] `libs/veridoc-rave/tests/fixtures/subject_odm.xml` — sample ODM READ response fixture
- [ ] `libs/veridoc-rave/tests/fixtures/write_response.xml` — sample POST success response fixture
- [ ] `libs/veridoc-rave/tests/test_odm.py` — ODM parsing unit tests (all 6 DTO types)
- [ ] `libs/veridoc-rave/tests/test_port_contract.py` — ABC contract enforcement tests
- [ ] `libs/veridoc-rave/tests/test_adapter_read.py` — READ operations against mock TestClient
- [ ] `libs/veridoc-rave/tests/test_adapter_write.py` — WRITE + read-back round-trip
- [ ] `services/rave-integration/tests/conftest.py` — DB + RQ fixtures (testcontainer Postgres)
- [ ] `services/rave-integration/tests/test_webhook.py` — webhook auth + audit + enqueue
- [ ] `services/rave-integration/tests/test_webhook_auth.py` — HMAC signature rejection

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (inbound API + webhook) | RS256/MFA for `rave-integration` API surface (DEC-auth-direct-jwt); HMAC-SHA256 for webhook receiver |
| V3 Session Management | no | MDRWS is stateless Basic auth; no session management needed |
| V4 Access Control | yes (rave-integration API) | fail-closed tenancy (DEC-tenancy-fail-closed) + deny-by-default RBAC (inherited from ingestion-service) |
| V5 Input Validation | yes | ODM-XML parsed via lxml (structured; no eval/exec); Pydantic DTOs validate field types; reject malformed ODM |
| V6 Cryptography | yes (webhook HMAC + pseudonym) | `hmac.compare_digest` for webhook; `veridoc-pseudonym` for subject ID; never hand-roll |

### Known Threat Patterns for MDRWS / Webhook stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Forged webhook payload (no auth) | Spoofing | HMAC-SHA256 with shared secret + `hmac.compare_digest` (constant-time); 401 on invalid signature |
| XML injection in ODM WRITE payload | Tampering | Use lxml etree builder (not string concat); never embed user-supplied strings directly in XML |
| Rave Subject ID exposed in audit log | Information Disclosure | Subject ID pseudonymized at adapter boundary (D-07) BEFORE writing to any DTO, log, or audit row |
| Pickle RCE via `rave-events` queue | Elevation of Privilege | JSONSerializer mandatory (DEC-rq-json-serializer); no bytes/objects in queue payloads |
| Stale audit rows (audit written after commit) | Repudiation | DEC-audit-same-txn-writer; `append_audit` + `session.commit()` are atomic |
| Basic auth credentials over HTTP | Information Disclosure | Mock only operates in kind/dev cluster (HTTP acceptable for CI); production MDRWS uses HTTPS by default [ASSUMED] |
| Webhook replay attack | Repudiation | Deferred to Phase 4 (timestamp + nonce idempotency); Phase 3 stub does not require idempotency |

---

## Sources

### Primary (HIGH confidence)
- Codebase: `libs/veridoc-ingestion/src/veridoc_ingestion/adapter.py` — SourceAdapter ABC template
- Codebase: `libs/veridoc-audit/src/veridoc_audit/sdk.py` — `append_audit` API + DEC-audit-same-txn-writer
- Codebase: `libs/veridoc-pseudonym/src/veridoc_pseudonym/pseudonym.py` — `patient_pseudonym` API
- Codebase: `services/ingestion-service/` — service clone template (FastAPI + RQ + Dockerfile + Helm)
- Codebase: `.github/workflows/ci.yml` + `Taskfile.yml` — kind smoke test wiring template
- Codebase: `docs/validation/PACKAGE-LEGITIMACY.md` — package vetting process

### Secondary (MEDIUM confidence)
- [rwslib Python docs](https://rwslib.readthedocs.io/en/latest/) — RWS URL patterns, HTTP Basic auth, ODM format (public Medidata client lib)
- [Medidata.RWS.NET core resources](https://medidatarwsnet.readthedocs.io/en/latest/core_resources.html) — subject dataset URLs, `StudySubjectsRequest`
- [rwslib classes_builders](https://rwslib.readthedocs.io/en/latest/classes_builders.html) — `MdsolQuery`, `MdsolProtocolDeviation`, `ItemData.verify` builder classes
- [pydantic-xml PyPI](https://pypi.org/project/pydantic-xml/) + [GitHub](https://github.com/dapper91/pydantic-xml) — version 2.21.0 confirmed, 408K downloads/week
- [lxml PyPI](https://pypi.org/project/lxml/) — version 6.1.1 confirmed

### Tertiary (LOW confidence — assumed, flagged)
- Medidata RWS 2014.2.0 web help (behind S3; 403 returned) — could not verify freeze/lock attribute names directly
- Rave webhook mechanism details — official docs behind Technology Partner portal (CON-medidata-partner); inferred from Safety Gateway docs + rwslib patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack (new packages): MEDIUM — pydantic-xml + lxml confirmed on PyPI and GitHub; not slopcheck-verified in this session
- MDRWS URL patterns: MEDIUM — confirmed via public client libraries (rwslib, Medidata.RWS.NET); not confirmed against official partner API docs
- ODM-XML structure (basic hierarchy): HIGH — CDISC standard; confirmed via multiple sources
- ODM mdsol extensions (query, SDV, PD): MEDIUM — confirmed via rwslib builder class signatures; exact attribute names assumed [A2, A3]
- Architecture patterns: HIGH — directly derived from established codebase patterns (ingestion-service, audit SDK, pseudonym)
- Pitfalls: HIGH — most are derived from actual codebase decisions and established project patterns

**Research date:** 2026-06-12
**Valid until:** 2026-09-12 (stable domain) — MDRWS API surface changes slowly; pydantic-xml version may advance but API is stable
