import React, { useMemo } from 'react';
import clsx from 'clsx';
import { Pagination } from '../../ui/pagination';
import { HistoricalDataPoint } from './useContractHistoricalData';

const formatChartTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const month = monthNames[date.getUTCMonth()];
  const day = date.getUTCDate();
  const hours = date.getUTCHours();
  const minutes = date.getUTCMinutes();
  const period = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;

  const timeString = minutes === 0
    ? `${displayHours} ${period}`
    : `${displayHours}:${minutes.toString().padStart(2, '0')} ${period}`;

  return `${month} ${day}, ${timeString}`;
};

interface ContractHistoricalTableProps {
  data: HistoricalDataPoint[];
  currentPage: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export const ContractHistoricalTable = React.memo<ContractHistoricalTableProps>(({
  data,
  currentPage,
  pageSize,
  onPageChange
}) => {
  const totalPages = Math.ceil(data.length / pageSize);

  const paginatedData = useMemo(() => {
    const reversedData = [...data].reverse();
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return reversedData.slice(startIndex, endIndex);
  }, [data, currentPage, pageSize]);

  return (
    <div className="p-6">
      <h3 className="text-lg font-medium text-gray-700 mb-4">Historical Data</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-2 text-left text-text-secondary font-medium">
                Timestamp (UTC)
              </th>
              <th className="px-4 py-2 text-center text-text-secondary font-medium">
                Funding Rate (%)
              </th>
              <th className="px-4 py-2 text-center text-text-secondary font-medium">
                APR (%)
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-light-border">
            {paginatedData.map((item, index) => (
              <tr key={index} className="hover:bg-gray-50">
                <td className="px-4 py-2 text-text-secondary">
                  {formatChartTime(item.timestamp)}
                </td>
                <td className={clsx(
                  'px-4 py-2 text-center',
                  item.funding_rate !== null && item.funding_rate > 0 ? 'text-funding-positive' :
                  item.funding_rate !== null && item.funding_rate < 0 ? 'text-funding-negative' :
                  'text-funding-neutral'
                )}>
                  {item.funding_rate !== null ? item.funding_rate.toFixed(4) : '-'}
                </td>
                <td className={clsx(
                  'px-4 py-2 text-center',
                  item.apr !== null && item.apr > 0 ? 'text-funding-positive' :
                  item.apr !== null && item.apr < 0 ? 'text-funding-negative' :
                  'text-funding-neutral'
                )}>
                  {item.apr !== null ? `${item.apr.toFixed(2)}%` : '-'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4">
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            pageSize={pageSize}
            totalItems={data.length}
            onPageChange={onPageChange}
          />
        </div>
      )}

      {totalPages === 1 && (
        <div className="mt-4 text-sm text-text-secondary text-center">
          Showing all {data.length} results
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.data === nextProps.data &&
    prevProps.currentPage === nextProps.currentPage &&
    prevProps.pageSize === nextProps.pageSize
  );
});

ContractHistoricalTable.displayName = 'ContractHistoricalTable';
