import React, { useState, useEffect } from 'react';
import styles from './ArbitrageFilter.module.css';

interface APRRangeFilterProps {
  minApr: number | null;
  maxApr: number | null;
  onChange: (range: { minApr: number | null; maxApr: number | null }) => void;
}

export const APRRangeFilter: React.FC<APRRangeFilterProps> = ({
  minApr,
  maxApr,
  onChange
}) => {
  const [error, setError] = useState<string | null>(null);

  // Validate range
  useEffect(() => {
    if (minApr !== null && maxApr !== null && minApr > maxApr) {
      setError('Min APR cannot exceed Max APR');
    } else {
      setError(null);
    }
  }, [minApr, maxApr]);

  const handleMinChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minApr: value === 'null' ? null : Number(value),
      maxApr
    });
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minApr,
      maxApr: value === 'null' ? null : Number(value)
    });
  };

  return (
    <div className={styles.filterSection}>
      <div className={styles.sectionLabel}>APR Spread</div>

      <div className={styles.inputRow}>
        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Min APR Spread</label>
          <select
            className={styles.selectField}
            value={minApr === null ? 'null' : minApr}
            onChange={handleMinChange}
            aria-label="Min APR"
          >
            <option value="null">No minimum</option>
            <option value="5">5%</option>
            <option value="10">10%</option>
            <option value="20">20%</option>
            <option value="30">30%</option>
            <option value="50">50%</option>
            <option value="75">75%</option>
            <option value="100">100%</option>
          </select>
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Max APR Spread</label>
          <select
            className={styles.selectField}
            value={maxApr === null ? 'null' : maxApr}
            onChange={handleMaxChange}
            aria-label="Max APR"
          >
            <option value="50">50%</option>
            <option value="100">100%</option>
            <option value="200">200%</option>
            <option value="500">500%</option>
            <option value="1000">1000%</option>
            <option value="null">No limit</option>
          </select>
        </div>
      </div>

      {error && (
        <p style={{ marginTop: '8px', fontSize: '12px', color: '#DC2626' }}>
          {error}
        </p>
      )}
    </div>
  );
};

export default APRRangeFilter;