import { render, screen } from '@testing-library/react';
import LoadingSpinner from './components/common/LoadingSpinner';

test('renders loading spinner', () => {
  render(<LoadingSpinner message="Loading..." />);
  const loadingElement = screen.getByText(/Loading.../i);
  expect(loadingElement).toBeInTheDocument();
});

test('renders loading spinner without message', () => {
  render(<LoadingSpinner />);
  const spinnerContainer = document.querySelector('.animate-spin');
  expect(spinnerContainer).toBeInTheDocument();
});
