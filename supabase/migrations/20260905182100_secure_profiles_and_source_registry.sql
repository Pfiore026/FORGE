-- Secure profiles and source registry
-- Applied manually to the FORGE Supabase project on 2026-09-05.

CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.state_source_registry ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS profiles_select_own ON public.profiles;
DROP POLICY IF EXISTS profiles_insert_own ON public.profiles;
DROP POLICY IF EXISTS profiles_update_own ON public.profiles;
DROP POLICY IF EXISTS profiles_delete_own ON public.profiles;

CREATE POLICY profiles_select_own
ON public.profiles
FOR SELECT
TO authenticated
USING (id = auth.uid());

CREATE POLICY profiles_insert_own
ON public.profiles
FOR INSERT
TO authenticated
WITH CHECK (id = auth.uid());

CREATE POLICY profiles_update_own
ON public.profiles
FOR UPDATE
TO authenticated
USING (id = auth.uid())
WITH CHECK (id = auth.uid());

CREATE POLICY profiles_delete_own
ON public.profiles
FOR DELETE
TO authenticated
USING (id = auth.uid());

DROP POLICY IF EXISTS state_source_registry_authenticated_read
ON public.state_source_registry;

CREATE POLICY state_source_registry_authenticated_read
ON public.state_source_registry
FOR SELECT
TO authenticated
USING (true);
