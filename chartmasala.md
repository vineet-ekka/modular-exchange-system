# Chart Implementation Plan for Historical Funding Pages

## Executive Summary

This document outlines the implementation plan for adding interactive charts and comprehensive metrics display to the historical funding rate pages. The implementation will handle incomplete data gracefully, adapt to different funding intervals, and provide clear visual feedback about data quality.

## 1. Key Metrics Display

### 1.1 Seven Core Metrics
The Key Information Display will show exactly these metrics:

1. **Mark Price** - Latest available mark price from the contract
2. **Current Funding Rate** - Most recent funding rate (percentage)
3. **APR** - Annualized Percentage Rate based on current rate
4. **Z-Score (Period)** - Statistical deviation for selected period (7d/14d/30d)
5. **Percentile (Period)** - Rank within selected period (7d/14d/30d)
6. **Mean (30d)** - 30-day average funding rate
7. **Std Dev (30d)** - 30-day standard deviation

### 1.2 Layout Structure
```
┌──────────────────────────────────────────────────────────────────────┐
│  Mark Price        Current Rate      APR           Mean (30d)         │
│  $67,432.50        0.0045%          14.31%        0.0023%            │
│                                                                       │
│  Z-Score (7d)      Percentile (7d)  Std Dev (30d)                   │
│  +1.24             85th              0.0034%                         │
└──────────────────────────────────────────────────────────────────────┘
```

## 2. Adaptive Period Selection

### 2.1 Period Availability Logic

The system will dynamically determine which time periods can be displayed based on:
- Funding interval of the contract
- Number of available data points
- Data completeness percentage
- Maximum gap size in the data

### 2.2 Required Data Points by Interval

| Funding Interval | 1D Points | 7D Points | 14D Points | 30D Points |
|-----------------|-----------|-----------|------------|------------|
| 1 hour          | 24        | 168       | 336        | 720        |
| 2 hours         | 12        | 84        | 168        | 360        |
| 4 hours         | 6         | 42        | 84         | 180        |
| 8 hours         | 3         | 21        | 42         | 90         |

### 2.3 Data Completeness Thresholds

For each period to be enabled:
- **Minimum 70% data completeness** required
- **Maximum consecutive gap** limits:
  - 1D: Max 1 funding interval gap
  - 7D: Max 24 hours gap
  - 14D: Max 48 hours gap
  - 30D: Max 72 hours gap

### 2.4 Period Selection Algorithm

```
For each potential period [1D, 7D, 14D, 30D]:
  1. Calculate expected data points = period_days * (24 / funding_interval_hours)
  2. Count actual available data points (non-null funding rates)
  3. Calculate completeness = (actual / expected) * 100
  4. Find largest consecutive gap in data
  5. Determine period status:
     - If completeness >= 70% AND gap <= max_allowed: ENABLE
     - If completeness >= 50% AND gap <= max_allowed * 1.5: ENABLE_WITH_WARNING
     - Otherwise: DISABLE
```

## 3. Data Quality Handling

### 3.1 Data Quality Indicators

Each period will have a quality assessment:
- **High Quality** (Green): >90% complete, no significant gaps
- **Medium Quality** (Yellow): 70-90% complete, minor gaps
- **Low Quality** (Orange): 50-70% complete, notable gaps
- **Insufficient** (Gray/Disabled): <50% complete or excessive gaps

### 3.2 Missing Data Scenarios

#### Scenario A: New Contract
- Contract listed < 7 days ago
- Show only 1D (and possibly partial 7D with warning)
- Display actual data range in chart
- Metrics show "--" for unavailable periods

#### Scenario B: API Outages
- Gaps in historical data due to exchange/collector issues
- Chart shows gaps as blank spaces (no interpolation)
- Metrics calculated only on available data
- Warning badge shows data completeness percentage

#### Scenario C: Incomplete Current Data
- Missing current funding rate or mark price
- Fall back to most recent historical value
- Show "Last Updated: X hours ago" indicator
- Use stale data with visual warning

### 3.3 Visual Communication

```
Period Selector with Quality Indicators:
[1D ✓] [7D ⚠ 85%] [14D ✓] [30D ✗]

Or simpler approach (hide unavailable):
[1D] [7D] [14D]  (30D not shown when insufficient data)
```

