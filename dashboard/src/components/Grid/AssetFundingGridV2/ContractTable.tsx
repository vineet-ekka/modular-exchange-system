import React, { useRef, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { cn } from '../../../lib/utils';
import { ContractDetails } from '../../../services/api';
import { ContractLink } from '../../ContractLink';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../ui/table';
import { Button } from '../../ui/button';
import {
  formatRate,
  formatInterval,
  formatOpenInterest,
  formatPrice,
  getZScoreColor,
  getPercentileColor,
  doesContractMatchSearch,
} from './utils';

interface ContractTableProps {
  contracts: ContractDetails[];
  asset: string;
  searchTerm: string;
  loading?: boolean;
}

const ContractTableComponent: React.FC<ContractTableProps> = ({
  contracts,
  asset,
  searchTerm,
  loading = false,
}) => {
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (typeof IntersectionObserver === 'undefined') {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setIsVisible(true);
          }
        });
      },
      { threshold: 0.1 }
    );

    if (containerRef.current) {
      observer.observe(containerRef.current);
    }

    return () => observer.disconnect();
  }, []);

  if (loading) {
    return (
      <div className="p-4 text-center">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto"></div>
        <p className="text-sm text-muted-foreground mt-2">Loading contracts...</p>
      </div>
    );
  }

  if (!contracts || contracts.length === 0) {
    return (
      <div className="p-4 text-center text-muted-foreground">
        No contracts found for {asset}
      </div>
    );
  }

  return (
    <div ref={containerRef}>
      {!isVisible ? (
        <div className="flex items-center justify-center h-[400px] bg-muted/50 border-t border-b border-border">
          <span className="text-muted-foreground">Scroll to load contracts...</span>
        </div>
      ) : (
    <div className="bg-muted/50 border-t border-b border-border">
      <Table className="table-fixed w-full">
        <TableHeader>
          <TableRow className="bg-muted">
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[9%]">
              Contract Name
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[8%]">
              Exchange Name
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[6%]">
              Base Asset
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[5%]">
              Quote Asset
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[5%]">
              Interval
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[8%]">
              Funding Rate
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[7%]">
              APR
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[10%]">
              Open Interest USD
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[8%]">
              Mark Price
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[8%]">
              Index Price
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[6%]">
              Z-Score
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[5%]">
              Percentile
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[5%]">
              Mean(30d)
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[5%]">
              StdDev
            </TableHead>
            <TableHead className="px-3 py-2 text-center font-medium text-muted-foreground w-[5%]">
              Actions
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {contracts.map((contract, idx) => {
            const isContractMatch = doesContractMatchSearch(contract, searchTerm);

            return (
              <TableRow
                key={`${contract.exchange}-${contract.symbol}`}
                className={cn(
                  idx % 2 === 0 ? 'bg-background' : 'bg-muted/30',
                  isContractMatch && 'ring-2 ring-primary/50'
                )}
              >
                <TableCell
                  className={cn(
                    'px-3 py-2 text-xs text-center font-medium',
                    isContractMatch && 'text-primary font-semibold'
                  )}
                >
                  <ContractLink
                    exchange={contract.exchange}
                    symbol={contract.symbol}
                    baseAsset={contract.base_asset}
                    isActive={true}
                    hoursSinceUpdate={0}
                    className={isContractMatch ? 'text-primary font-semibold' : 'text-foreground'}
                  />
                </TableCell>
                <TableCell className="px-3 py-2 text-xs text-center text-muted-foreground">{contract.exchange}</TableCell>
                <TableCell className="px-3 py-2 text-xs text-center text-muted-foreground">{contract.base_asset}</TableCell>
                <TableCell className="px-3 py-2 text-xs text-center text-muted-foreground">{contract.quote_asset}</TableCell>
                <TableCell className="px-3 py-2 text-xs text-center font-medium text-muted-foreground">
                  {formatInterval(contract.funding_interval_hours)}
                </TableCell>
                <TableCell
                  className={cn(
                    'px-3 py-2 text-xs text-center font-medium',
                    contract.funding_rate > 0
                      ? 'text-green-600'
                      : contract.funding_rate < 0
                      ? 'text-red-600'
                      : 'text-muted-foreground'
                  )}
                >
                  {formatRate(contract.funding_rate)}
                </TableCell>
                <TableCell
                  className={cn(
                    'px-3 py-2 text-xs text-center font-medium',
                    (contract.apr ?? 0) > 0
                      ? 'text-green-600'
                      : (contract.apr ?? 0) < 0
                      ? 'text-red-600'
                      : 'text-muted-foreground'
                  )}
                >
                  {contract.apr !== null && contract.apr !== undefined
                    ? `${contract.apr.toFixed(2)}%`
                    : '-'}
                </TableCell>
                <TableCell className="px-3 py-2 text-xs text-center text-muted-foreground">
                  {formatOpenInterest(contract)}
                </TableCell>
                <TableCell className="px-3 py-2 text-xs text-center text-muted-foreground">
                  {formatPrice(contract.mark_price)}
                </TableCell>
                <TableCell className="px-3 py-2 text-xs text-center text-muted-foreground">
                  {formatPrice(contract.index_price)}
                </TableCell>
                <TableCell className={cn('px-3 py-2 text-xs text-center font-medium', getZScoreColor(contract.current_z_score))}>
                  {contract.current_z_score !== null && contract.current_z_score !== undefined
                    ? contract.current_z_score.toFixed(2)
                    : '-'}
                </TableCell>
                <TableCell className={cn('px-3 py-2 text-xs text-center font-medium', getPercentileColor(contract.current_percentile))}>
                  {contract.current_percentile !== null && contract.current_percentile !== undefined
                    ? `${Math.round(contract.current_percentile)}%`
                    : '-'}
                </TableCell>
                <TableCell className="px-3 py-2 text-center text-xs">
                  {contract.mean_30d !== null && contract.mean_30d !== undefined
                    ? `${(contract.mean_30d * 100).toFixed(4)}%`
                    : '-'}
                </TableCell>
                <TableCell className="px-3 py-2 text-center text-xs">
                  {contract.std_dev_30d !== null && contract.std_dev_30d !== undefined
                    ? `${(contract.std_dev_30d * 100).toFixed(4)}%`
                    : '-'}
                </TableCell>
                <TableCell className="px-3 py-2 text-center">
                  <Button
                    variant="link"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/historical/${contract.exchange}/${contract.symbol}`);
                    }}
                    className="text-xs text-primary hover:text-primary/80 p-0 h-auto"
                  >
                    History
                  </Button>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
      )}
    </div>
  );
};

export const ContractTable = React.memo(ContractTableComponent, (prevProps, nextProps) => {
  return (
    prevProps.contracts === nextProps.contracts &&
    prevProps.asset === nextProps.asset &&
    prevProps.searchTerm === nextProps.searchTerm &&
    prevProps.loading === nextProps.loading
  );
});

ContractTable.displayName = 'ContractTable';
