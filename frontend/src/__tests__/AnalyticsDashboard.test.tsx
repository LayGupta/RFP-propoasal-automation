/**
 * AnalyticsDashboard.test.tsx — Smoke Tests
 *
 * Verifies that AnalyticsDashboard renders correctly in three states:
 *   1. Loading state (spinner visible)
 *   2. Error state (error message + retry button)
 *   3. Data state (KPI cards, charts, scout logs)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AnalyticsDashboard from '../components/AnalyticsDashboard';
import type { AnalyticsData } from '../types';

// ── Mock API module ──
const mockFetchAnalytics = vi.fn();
vi.mock('../lib/api', () => ({
  fetchAnalytics: (...args: unknown[]) => mockFetchAnalytics(...args),
}));

const SAMPLE_ANALYTICS: AnalyticsData = {
  total_proposals: 42,
  total_products: 45,
  total_inventory_value: 2_50_00_000, // ₹2.5 Cr → displays as "250.0L"
  copper_products: 30,
  aluminium_products: 15,
  proposals_timeline: [
    { date: '2026-06-01', count: 5 },
    { date: '2026-06-08', count: 12 },
    { date: '2026-06-15', count: 25 },
  ],
  scout_logs: [
    {
      id: 'log-001',
      query: '1100V XLPE cable tender India',
      results_count: 7,
      alert_sent: true,
      created_at: '2026-06-20T10:00:00Z',
    },
    {
      id: 'log-002',
      query: 'copper cable RFP government',
      results_count: 3,
      alert_sent: false,
      created_at: '2026-06-21T14:30:00Z',
    },
  ],
};

describe('AnalyticsDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Loading State ──
  it('shows a loading spinner initially', () => {
    // Never resolve the promise → stays in loading state
    mockFetchAnalytics.mockReturnValue(new Promise(() => {}));

    render(<AnalyticsDashboard token="test-token" />);

    expect(screen.getByText('Loading analytics...')).toBeInTheDocument();
  });

  // ── Error State ──
  it('shows error message and retry button on API failure', async () => {
    mockFetchAnalytics.mockRejectedValueOnce(new Error('Network error'));

    render(<AnalyticsDashboard token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText(/Network error/)).toBeInTheDocument();
    });

    // Retry button should be visible
    const retryBtn = screen.getByText('Retry');
    expect(retryBtn).toBeInTheDocument();
  });

  // ── Data Loaded: KPI Cards ──
  it('renders KPI cards with correct values', async () => {
    mockFetchAnalytics.mockResolvedValueOnce(SAMPLE_ANALYTICS);

    render(<AnalyticsDashboard token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument(); // total proposals
    });

    expect(screen.getByText('45')).toBeInTheDocument();         // catalog products
    expect(screen.getByText('2')).toBeInTheDocument();          // scout runs (2 logs)
    expect(screen.getByText('Total Proposals')).toBeInTheDocument();
    expect(screen.getByText('Catalog Products')).toBeInTheDocument();
    expect(screen.getByText('Inventory Value')).toBeInTheDocument();
    expect(screen.getByText('Scout Runs')).toBeInTheDocument();
  });

  // ── Data Loaded: Chart Sections ──
  it('renders chart section headers', async () => {
    mockFetchAnalytics.mockResolvedValueOnce(SAMPLE_ANALYTICS);

    render(<AnalyticsDashboard token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText('📊 Proposals Over Time')).toBeInTheDocument();
    });

    expect(screen.getByText('🔩 Material Distribution')).toBeInTheDocument();
  });

  // ── Data Loaded: Scout Logs Table ──
  it('renders scout logs table with entries', async () => {
    mockFetchAnalytics.mockResolvedValueOnce(SAMPLE_ANALYTICS);

    render(<AnalyticsDashboard token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText('🔍 Tender Scout Activity')).toBeInTheDocument();
    });

    // Check log entries are rendered
    expect(screen.getByText('1100V XLPE cable tender India')).toBeInTheDocument();
    expect(screen.getByText('copper cable RFP government')).toBeInTheDocument();
    expect(screen.getByText('✓ Sent')).toBeInTheDocument(); // alert_sent: true
  });

  // ── Refresh Button ──
  it('calls fetchAnalytics again when refresh button is clicked', async () => {
    mockFetchAnalytics.mockResolvedValue(SAMPLE_ANALYTICS);

    render(<AnalyticsDashboard token="test-token" />);

    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });

    // Initial call
    expect(mockFetchAnalytics).toHaveBeenCalledTimes(1);
    expect(mockFetchAnalytics).toHaveBeenCalledWith('test-token');

    // Click refresh
    fireEvent.click(screen.getByText('↻ Refresh Analytics'));

    await waitFor(() => {
      expect(mockFetchAnalytics).toHaveBeenCalledTimes(2);
    });
  });

  // ── Retry After Error ──
  it('retries fetch when retry button is clicked after error', async () => {
    mockFetchAnalytics
      .mockRejectedValueOnce(new Error('Server down'))
      .mockResolvedValueOnce(SAMPLE_ANALYTICS);

    render(<AnalyticsDashboard token="test-token" />);

    // Wait for error state
    await waitFor(() => {
      expect(screen.getByText(/Server down/)).toBeInTheDocument();
    });

    // Click retry
    fireEvent.click(screen.getByText('Retry'));

    // Should now show data
    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });
  });
});
