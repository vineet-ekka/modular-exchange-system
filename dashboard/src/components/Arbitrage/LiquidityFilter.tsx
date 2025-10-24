import React from 'react';
import styles from './ArbitrageFilter.module.css';

interface LiquidityFilterProps {
  minOIEither: number | null;
  minOICombined: number | null;
  onChange: (liquidity: { minOIEither: number | null; minOICombined: number | null }) => void;
}

export const LiquidityFilter: React.FC<LiquidityFilterProps> = ({
  minOIEither,
  minOICombined,
  onChange
}) => {
  const handleEitherChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minOIEither: value === 'null' ? null : Number(value),
      minOICombined
    });
  };

  const handleCombinedChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    onChange({
      minOIEither,
      minOICombined: value === 'null' ? null : Number(value)
    });
  };

  return (
    <div className={styles.filterSection}>
      <div className={styles.sectionLabel}>Liquidity Requirements</div>

      <div className={styles.inputRow}>
        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Min OI (Either)</label>
          <select
            className={styles.selectField}
            value={minOIEither === null ? 'null' : minOIEither}
            onChange={handleEitherChange}
          >
            <option value="null">No minimum</option>
            <option value="10000">$10K</option>
            <option value="100000">$100K</option>
            <option value="1000000">$1M</option>
            <option value="10000000">$10M</option>
          </select>
        </div>

        <div className={styles.inputGroup}>
          <label className={styles.inputLabel}>Min Combined OI</label>
          <select
            className={styles.selectField}
            value={minOICombined === null ? 'null' : minOICombined}
            onChange={handleCombinedChange}
          >
            <option value="null">No minimum</option>
            <option value="100000">$100K</option>
            <option value="500000">$500K</option>
            <option value="1000000">$1M</option>
            <option value="10000000">$10M</option>
          </select>
        </div>
      </div>

      <p style={{ marginTop: '8px', fontSize: '12px', color: '#A3A3A3' }}>
        Filter by minimum open interest for trade execution feasibility
      </p>
    </div>
  );
};

export default LiquidityFilter;