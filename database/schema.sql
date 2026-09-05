-- FORGE Database Schema
CREATE TABLE IF NOT EXISTS case_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    case_name TEXT,
    filing_status TEXT CHECK (filing_status IN ('pre_filing','filed','filed_against_me','unsure')),
    federal_court TEXT DEFAULT 'United States District Court for the District of Maine',
    federal_court_confirmed BOOLEAN DEFAULT FALSE,
    incident_state TEXT,
    state_source_jurisdiction TEXT,
    state_source_confirmed BOOLEAN DEFAULT FALSE,
    event_types TEXT[],
    primary_event_date DATE,
    primary_event_date_precision TEXT CHECK (primary_event_date_precision IN ('exact','approximate','unknown')),
    primary_event_city TEXT,
    primary_event_county TEXT,
    primary_event_state TEXT,
    primary_event_narrative TEXT,
    related_proceeding_status TEXT CHECK (related_proceeding_status IN
        ('none','pending','ended_unknown','dismissed','conviction_or_plea','other','unsure')),
    civil_case_filed TEXT CHECK (civil_case_filed IN ('filed_by_me','filed_against_me','not_yet','unsure')),
    federal_case_number TEXT,
    judge_assigned BOOLEAN,
    assigned_district_judge TEXT,
    assigned_magistrate_judge TEXT,
    judge_practices_status TEXT DEFAULT 'not_applicable_yet'
        CHECK (judge_practices_status IN ('not_applicable_yet','pending_assignment','pending_order_upload','verified')),
    intake_completed BOOLEAN DEFAULT FALSE,
    intake_reviewed_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS additional_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_profiles(id) ON DELETE CASCADE,
    event_date DATE,
    event_date_precision TEXT CHECK (event_date_precision IN ('exact','approximate','unknown')),
    person_involved TEXT,
    event_type TEXT,
    has_related_document BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS case_vaults (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL UNIQUE REFERENCES case_profiles(id) ON DELETE CASCADE,
    storage_prefix TEXT NOT NULL,
    encryption_status TEXT DEFAULT 'required',
    access_status TEXT DEFAULT 'private',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS case_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_profiles(id) ON DELETE CASCADE,
    vault_id UUID NOT NULL REFERENCES case_vaults(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    document_category TEXT,
    upload_status TEXT DEFAULT 'uploaded' CHECK (upload_status IN ('uploaded','failed','quarantined')),
    processing_status TEXT DEFAULT 'queued'
        CHECK (processing_status IN ('queued','extracting','needs_review','processed','failed')),
    ocr_confidence NUMERIC,
    page_count INTEGER,
    extracted_text TEXT,
    completeness_status TEXT DEFAULT 'unreviewed'
        CHECK (completeness_status IN ('unreviewed','flagged_incomplete','user_confirmed_complete')),
    uploaded_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS completeness_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES case_documents(id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('amber','red','info')),
    detail TEXT,
    page_reference INTEGER,
    resolution_status TEXT DEFAULT 'unresolved' CHECK (resolution_status IN ('unresolved','resolved','acknowledged')),
    resolution_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS fact_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_profiles(id) ON DELETE CASCADE,
    normalized_statement TEXT NOT NULL,
    fact_type TEXT,
    strength_tier TEXT DEFAULT 'weak' CHECK (strength_tier IN ('strong','moderate','weak')),
    status TEXT DEFAULT 'proposed' CHECK (status IN ('proposed','confirmed','corrected','rejected')),
    user_correction TEXT,
    last_verified_at TIMESTAMPTZ DEFAULT now(),
    decay_window_days INTEGER DEFAULT 60,
    needs_reverification BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    reviewed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS fact_card_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fact_card_id UUID NOT NULL REFERENCES fact_cards(id) ON DELETE CASCADE,
    source_document_id UUID REFERENCES case_documents(id) ON DELETE SET NULL,
    source_page INTEGER,
    source_quote TEXT,
    confidence NUMERIC,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS contradiction_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_profiles(id) ON DELETE CASCADE,
    fact_card_id_a UUID REFERENCES fact_cards(id) ON DELETE CASCADE,
    fact_card_id_b UUID REFERENCES fact_cards(id) ON DELETE CASCADE,
    contradiction_type TEXT,
    severity TEXT CHECK (severity IN ('high','medium','low')),
    detail TEXT,
    resolution_status TEXT DEFAULT 'unresolved' CHECK (resolution_status IN ('unresolved','resolved','acknowledged')),
    resolution_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL REFERENCES case_profiles(id) ON DELETE CASCADE,
    event_date DATE,
    date_precision TEXT CHECK (date_precision IN ('exact','approximate','unknown')),
    title TEXT NOT NULL,
    event_type TEXT,
    description TEXT,
    source_type TEXT CHECK (source_type IN ('user_stated','document_verified','fact_card')),
    source_fact_card_id UUID REFERENCES fact_cards(id) ON DELETE SET NULL,
    source_document_id UUID REFERENCES case_documents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID REFERENCES case_profiles(id) ON DELETE SET NULL,
    user_id UUID,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id UUID,
    detail JSONB,
    occurred_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS state_source_registry (
    state_code TEXT PRIMARY KEY,
    state_name TEXT NOT NULL,
    statutes_title TEXT,
    statutes_url TEXT,
    civil_rules_title TEXT,
    civil_rules_url TEXT,
    court_home_url TEXT,
    source_status TEXT DEFAULT 'needs_verified_source'
        CHECK (source_status IN ('verified','needs_verified_source')),
    last_verified DATE
);

INSERT INTO state_source_registry (state_code, state_name, statutes_title, statutes_url, civil_rules_title, civil_rules_url, court_home_url, source_status, last_verified)
VALUES ('ME', 'Maine', 'Maine Revised Statutes', 'https://legislature.maine.gov/statutes/',
        'Maine Rules of Civil Procedure', 'https://www.courts.maine.gov/rules/rules-civil.html',
        'https://www.courts.maine.gov/', 'verified', CURRENT_DATE)
ON CONFLICT (state_code) DO NOTHING;

ALTER TABLE case_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE fact_card_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE contradiction_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE completeness_flags ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_vaults ENABLE ROW LEVEL SECURITY;
ALTER TABLE additional_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY case_profiles_owner ON case_profiles USING (user_id = auth.uid());
CREATE POLICY case_documents_owner ON case_documents
    USING (case_id IN (SELECT id FROM case_profiles WHERE user_id = auth.uid()));
CREATE POLICY fact_cards_owner ON fact_cards
    USING (case_id IN (SELECT id FROM case_profiles WHERE user_id = auth.uid()));
CREATE POLICY fact_card_sources_owner ON fact_card_sources
    USING (fact_card_id IN (SELECT id FROM fact_cards WHERE case_id IN
        (SELECT id FROM case_profiles WHERE user_id = auth.uid())));
CREATE POLICY contradiction_flags_owner ON contradiction_flags
    USING (case_id IN (SELECT id FROM case_profiles WHERE user_id = auth.uid()));
CREATE POLICY completeness_flags_owner ON completeness_flags
    USING (document_id IN (SELECT id FROM case_documents WHERE case_id IN
        (SELECT id FROM case_profiles WHERE user_id = auth.uid())));
CREATE POLICY timeline_events_owner ON timeline_events
    USING (case_id IN (SELECT id FROM case_profiles WHERE user_id = auth.uid()));
CREATE POLICY case_vaults_owner ON case_vaults
    USING (case_id IN (SELECT id FROM case_profiles WHERE user_id = auth.uid()));
CREATE POLICY additional_events_owner ON additional_events
    USING (case_id IN (SELECT id FROM case_profiles WHERE user_id = auth.uid()));
