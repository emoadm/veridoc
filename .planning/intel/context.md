# Context Intel

Running notes keyed by topic, appended verbatim with source attribution. No DOC-
type documents were classified; these notes are non-requirement, non-constraint
background extracted from the PRD to inform downstream planning.

---

## Topic: Project vision and problem

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (Executive Summary, section 1.1)

VeriDoc AI is an AI-powered Source Data Verification (SDV) platform for clinical
trials. It deploys a fleet of specialized AI agents to automate, standardize, and
accelerate the SDV workflow — the manual verification of source medical
documentation against eCRF data.

Vision: become the global standard for AI-assisted SDV in clinical trials —
faster, more accurate, fully auditable across any therapeutic area, phase, and
geography, while maintaining compliance with GCP, ALCOA+, 21 CFR Part 11, EMA
Annex 11, and ICH E6(R3).

Core problem: traditional on-site SDV consumes 30–35% of total trial costs and is
a primary timeline bottleneck. ICH E6(R3) risk-based monitoring shifts emphasis
toward centralized/targeted SDV, creating opportunity for AI-powered continuous
monitoring at scale.

Key value propositions: 70–85% reduction in manual SDV effort for routine fields;
real-time ALCOA+ verification; automated clinical significance assessment;
proactive AE/SAE timeline monitoring; cross-domain consistency; risk-based site
prioritization; full audit trail; global scalability.

---

## Topic: Target users and access levels

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 1.3)

Eight user roles with distinct access levels:
- CRA / Monitor (CRO/Sponsor) — perform and review SDV — full SDV workflow
- Data Manager (CRO/Sponsor) — query + data review
- Medical Monitor (CRO/Sponsor) — medical review module
- Site Coordinator (Clinical Site) — query responses only
- Principal Investigator (Clinical Site) — medical sign-off
- Sponsor Representative (Pharma/Biotech) — read-only dashboard
- Regulatory Affairs (CRO/Sponsor) — reports and audit trail
- System Administrator (Any) — full admin access

---

## Topic: Technology stack (by architecture layer)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 3.1)

Cloud-native microservices across regional cloud instances, four primary layers:
- Presentation: React.js, TypeScript, REST/GraphQL (Sponsor/CRO/Site portals, Mobile App, REST API)
- Integration: FHIR R4, HL7 v2, OAuth 2.0, SAML 2.0 (EMR adapters, eCRF/eTMF connectors, IdP)
- AI Processing: LangGraph, Python, Claude/GPT-4, Azure AI (Orchestrator + 10 agents, LLM engine, OCR engine)
- Data: PostgreSQL, MongoDB, Azure Blob, Redis (patient data store, audit DB, document store, config DB)
- Infrastructure: AWS/Azure, Terraform, Kubernetes (regional clusters, CDN, WAF, HSM, monitoring)

---

## Topic: Implementation roadmap (phasing)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 5.1)

Four phases over 36 months.
- Phase 1 — Foundation and MVP (M1–12): production-ready MVP with core SDV for EU/US; onboard 2–3 pilot clients; achieve Medidata Technology Partner status; complete initial regulatory docs and begin IQ/OQ. Sprint breakdown: M1–3 architecture + FHIR + Rave + SDV Agent; M4–5 ALCOA+ + Lab Agent + LOINC/MedDRA/SNOMED; M6–7 AE/SAE + ConMed agents; M8–9 Consistency + Orchestrator + Query agents; M10–11 Risk + Report agents + portals + audit trail; M12 pilot onboarding + IQ/OQ + regulatory docs.
- Phase 2 — Scale and Expand (M13–24): eTMF integration; additional eCRFs (Veeva EDC, Oracle Inform, REDCap); EMR adapters for Japan/Brazil/Middle East; enterprise tier + white-label; ISO 27001 certification; PQ completion + FDA/EMA submissions; second regional cluster.
- Phase 3 — Global Platform (M25–36): full global deployment incl. China isolated instance; PMDA/NMPA/ANVISA submissions; AI model fine-tuning; predictive analytics; partner ecosystem.

---

## Topic: Resource requirements (Phase 1 team)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 5.2)

Technical Lead/Architect (1), Backend Engineers Python/AI (3), Frontend Engineers
(2), DevOps/Infrastructure (1), Medical Informatics Specialist (1), Regulatory
Affairs Consultant (1 part-time), Clinical Operations Expert (1 part-time),
QA/Validation Engineer (1), Project Manager (1).

---

## Topic: Risk register

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 6)

Top risks (probability/impact/mitigation):
- Regulatory non-acceptance of AI-generated SDV findings (Med/Critical) → human-in-the-loop, explainability, early FDA/EMA engagement
- Medidata API access restrictions (Low/High) → Technology Partner agreement, abstraction layer, import fallback
- EMR integration complexity (High/Medium) → phased integration, semi-manual fallback, per-region team
- Data residency compliance failures (Low/Critical) → regional deployment day one, legal review, GDPR/PIPL by design
- AI model hallucination in clinical context (Med/Critical) → confidence thresholds, structured outputs, medical validation, conservative escalation
- CSV delays (Med/High) → early CSV consultants, validation-ready docs, 20% contingency
- Failure to secure pilot clients (Med/High) → early clinical network, no-cost pilots, academic partnerships
- Cybersecurity breach (Low/Critical) → ISO 27001, pen testing, field-level encryption, annual third-party audit
- Key personnel attrition (Med/Med) → documentation, knowledge transfer, competitive comp, equity

---

## Topic: Commercial / go-to-market and business model

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (Business Model, Financial Summary, section 7)

Business model tiers: Core (~$15–25 per-patient/month), Standard (~$3,000–8,000/month per study), Enterprise ($200K–2M/year).
Financials: Phase 1 MVP ~$800K–1.2M; break-even M20–24; ARR Y1 $200–400K, Y2 $1.5–3M, Y3 $5–12M.
Go-to-market: Phase 1 2–3 CRO pilots (no-cost/discounted for co-dev + reference); Phase 2 10–15 mid-size CROs/Sponsors (direct sales, DIA/ACRP, Medidata marketplace); Phase 3 Top-20 CROs / Big Pharma (enterprise, white-label, channel).
Competitive positioning: AI-native specialized SDV vs. broad suites (Medidata, Veeva, Oracle); eCRF-agnostic; multi-agent continuous monitoring; global EMR incl. non-FHIR legacy; ICH E6(R3) RBM built in.
Partnerships to pursue: Medidata (Dassault) Technology Partner Program; Veeva (Vault TMF/EDC); major CROs (ICON, IQVIA, Syneos, PPD); academic medical centers; regional EMR vendors.

---

## Topic: Immediate next steps (60–90 days)

source: /home/emoadm/projects/veridoc/docs/prd/veridoc-pid.md (section 8)

Critical: (#1) engage Regulatory Affairs consultant to develop regulatory strategy
+ CSV plan before any development; (#2) approach 2–3 pilot CRO/Sponsor clients;
(#3) apply for Medidata Technology Partner Program.
High: (#4) finalize architecture + select cloud provider AWS/Azure by geography;
(#5) recruit core technical team; (#6) develop detailed URS.
Medium: (#7) legal review of data privacy for EU/US; (#8) company entity + IP
strategy; (#9) financial model + Phase 1 funding; (#10) system name/brand/marketing.
Decision Gate: PID requires formal stakeholder approval before commencement;
approval authorizes Phase 1 activities and ~$800K–1.2M budget.
