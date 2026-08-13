create extension if not exists vector;

create table if not exists papers (
    id uuid primary key default gen_random_uuid(),
    arxiv_id text unique not null,
    title text not null,
    abstract text not null,
    link text not null,
    match_score float,             
    published_date date not null
);

create index if not exists idx_papers_published_date
    on papers (published_date);

create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    paper_id uuid not null references papers(id) on delete cascade,
    chunk_text text not null,
    embedding vector(384)          

create index if not exists idx_chunks_paper_id
    on chunks (paper_id);