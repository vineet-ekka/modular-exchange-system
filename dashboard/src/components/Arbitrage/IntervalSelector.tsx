import React from 'react';
import styles from './ArbitrageFilter.module.css';

const FUNDING_INTERVALS = [
  { hours: 1, label: '1 hour' },
  { hours: 4, label: '4 hours' },
  { hours: 8, label: '8 hours' },
  { hours: 24, label: '24 hours' },
];

interface IntervalSelectorProps {
  selectedIntervals: Set<number>;
  onChange: (intervals: Set<number>) => void;
}

export const IntervalSelector: React.FC<IntervalSelectorProps> = ({
  selectedIntervals,
  onChange
}) => {
  const toggleInterval = (hours: number) => {
    const newSet = new Set(selectedIntervals);
    if (newSet.has(hours)) {
      newSet.delete(hours);
    } else {
      newSet.add(hours);
    }
    onChange(newSet);
  };

  return (
    <div className={styles.filterSection}>
      <div className={styles.sectionLabel}>Funding Intervals</div>

      <div className={styles.intervalPills}>
        {FUNDING_INTERVALS.map(({ hours, label }) => (
          <button
            key={hours}
            onClick={() => toggleInterval(hours)}
            className={`${styles.intervalPill} ${
              selectedIntervals.has(hours) ? styles.selected : ''
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {selectedIntervals.size === 0 && (
        <p style={{ marginTop: '8px', fontSize: '12px', color: '#A3A3A3' }}>
          No intervals selected - showing all opportunities
        </p>
      )}
    </div>
  );
};

export default IntervalSelector;