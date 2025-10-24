import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { ArbitrageFilterPanel } from '../ArbitrageFilterPanel';
import AssetAutocomplete from '../AssetAutocomplete';
import IntervalSelector from '../IntervalSelector';
import APRRangeFilter from '../APRRangeFilter';
import LiquidityFilter from '../LiquidityFilter';
import { useArbitrageFilter } from '../../../hooks/useArbitrageFilter';
import { ArbitrageFilterState, DEFAULT_ARBITRAGE_FILTER_STATE } from '../../../types/arbitrageFilter';

// Mock the API calls
global.fetch = jest.fn();

describe('ArbitrageFilterPanel', () => {
  const mockOnFilterChange = jest.fn();
  const mockOnApply = jest.fn();
  const mockOnReset = jest.fn();

  const defaultFilterState: ArbitrageFilterState = {
    ...DEFAULT_ARBITRAGE_FILTER_STATE
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders filter button with correct initial state', () => {
    render(
      <ArbitrageFilterPanel
        filterState={defaultFilterState}
        onFilterChange={mockOnFilterChange}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const filterButton = screen.getByRole('button', { name: /filters/i });
    expect(filterButton).toBeInTheDocument();
    expect(filterButton).not.toHaveClass('active');
  });

  it('shows filter count badge when filters are active', () => {
    const activeFilterState: ArbitrageFilterState = {
      ...defaultFilterState,
      selectedAssets: [{ symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 }],
      selectedExchanges: new Set(['Binance']),
    };

    render(
      <ArbitrageFilterPanel
        filterState={activeFilterState}
        onFilterChange={mockOnFilterChange}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const filterCount = screen.getByText('2');
    expect(filterCount).toBeInTheDocument();
  });

  it('opens dropdown when filter button is clicked', () => {
    render(
      <ArbitrageFilterPanel
        filterState={defaultFilterState}
        onFilterChange={mockOnFilterChange}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);

    const dropdown = screen.getByText('Filter Options');
    expect(dropdown).toBeInTheDocument();
  });

  it('calls onReset when Clear button is clicked', () => {
    render(
      <ArbitrageFilterPanel
        filterState={defaultFilterState}
        onFilterChange={mockOnFilterChange}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);

    const clearButton = screen.getByText('Clear');
    fireEvent.click(clearButton);

    expect(mockOnReset).toHaveBeenCalled();
  });

  it('calls onApply when Apply button is clicked', () => {
    render(
      <ArbitrageFilterPanel
        filterState={defaultFilterState}
        onFilterChange={mockOnFilterChange}
        onApply={mockOnApply}
        onReset={mockOnReset}
      />
    );

    const filterButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(filterButton);

    const applyButton = screen.getByText('Apply');
    fireEvent.click(applyButton);

    expect(mockOnApply).toHaveBeenCalled();
  });
});

describe('AssetAutocomplete', () => {
  const mockOnChange = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    (fetch as jest.MockedFunction<typeof fetch>).mockClear();
  });

  it('renders search input with placeholder', () => {
    render(
      <AssetAutocomplete
        selectedAssets={[]}
        onChange={mockOnChange}
      />
    );

    const input = screen.getByPlaceholderText(/search assets/i);
    expect(input).toBeInTheDocument();
  });

  it('performs search when typing', async () => {
    const mockSearchResults = {
      results: [
        { symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 },
        { symbol: 'BTCUSD', name: 'Bitcoin USD', exchanges: 3, avg_spread_pct: 0.003, avg_apr: 8, max_spread_pct: 0.008, total_opportunities: 3 }
      ],
      query: 'BTC',
      count: 2,
      timestamp: '2025-01-01T00:00:00Z'
    };

    (fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSearchResults
    } as Response);

    render(
      <AssetAutocomplete
        selectedAssets={[]}
        onChange={mockOnChange}
      />
    );

    const input = screen.getByRole('combobox');
    await userEvent.type(input, 'BTC');

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/arbitrage/assets/search?q=BTC')
      );
    });

    await waitFor(() => {
      expect(screen.getByText('Bitcoin')).toBeInTheDocument();
      expect(screen.getByText('Bitcoin USD')).toBeInTheDocument();
    });
  });

  it('handles asset selection', async () => {
    const mockSearchResults = {
      results: [
        { symbol: 'ETH', name: 'Ethereum', exchanges: 8, avg_spread_pct: 0.004, avg_apr: 12, max_spread_pct: 0.015, total_opportunities: 10 }
      ],
      query: 'ETH',
      count: 1,
      timestamp: '2025-01-01T00:00:00Z'
    };

    (fetch as jest.MockedFunction<typeof fetch>).mockResolvedValueOnce({
      ok: true,
      json: async () => mockSearchResults
    } as Response);

    render(
      <AssetAutocomplete
        selectedAssets={[]}
        onChange={mockOnChange}
      />
    );

    const input = screen.getByRole('combobox');
    await userEvent.type(input, 'ETH');

    await waitFor(() => {
      const ethOption = screen.getByText('Ethereum');
      fireEvent.click(ethOption);
    });

    expect(mockOnChange).toHaveBeenCalledWith([
      expect.objectContaining({ symbol: 'ETH', name: 'Ethereum' })
    ]);
  });

  it('displays selected assets as tags', () => {
    const selectedAssets = [
      { symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 },
      { symbol: 'ETH', name: 'Ethereum', exchanges: 8, avg_spread_pct: 0.004, avg_apr: 12, max_spread_pct: 0.015, total_opportunities: 10 }
    ];

    render(
      <AssetAutocomplete
        selectedAssets={selectedAssets}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByText('BTC')).toBeInTheDocument();
    expect(screen.getByText('ETH')).toBeInTheDocument();
  });

  it('removes asset when tag X is clicked', () => {
    const selectedAssets = [
      { symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 }
    ];

    render(
      <AssetAutocomplete
        selectedAssets={selectedAssets}
        onChange={mockOnChange}
      />
    );

    const removeButton = screen.getByLabelText('Remove BTC');
    fireEvent.click(removeButton);

    expect(mockOnChange).toHaveBeenCalledWith([]);
  });
});