## 4. Chart Implementation

### 4.1 Chart Type and Features
- **Area Chart** with gradient fill
- Green gradient for positive rates
- Red gradient for negative rates
- Zero reference line always visible
- No interpolation across data gaps

### 4.2 Chart Behavior
- Height: 300px (responsive)
- X-axis: Time labels (auto-formatted based on period)
- Y-axis: Percentage values with 3 decimal places
- Tooltip: Shows exact funding rate, APR, and timestamp
- Gaps: Shown as breaks in the line (no connection)

### 4.3 Chart Data Processing

```
1. Fetch historical data for maximum available period
2. Process data points:
   - Convert funding_rate to percentage (* 100)
   - Mark null values (preserve gaps)
   - Calculate display timestamps
3. Determine available periods based on data
4. Default to longest available period
5. Update chart when period selection changes
```

## 5. Statistical Calculations

### 5.1 Period-Specific Metrics

**Z-Score Calculation:**
- Requires minimum 3 data points
- Calculated only for selected period
- Returns null if insufficient data or zero std dev
- Formula: (current_rate - period_mean) / period_std_dev

**Percentile Calculation:**
- Requires minimum 5 data points
- Based on selected period data only
- Returns null if insufficient data
- Method: Rank current rate within period distribution

### 5.2 Fixed Reference Metrics

**30-Day Mean and Std Dev:**
- Always attempts 30-day calculation
- Shows "--" if less than 30 days of data
- Not affected by selected period
- Provides consistent reference point

## 6. Implementation Components

### 6.1 Data Fetching Strategy

Two API calls required:
1. **Contract Statistics** (`/api/contracts-with-zscores`)
   - Provides current values
   - 30-day mean and std dev
   - Current Z-score (database calculated)
   - Returns data in this structure:
     ```typescript
     {
       mark_price: number;
       funding_rate: number;
       apr: number;
       mean_30d: number;
       std_dev_30d: number;
       current_z_score: number;
       current_percentile: number;
     }
     ```

2. **Historical Data** (`/api/historical-funding-by-contract/{exchange}/{symbol}`)
   - Time series data for selected period
   - Used for chart display
   - Used for period-specific calculations
   - Returns data in this structure:
     ```typescript
     {
       exchange: string;
       symbol: string;
       base_asset: string;
       funding_interval_hours: number;
       data: Array<{
         timestamp: string;
         funding_rate: number | null;
         apr: number | null;
         mark_price?: number;
         open_interest?: number;
       }>;
     }
     ```

### 6.2 Component Structure

```
HistoricalFundingViewContract.tsx
├── Key Information Display Component
│   ├── Current Metrics Row (4 metrics)
│   └── Statistical Metrics Row (3 metrics)
├── Period Selector Component
│   ├── Available Period Buttons
│   └── Data Quality Indicator
├── Chart Component
│   ├── Area Chart with Recharts
│   ├── Custom Tooltip
│   └── Gap Handling
└── Existing Table Component (unchanged)
```

### 6.3 State Management

```typescript
// Core state
const [timeRange, setTimeRange] = useState<number>(7);
const [availablePeriods, setAvailablePeriods] = useState<number[]>([]);
const [dataQuality, setDataQuality] = useState<QualityMap>({});
const [historicalData, setHistoricalData] = useState<DataPoint[]>([]);
const [contractStats, setContractStats] = useState<ContractStats | null>(null);

// Calculated metrics
const [periodZScore, setPeriodZScore] = useState<number | null>(null);
const [periodPercentile, setPeriodPercentile] = useState<number | null>(null);
```

## 7. Error Handling

### 7.1 Calculation Safeguards
- All calculations wrapped in try-catch
- Check for NaN, Infinity before displaying
- Return null for invalid calculations
- Show "--" or "N/A" in UI for null values

### 7.2 Data Validation
- Verify funding_rate is numeric
- Check timestamp validity
- Ensure positive funding intervals
- Validate percentage calculations

### 7.3 User Feedback
- Loading skeletons during data fetch
- Error messages for API failures
- Retry button for failed requests
- Clear indication of data staleness

## 8. Performance Considerations

