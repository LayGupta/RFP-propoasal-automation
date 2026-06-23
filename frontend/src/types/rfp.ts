/**
 * rfp.ts — Strict TypeScript interfaces for the FMCG RFP Platform
 *
 * Single source of truth for domain models shared across components,
 * stores, and API layers. Keep in sync with backend schemas.
 */

// ────────────────────────────────────────────────────────────────────────────
// User & Auth
// ────────────────────────────────────────────────────────────────────────────

/** Authenticated user returned after login/register. */
export interface User {
  user_id: string;
  email: string;
  full_name: string;
  token: string;
}

// ────────────────────────────────────────────────────────────────────────────
// RFP Requirements & SKU Matching
// ────────────────────────────────────────────────────────────────────────────

/** Single extracted line-item from the RFP document. */
export interface RFPRequirement {
  line_item_id: string;
  raw_specification_string: string;
  core_count: number;
  conductor_material: string;
  voltage_rating: number;
  insulation_type: string;
  cross_section_mm2: number;
}

/** Catalog SKU matched against an RFP requirement. */
export interface SKURecommendation {
  sku_id: string;
  product_name: string;
  spec_match_percentage: number;
  is_custom_mto: boolean;
  gap_analysis_notes: string;
}

/** Pricing calculation for a single SKU line. */
export interface PricingLineItem {
  sku_id: string;
  core_count: number;
  voltage_rating: number;
  base_price_per_meter: number;
  volatility_multiplier: number;
  adjusted_price_per_meter: number;
}

// ────────────────────────────────────────────────────────────────────────────
// Proposals & Bids
// ────────────────────────────────────────────────────────────────────────────

/** Pipeline status across the full workflow lifecycle. */
export type ProposalStatus =
  | 'IDLE'
  | 'PROCESSING'
  | 'PAUSED_FOR_HUMAN_REVIEW'
  | 'COMPLETED'
  | 'ERROR';

/** Document-level metadata extracted from the RFP. */
export interface ProposalMetadata {
  client_name: string;
  project_name: string;
  rfp_date: string;
}

/** A saved/completed proposal record (history sidebar + DB row). */
export interface Proposal {
  id: string;
  thread_id: string;
  project_name: string;
  final_markdown: string;
  outreach_email_draft?: string;
  metadata?: ProposalMetadata;
  pricing_breakdown?: PricingLineItem[];
  matched_skus?: SKURecommendation[];
  status: ProposalStatus;
  created_at: string;
  updated_at?: string;
}

/** Response from POST /api/process-rfp/start */
export interface StartResponse {
  status: ProposalStatus;
  thread_id: string;
  blueprint_payload: string[];
  matched_skus: SKURecommendation[];
  final_proposal_markdown?: string;
  outreach_email_draft?: string;
}

/** Response from POST /api/process-rfp/resume */
export interface FinalResponse {
  status: ProposalStatus;
  thread_id: string;
  final_proposal_markdown: string;
  outreach_email_draft?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Bid
// ────────────────────────────────────────────────────────────────────────────

/** A bid wraps a proposal with submission context and pricing totals. */
export interface Bid {
  id: string;
  proposal_id: string;
  thread_id: string;
  client_name: string;
  project_name: string;
  total_base_price: number;
  total_adjusted_price: number;
  volatility_multiplier: number;
  line_items: PricingLineItem[];
  mto_count: number;
  standard_count: number;
  submitted_at: string;
  submitted_by: string;
  status: 'draft' | 'submitted' | 'accepted' | 'rejected' | 'expired';
  notes?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Email
// ────────────────────────────────────────────────────────────────────────────

/** Payload for the outreach email API. */
export interface EmailPayload {
  recipient_email: string;
  subject: string;
  email_body: string;
  /** Optional CC list. */
  cc?: string[];
  /** Optional BCC list. */
  bcc?: string[];
  /** Thread ID linking the email to a proposal. */
  thread_id?: string;
  /** Reply-To address override. */
  reply_to?: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Scout (Sales Discovery)
// ────────────────────────────────────────────────────────────────────────────

export interface ScoutOpportunity {
  tender_title: string;
  summary: string;
  issuing_authority: string;
  source_url: string;
  matched_category?: string;
}

export interface ScoutResult {
  results_count: number;
  categories_searched: string[];
  opportunities: ScoutOpportunity[];
  alert_sent: boolean;
}

export interface ScoutLog {
  id: string;
  query: string;
  results_count: number;
  alert_sent: boolean;
  created_at: string;
}

// ────────────────────────────────────────────────────────────────────────────
// Analytics
// ────────────────────────────────────────────────────────────────────────────

export interface AnalyticsData {
  total_proposals: number;
  total_products: number;
  total_inventory_value: number;
  copper_products: number;
  aluminium_products: number;
  proposals_timeline: { date: string; count: number }[];
  scout_logs: ScoutLog[];
}

// ────────────────────────────────────────────────────────────────────────────
// Chat (RAG)
// ────────────────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources: { content: string; source: string }[];
  on_topic?: boolean;
}
