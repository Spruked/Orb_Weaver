# CALI CRM Integration

This folder is the canonical Vault bridge for CALI CRM runtime data.

Orb Weaver customers and CALI CRM contacts are separate systems. Customers may be exported
to the import queue, but deep dossier folders are created only for manual CALI CRM contacts
or explicit CALI CRM imports.

## Runtime Folders

```text
imports/pending/
  Orb Weaver export payloads queued for CALI CRM import.

contacts/<contact-id>_<slug>/
  dossier.json
  relationship_notes.md
  documents/
    inbox/
    contracts/
    notes/
    screenshots/
  research/
    research_notes.md
    source_index.json
  web_history/
    web_history.md
    submitted_sites.json
  knowledge/
    contact_knowledge.md
    followups.json
  provenance/
    governance.md
    source_log.json
```

## Dossier Boundary

The dossier folders are designed for owner-added business contact material:
documents, notes, web observations, relationship knowledge, follow-ups, and source logs.

Orb Weaver does not automatically research contacts through this bridge. Automated research is marked disabled in the export payload. Add source URLs, dates checked, and context notes manually when you place research material in a dossier.