### 8.1 Optimization Strategies
- Memoize expensive calculations
- Debounce period selection changes
- Cache API responses (5-second TTL)
- Virtual scrolling for table (existing)

### 8.2 Data Limits
- Maximum 30 days of historical data
- Limit chart points to 1000 (downsample if needed)
- Progressive loading for initial render

## 9. User Experience Flow

### 9.1 Initial Load
1. Fetch historical data (max available)
2. Determine available periods
3. Auto-select longest valid period
4. Calculate all metrics
5. Display chart and metrics

### 9.2 Period Change
1. User clicks different period
2. Recalculate period-specific metrics
3. Adjust chart X-axis range
4. Update Z-score and percentile displays
5. Keep 30d metrics unchanged

### 9.3 Auto-Refresh
- Every 30 seconds (existing behavior)
- Update current values
- Append new data point if available
- Recalculate affected metrics
- Maintain selected period

## 10. Testing Requirements

### 10.1 Functional Tests
- New contract with < 1 day of data
- Contract with exactly 7 days of data
- Contract with gaps in data
- Different funding intervals (1h, 4h, 8h)
- Null/undefined value handling

### 10.2 Visual Tests
- Chart renders correctly with gaps
- Period selector shows correct availability
- Metrics display "--" when unavailable
- Responsive behavior on mobile

### 10.3 Edge Cases
- Contract with all zero funding rates
- Contract with single data point
- Extremely volatile funding rates
- Switching between contracts rapidly

## 11. Future Enhancements (Not in MVP)

- Historical period comparison (this week vs last week)
- Correlation with price movements
- Export chart as image
- Custom period selection (date picker)
- Multiple contract comparison overlay
- Moving average overlay on chart
- Funding rate distribution histogram

## 12. Success Criteria

The implementation is successful when:
1. Chart displays for all contracts with sufficient data
2. Metrics accurately reflect the selected period
3. Data quality is clearly communicated
4. No misleading statistics from incomplete data
5. Performance remains smooth with 30-second updates
6. Users can easily understand data completeness
7. System handles all edge cases gracefully

---

*This plan ensures robust handling of incomplete data while providing maximum value from available information. The adaptive approach means every contract gets the best possible visualization based on its specific data characteristics.*

## 13. STRICT COMPLIANCE REQUIREMENTS

### 13.1 NON-NEGOTIABLE SPECIFICATIONS

The following specifications are ABSOLUTE and MUST NOT be changed under any circumstances:

#### Metrics Display (EXACTLY 7 METRICS - NO MORE, NO LESS)
```typescript
// REQUIRED: These exact metrics in this exact order
const REQUIRED_METRICS = {
  row1: ['Mark Price', 'Current Funding Rate', 'APR', 'Mean (30d)'],
  row2: ['Z-Score (Period)', 'Percentile (Period)', 'Std Dev (30d)']
};

// FORBIDDEN: Any additional metrics or removal of specified metrics
// FORBIDDEN: Changing the layout from 4-3 split to any other arrangement
// FORBIDDEN: Renaming metrics (e.g., "Average" instead of "Mean")

// IMPLEMENTATION REQUIREMENT: Use data attributes for validation
<div data-metric="mark-price">...</div>
<div data-metric="current-rate">...</div>
// etc. for all 7 metrics
```

#### Chart Specifications (MUST BE AREA CHART)
```typescript
// REQUIRED: Area chart with gradient fill
const CHART_TYPE = 'area'; // NOT 'line', 'bar', 'candlestick', or any other

// REQUIRED: Color scheme
const POSITIVE_GRADIENT = 'green'; // NOT blue, NOT any other color
const NEGATIVE_GRADIENT = 'red';   // NOT orange, NOT any other color
const ZERO_LINE = 'always_visible'; // MUST show zero reference

// FORBIDDEN: Line interpolation across gaps
const INTERPOLATION = 'none'; // Gaps MUST show as breaks
```

#### Data Thresholds (EXACT VALUES - NO DEVIATION)
```typescript
const DATA_COMPLETENESS = {
  minimum_required: 70,     // NOT 60, NOT 75, EXACTLY 70%
  warning_threshold: 50,    // NOT 40, NOT 60, EXACTLY 50%
  quality_high: 90,        // NOT 85, NOT 95, EXACTLY 90%
};

const GAP_LIMITS = {
  '1D': 1,   // EXACTLY 1 funding interval
  '7D': 24,  // EXACTLY 24 hours
  '14D': 48, // EXACTLY 48 hours  
  '30D': 72  // EXACTLY 72 hours
};
```

