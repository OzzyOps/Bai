-- BAi platform · extensions
create extension if not exists "pgcrypto";     -- gen_random_uuid
create extension if not exists "vector";       -- pgvector, embeddings in the tenant DB
create extension if not exists "pg_trgm";      -- fuzzy matching for entity resolution
