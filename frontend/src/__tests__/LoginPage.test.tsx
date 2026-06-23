import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from '../components/LoginPage';

// Mock the auth store
const mockLogin = vi.fn();
const mockRegister = vi.fn();
const mockClearError = vi.fn();

vi.mock('../store/useAuthStore', () => ({
  useAuthStore: vi.fn((selector?: (state: Record<string, unknown>) => unknown) => {
    const state = {
      user: null,
      isLoading: false,
      error: '',
      login: mockLogin,
      register: mockRegister,
      logout: vi.fn(),
      hydrate: vi.fn(),
      clearError: mockClearError,
    };
    return typeof selector === 'function' ? selector(state) : state;
  }),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the login form by default', () => {
    render(<LoginPage />);
    const matches = screen.getAllByText(/sign in/i);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('renders email and password input fields', () => {
    render(<LoginPage />);
    const emailInput = document.querySelector('input[type="email"]');
    const passwordInput = document.querySelector('input[type="password"]');
    expect(emailInput).not.toBeNull();
    expect(passwordInput).not.toBeNull();
  });

  it('allows toggling between login and register modes', () => {
    render(<LoginPage />);
    // Click the "Sign Up" toggle button
    const toggleBtn = screen.getByText('Sign Up');
    fireEvent.click(toggleBtn);
    // After toggle, should show "Create Account" button and "Full Name" input
    expect(screen.getByText('Create Account')).toBeDefined();
    expect(screen.getByLabelText('Full Name')).toBeDefined();
  });

  it('calls login with email and password on form submit', async () => {
    render(<LoginPage />);
    const emailInput = document.querySelector('input[type="email"]') as HTMLInputElement;
    const passwordInput = document.querySelector('input[type="password"]') as HTMLInputElement;
    const form = document.querySelector('form');

    if (emailInput && passwordInput && form) {
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
      fireEvent.change(passwordInput, { target: { value: 'password123' } });
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
      });
    }
  });
});