### 13.2 IMPLEMENTATION GUARDS

#### Pre-Implementation Checklist
Before ANY code is written, verify:
- [ ] Read this entire document twice
- [ ] Confirm exactly 7 metrics will be displayed
- [ ] Confirm area chart with gradient implementation
- [ ] Confirm no interpolation will be added
- [ ] Confirm 70% minimum data completeness threshold
- [ ] Confirm API endpoints match specification exactly

#### Code Review Criteria
Every pull request MUST be rejected if:
1. Number of metrics ≠ 7
2. Chart type ≠ area chart
3. Interpolation is implemented for gaps
4. Data completeness threshold ≠ 70%
5. Period selection logic differs from specification
6. API endpoints are modified or new ones created
7. Z-score calculation formula is changed
8. Percentile calculation method is altered
9. Layout does not match 4-3 metric split
10. Color scheme uses colors other than specified

### 13.3 VALIDATION MATRIX

| Component | Specification | Validation Method | Failure Action |
|-----------|--------------|-------------------|----------------|
| Metrics Count | Exactly 7 | Count rendered metric components | BLOCK DEPLOYMENT |
| Chart Type | Area Chart | Check chart component type | BLOCK DEPLOYMENT |
| Gap Handling | No Interpolation | Verify null data points remain null | BLOCK DEPLOYMENT |
| Data Threshold | 70% minimum | Test with 69% complete data | MUST DISABLE PERIOD |
| Period Logic | As specified | Unit test all scenarios | BLOCK DEPLOYMENT |
| API Endpoints | Use existing only | Check for new endpoint creation | BLOCK DEPLOYMENT |
| Calculations | Exact formulas | Validate calculation output | BLOCK DEPLOYMENT |

### 13.4 ENFORCEMENT RULES

#### Automated Validation
```typescript
// REQUIRED: Add this validation to the component
class MetricsValidator {
  static validate(metrics: any[]): void {
    if (metrics.length !== 7) {
      throw new Error(`COMPLIANCE VIOLATION: Expected 7 metrics, got ${metrics.length}`);
    }
    
    const required = ['Mark Price', 'Current Funding Rate', 'APR', 
                     'Z-Score', 'Percentile', 'Mean', 'Std Dev'];
    const missing = required.filter(m => !metrics.some(metric => 
      metric.label.includes(m)));
    
    if (missing.length > 0) {
      throw new Error(`COMPLIANCE VIOLATION: Missing metrics: ${missing.join(', ')}`);
    }
  }
  
  static validateDOM(): void {
    const metricElements = document.querySelectorAll('[data-metric]');
    if (metricElements.length !== 7) {
      throw new Error(`COMPLIANCE VIOLATION: DOM has ${metricElements.length} metrics, expected 7`);
    }
  }
}

// REQUIRED: Add chart type validation
class ChartValidator {
  static validate(chartProps: any): void {
    if (chartProps.type !== 'area') {
      throw new Error(`COMPLIANCE VIOLATION: Chart must be area type, got ${chartProps.type}`);
    }
    
    if (chartProps.connectNulls !== false) {
      throw new Error('COMPLIANCE VIOLATION: connectNulls must be false');
    }
    
    if (chartProps.interpolation !== undefined && chartProps.interpolation !== 'linear') {
      throw new Error('COMPLIANCE VIOLATION: Interpolation must be linear or undefined');
    }
  }
}

// REQUIRED: Data Quality Validator
class DataQualityValidator {
  static validatePeriodAvailability(completeness: number, maxGap: number, period: number): boolean {
    const gapLimits = { 1: 1, 7: 24, 14: 48, 30: 72 };
    return completeness >= 70 && maxGap <= gapLimits[period];
  }
}
```