describe('IntervalSelector', () => {
  const mockOnChange = jest.fn();

  it('renders all interval options', () => {
    render(
      <IntervalSelector
        selectedIntervals={new Set()}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByLabelText('1 Hour')).toBeInTheDocument();
    expect(screen.getByLabelText('4 Hours')).toBeInTheDocument();
    expect(screen.getByLabelText('8 Hours')).toBeInTheDocument();
    expect(screen.getByLabelText('Daily')).toBeInTheDocument();
  });

  it('handles interval selection', () => {
    render(
      <IntervalSelector
        selectedIntervals={new Set()}
        onChange={mockOnChange}
      />
    );

    const fourHourCheckbox = screen.getByLabelText('4 Hours');
    fireEvent.click(fourHourCheckbox);

    expect(mockOnChange).toHaveBeenCalledWith(new Set([4]));
  });

  it('handles interval deselection', () => {
    render(
      <IntervalSelector
        selectedIntervals={new Set([4, 8])}
        onChange={mockOnChange}
      />
    );

    const fourHourCheckbox = screen.getByLabelText('4 Hours');
    fireEvent.click(fourHourCheckbox);

    expect(mockOnChange).toHaveBeenCalledWith(new Set([8]));
  });
});

describe('APRRangeFilter', () => {
  const mockOnChange = jest.fn();

  it('renders min and max APR inputs', () => {
    render(
      <APRRangeFilter
        minApr={null}
        maxApr={null}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByPlaceholderText('Min %')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Max %')).toBeInTheDocument();
  });

  it('handles min APR input', async () => {
    render(
      <APRRangeFilter
        minApr={null}
        maxApr={null}
        onChange={mockOnChange}
      />
    );

    const minInput = screen.getByPlaceholderText('Min %');
    await userEvent.type(minInput, '10');

    expect(mockOnChange).toHaveBeenLastCalledWith({ minApr: 10 });
  });

  it('handles max APR input', async () => {
    render(
      <APRRangeFilter
        minApr={null}
        maxApr={null}
        onChange={mockOnChange}
      />
    );

    const maxInput = screen.getByPlaceholderText('Max %');
    await userEvent.type(maxInput, '100');

    expect(mockOnChange).toHaveBeenLastCalledWith({ maxApr: 100 });
  });

  it('displays current values', () => {
    render(
      <APRRangeFilter
        minApr={5}
        maxApr={50}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByDisplayValue('5')).toBeInTheDocument();
    expect(screen.getByDisplayValue('50')).toBeInTheDocument();
  });
});

describe('LiquidityFilter', () => {
  const mockOnChange = jest.fn();

  it('renders OI filter inputs', () => {
    render(
      <LiquidityFilter
        minOIEither={null}
        minOICombined={null}
        onChange={mockOnChange}
      />
    );

    expect(screen.getByLabelText('Min OI (Either Side)')).toBeInTheDocument();
    expect(screen.getByLabelText('Min OI (Combined)')).toBeInTheDocument();
  });

  it('handles min OI either input', async () => {
    render(
      <LiquidityFilter
        minOIEither={null}
        minOICombined={null}
        onChange={mockOnChange}
      />
    );

    const input = screen.getByPlaceholderText('$0');
    await userEvent.type(input, '100000');

    expect(mockOnChange).toHaveBeenLastCalledWith({ minOIEither: 100000 });
  });

  it('handles min OI combined input', async () => {
    render(
      <LiquidityFilter
        minOIEither={null}
        minOICombined={null}
        onChange={mockOnChange}
      />
    );

    const inputs = screen.getAllByPlaceholderText('$0');
    const combinedInput = inputs[1]; // Second input is for combined
    await userEvent.type(combinedInput, '500000');

    expect(mockOnChange).toHaveBeenLastCalledWith({ minOICombined: 500000 });
  });
});

describe('useArbitrageFilter Hook', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('initializes with default state', () => {
    const { result } = renderHook(() => useArbitrageFilter());

    expect(result.current.filterState).toEqual(DEFAULT_ARBITRAGE_FILTER_STATE);
    expect(result.current.filterCount).toBe(0);
  });

  it('persists state to localStorage', () => {
    const { result } = renderHook(() => useArbitrageFilter());

    act(() => {
      result.current.updateFilter({
        selectedAssets: [{ symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 }]
      });
    });

    const savedState = localStorage.getItem('arbitrage_filter_state');
    expect(savedState).toBeTruthy();

    const parsed = JSON.parse(savedState!);
    expect(parsed.selectedAssets[0].symbol).toBe('BTC');
  });

  it('loads state from localStorage on mount', () => {
    const initialState = {
      selectedAssets: [{ symbol: 'ETH', name: 'Ethereum', exchanges: 8, avg_spread_pct: 0.004, avg_apr: 12, max_spread_pct: 0.015, total_opportunities: 10 }],
      selectedExchanges: ['Binance'],
      selectedIntervals: [4, 8],
      minApr: 10,
      maxApr: 100,
      minOIEither: 50000,
      minOICombined: null
    };

    localStorage.setItem('arbitrage_filter_state', JSON.stringify(initialState));

    const { result } = renderHook(() => useArbitrageFilter());

    expect(result.current.filterState.selectedAssets[0].symbol).toBe('ETH');
    expect(result.current.filterState.minApr).toBe(10);
  });

  it('calculates filter count correctly', () => {
    const { result } = renderHook(() => useArbitrageFilter());

    act(() => {
      result.current.updateFilter({
        selectedAssets: [{ symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 }],
        selectedExchanges: new Set(['Binance', 'KuCoin']),
        minApr: 10,
        maxApr: 100
      });
    });

    expect(result.current.filterCount).toBe(4); // 1 asset + 1 exchange group + 2 APR filters
  });

  it('builds query parameters correctly', () => {
    const { result } = renderHook(() => useArbitrageFilter());

    act(() => {
      result.current.updateFilter({
        selectedAssets: [
          { symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 },
          { symbol: 'ETH', name: 'Ethereum', exchanges: 8, avg_spread_pct: 0.004, avg_apr: 12, max_spread_pct: 0.015, total_opportunities: 10 }
        ],
        selectedExchanges: new Set(['Binance']),
        selectedIntervals: new Set([4, 8]),
        minApr: 5,
        maxApr: 200,
        minOIEither: 100000
      });
    });

    const params = result.current.buildQueryParams();

    expect(params.assets).toEqual(['BTC', 'ETH']);
    expect(params.exchanges).toEqual(['Binance']);
    expect(params.intervals).toEqual([4, 8]);
    expect(params.min_apr).toBe(5);
    expect(params.max_apr).toBe(200);
    expect(params.min_oi_either).toBe(100000);
  });

  it('resets filter to defaults', () => {
    const { result } = renderHook(() => useArbitrageFilter());

    act(() => {
      result.current.updateFilter({
        selectedAssets: [{ symbol: 'BTC', name: 'Bitcoin', exchanges: 8, avg_spread_pct: 0.005, avg_apr: 10, max_spread_pct: 0.01, total_opportunities: 5 }],
        minApr: 50
      });
    });

    expect(result.current.filterCount).toBeGreaterThan(0);

    act(() => {
      result.current.resetFilter();
    });

    expect(result.current.filterState).toEqual(DEFAULT_ARBITRAGE_FILTER_STATE);
    expect(result.current.filterCount).toBe(0);
  });
});