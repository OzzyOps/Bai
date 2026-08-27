// Placeholder until `scripts/gen-types.sh` runs against a live project.
export type Role = 'owner' | 'admin' | 'manager' | 'operator' | 'viewer';
export type Region = 'eu' | 'uk' | 'us' | 'apac' | 'jp' | 'br';
export type RunState =
  | 'pending' | 'running' | 'awaiting_human' | 'completed' | 'failed' | 'cancelled';
export type Consequence = 'none' | 'reversible' | 'consequential';