#### Runtime Assertions
```typescript
// REQUIRED: Add to component initialization
useEffect(() => {
  // Validate on every render in development
  if (process.env.NODE_ENV === 'development') {
    console.assert(metrics.length === 7, 'VIOLATION: Metric count');
    console.assert(chartType === 'area', 'VIOLATION: Chart type');
    console.assert(dataCompleteness >= 70 || periodDisabled, 'VIOLATION: Completeness threshold');
  }
}, [metrics, chartType, dataCompleteness, periodDisabled]);
```

### 13.5 DEVIATION CONSEQUENCES

Any deviation from this specification will result in:
1. **Immediate code review rejection**
2. **Deployment block via CI/CD pipeline**
3. **Automated rollback if somehow deployed**
4. **Requirement to reimplement from scratch**

### 13.6 COMPLIANCE VERIFICATION SCRIPT

Create and run this script before EVERY commit:
```bash
#!/bin/bash
# compliance_check.sh

echo "Chart Implementation Compliance Check"
echo "====================================="

# Check for exactly 7 metrics
METRIC_COUNT=$(grep -o "metric" HistoricalFundingViewContract.tsx | wc -l)
if [ "$METRIC_COUNT" -ne "7" ]; then
  echo "FAIL: Metric count is $METRIC_COUNT, must be 7"
  exit 1
fi

# Check for area chart
if ! grep -q "type.*area" HistoricalFundingViewContract.tsx; then
  echo "FAIL: Chart type must be area"
  exit 1
fi

# Check for no interpolation
if grep -q "interpolat" HistoricalFundingViewContract.tsx; then
  echo "FAIL: Interpolation is forbidden"
  exit 1
fi

# Check for 70% threshold
if ! grep -q "70" HistoricalFundingViewContract.tsx; then
  echo "FAIL: 70% completeness threshold not found"
  exit 1
fi

echo "All compliance checks passed"
```

### 13.7 ACCEPTANCE CRITERIA

The implementation is ONLY acceptable when:
1. Exactly 7 metrics displayed (no more, no less)
2. Area chart with gradient fills (green positive, red negative)
3. No interpolation across data gaps
4. 70% minimum data completeness enforced
5. Period selection follows exact algorithm
6. Uses only existing API endpoints
7. Z-score formula: (current - mean) / std_dev
8. Percentile uses rank method
9. 4-3 metric layout preserved
10. All validation scripts pass

### 13.8 FINAL COMPLIANCE STATEMENT

**BY IMPLEMENTING THIS FEATURE, YOU ACKNOWLEDGE:**
- This specification is FINAL and IMMUTABLE
- NO creative interpretation is allowed
- NO "improvements" or "optimizations" that deviate from spec
- NO additional features beyond what is specified
- The implementation MUST match this document EXACTLY

**Signature Block for Developer Acknowledgment:**
```
I have read and understood the Chart Implementation Plan.
I will implement EXACTLY as specified with NO deviations.
I understand that any deviation will result in rejection.

Developer: ___________________
Date: _______________________
Reviewed By: ________________
```

### 13.9 SPECIFICATION FREEZE

**This document is FROZEN as of this version.**
- NO amendments allowed without executive approval
- NO clarifications that change requirements
- NO scope additions
- NO technical "improvements"

Any questions about implementation should be resolved by:
1. Re-reading this document
2. Following the specification exactly as written
3. Not adding anything not explicitly required

### 13.10 AUDIT TRAIL REQUIREMENTS

Every implementation must maintain:
```typescript
// REQUIRED: Add to component
const IMPLEMENTATION_METADATA = {
  specVersion: '1.0-FINAL',
  specDocument: 'chartmasala.md',
  implementationDate: new Date().toISOString(),
  deviations: [], // MUST BE EMPTY
  validationPassed: true, // MUST BE TRUE
  metricsCount: 7, // MUST BE 7
  chartType: 'area', // MUST BE 'area'
  interpolationEnabled: false, // MUST BE FALSE
  dataThreshold: 70, // MUST BE 70
  strictCompliance: true // MUST BE TRUE
};
```

## 14. IMPLEMENTATION CHECKLIST

### Pre-Implementation Setup
- [ ] Read this document completely
- [ ] Install required dependencies: `recharts` (already installed)
- [ ] Verify API endpoints are working
- [ ] Create backup of existing component

