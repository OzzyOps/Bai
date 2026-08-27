-- BAi platform · documents and chunks
-- A document is identified by the SHA-256 of its bytes, not its filename.
-- Re-uploading an unchanged file must never re-run inference.

create table public.documents (
  id           uuid primary key default gen_random_uuid(),
  org_id       uuid not null references public.orgs(id)    on delete cascade,
  record_id    uuid          references public.records(id) on delete cascade,
  filename     text not null,
  media_type   text not null,
  sha256       char(64) not null,
  byte_size    bigint not null check (byte_size > 0),
  storage_path text not null,
  uploaded_by  uuid references auth.users(id),
  created_at   timestamptz not null default now(),
  -- content dedupe is per tenant: two orgs may hold the same file independently
  constraint documents_org_sha_unique unique (org_id, sha256),
  constraint documents_sha_lower check (sha256 = lower(sha256))
);
create index documents_org_idx    on public.documents(org_id);
create index documents_record_idx on public.documents(record_id);

create table public.document_chunks (
  id          uuid primary key default gen_random_uuid(),
  org_id      uuid not null references public.orgs(id)      on delete cascade,
  document_id uuid not null references public.documents(id) on delete cascade,
  ordinal     integer not null,
  content     text    not null,
  char_start  integer not null,
  char_end    integer not null,
  locator     text,
  -- 1024 dims. Embeddings live in the tenant's region alongside their source and
  -- are deleted with it — a commonly missed erasure path.
  embedding   vector(1024),
  created_at  timestamptz not null default now(),
  constraint chunk_span_valid  check (char_end > char_start),
  constraint chunk_unique_ord  unique (document_id, ordinal)
);
create index chunks_org_idx on public.document_chunks(org_id);
create index chunks_doc_idx on public.document_chunks(document_id);
-- ANN index. Tune `lists` to roughly sqrt(row count) once the table is populated.
create index chunks_embedding_idx on public.document_chunks
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);
