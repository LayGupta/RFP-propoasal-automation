/**
 * types/index.ts — Barrel re-export
 *
 * Re-exports all types from rfp.ts so existing imports
 *   import { Proposal } from '../types'
 * continue to work unchanged.
 */
export * from './rfp';

// ── Legacy Aliases ──
// These preserve backward compatibility with the old AppState name.
export type { ProposalStatus as AppState } from './rfp';
// AuthUser → User alias for any remaining references.
export type { User as AuthUser } from './rfp';