### Core Implementation Tasks
- [ ] Create validation helper classes (MetricsValidator, ChartValidator, DataQualityValidator)
- [ ] Implement data quality assessment logic
- [ ] Build Key Information Display with exactly 7 metrics
- [ ] Add Period Selector with availability logic
- [ ] Implement Area Chart with green/red gradients
- [ ] Add statistical calculations (Z-score, Percentile)
- [ ] Create compliance verification script
- [ ] Add runtime assertions

### Validation Steps
- [ ] Run TypeScript type check: `cd dashboard && npx tsc --noEmit`
- [ ] Execute compliance script
- [ ] Test with new contract (<1 day data)
- [ ] Test with incomplete data (gaps)
- [ ] Test with different funding intervals
- [ ] Verify exactly 7 metrics render
- [ ] Verify area chart with no interpolation
- [ ] Check period availability logic

### Final Verification
- [ ] All 7 metrics display correctly
- [ ] Chart is area type with gradients
- [ ] No interpolation across gaps
- [ ] 70% completeness threshold enforced
- [ ] Period selection follows specification
- [ ] All validation scripts pass

## 15. COMMON IMPLEMENTATION PATTERNS

### Pattern 1: Fetching and Processing Data
```typescript
const fetchContractData = async () => {
  // Parallel fetch for efficiency
  const [statsResponse, historicalResponse] = await Promise.all([
    fetch(`/api/contracts-with-zscores?exchange=${exchange}&symbol=${symbol}`),
    fetch(`/api/historical-funding-by-contract/${exchange}/${symbol}?days=30`)
  ]);
  
  const stats = await statsResponse.json();
  const historical = await historicalResponse.json();
  
  // Process historical data - ALWAYS convert to percentage
  const processedData = historical.data.map(item => ({
    ...item,
    funding_rate: item.funding_rate !== null ? item.funding_rate * 100 : null,
    displayTime: new Date(item.timestamp).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC'
    })
  }));
  
  return { stats, historical: processedData };
};
```

### Pattern 2: Period Availability Assessment
```typescript
const assessPeriodAvailability = (data: HistoricalDataPoint[], fundingInterval: number) => {
  const periods = [1, 7, 14, 30];
  const availability: Record<number, PeriodInfo> = {};
  
  periods.forEach(days => {
    const expectedPoints = (days * 24) / fundingInterval;
    const cutoffTime = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    const periodData = data.filter(d => new Date(d.timestamp) >= cutoffTime);
    const actualPoints = periodData.filter(d => d.funding_rate !== null).length;
    const completeness = (actualPoints / expectedPoints) * 100;
    
    // Calculate max gap
    let maxGap = 0;
    for (let i = 1; i < periodData.length; i++) {
      const gap = new Date(periodData[i].timestamp).getTime() - 
                  new Date(periodData[i-1].timestamp).getTime();
      maxGap = Math.max(maxGap, gap / (60 * 60 * 1000)); // Convert to hours
    }
    
    const gapLimits = { 1: fundingInterval, 7: 24, 14: 48, 30: 72 };
    
    availability[days] = {
      enabled: completeness >= 70 && maxGap <= gapLimits[days],
      completeness,
      quality: completeness >= 90 ? 'high' : completeness >= 70 ? 'medium' : 'low',
      showWarning: completeness >= 50 && completeness < 70
    };
  });
  
  return availability;
};
```

### Pattern 3: Metric Display Component
```typescript
const MetricDisplay: React.FC<{label: string, value: any, format: string}> = ({ label, value, format }) => {
  const formatValue = () => {
    if (value === null || value === undefined) return '--';
    
    switch (format) {
      case 'currency':
        return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      case 'percentage':
        return `${value.toFixed(4)}%`;
      case 'decimal':
        return value.toFixed(2);
      case 'ordinal':
        const suffix = value === 1 ? 'st' : value === 2 ? 'nd' : value === 3 ? 'rd' : 'th';
        return `${value}${suffix}`;
      default:
        return value.toString();
    }
  };
  
  return (
    <div className="metric-item" data-metric={label.toLowerCase().replace(/\s+/g, '-')}>
      <div className="text-sm text-gray-500">{label}</div>
      <div className="text-lg font-semibold">{formatValue()}</div>
    </div>
  );
};
```