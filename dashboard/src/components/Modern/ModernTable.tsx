import React from 'react';
import clsx from 'clsx';

interface Column<T> {
  key: string;
  header: string | React.ReactNode;
  accessor: keyof T | ((row: T) => React.ReactNode);
  align?: 'left' | 'center' | 'right';
  width?: string;
  sortable?: boolean;
  className?: string;
}

interface ModernTableProps<T> {
  columns: Column<T>[];
  data: T[];
  className?: string;
  striped?: boolean;
  hover?: boolean;
  compact?: boolean;
  loading?: boolean;
  emptyMessage?: string;
  onRowClick?: (row: T, index: number) => void;
  selectedRows?: number[];
  onSort?: (key: string, direction: 'asc' | 'desc') => void;
  sortKey?: string;
  sortDirection?: 'asc' | 'desc';
  stickyHeader?: boolean;
}

function ModernTable<T extends Record<string, any>>({
  columns,
  data,
  className,
  striped = true,
  hover = true,
  compact = false,
  loading = false,
  emptyMessage = 'No data available',
  onRowClick,
  selectedRows = [],
  onSort,
  sortKey,
  sortDirection,
  stickyHeader = false,
}: ModernTableProps<T>) {
  const getCellValue = (row: T, column: Column<T>) => {
    if (typeof column.accessor === 'function') {
      return column.accessor(row);
    }
    return row[column.accessor as keyof T];
  };

  const handleSort = (column: Column<T>) => {
    if (column.sortable && onSort) {
      const newDirection =
        sortKey === column.key && sortDirection === 'asc' ? 'desc' : 'asc';
      onSort(column.key, newDirection);
    }
  };

  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  const cellPadding = compact ? 'px-3 py-2' : 'px-4 py-3';

  if (loading) {
    return (
      <div className="w-full bg-white rounded-lg border border-border p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-text-secondary text-sm">Loading data...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="w-full bg-white rounded-lg border border-border p-8">
        <div className="text-center text-text-secondary">
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('w-full overflow-auto rounded-lg border border-border bg-white', className)}>
      <table className="w-full">
        <thead className={clsx(
          'bg-gray-50 border-b border-border',
          { 'sticky top-0 z-10': stickyHeader }
        )}>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={clsx(
                  cellPadding,
                  'text-xs font-semibold text-text-secondary uppercase tracking-wider',
                  alignClasses[column.align || 'left'],
                  {
                    'cursor-pointer hover:bg-gray-100 transition-colors duration-150': column.sortable,
                  },
                  column.className
                )}
                style={{ width: column.width }}
                onClick={() => handleSort(column)}
              >
                <div className="flex items-center gap-1">
                  <span>{column.header}</span>
                  {column.sortable && (
                    <span className="inline-block ml-1">
                      {sortKey === column.key ? (
                        sortDirection === 'asc' ? (
                          <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M7 10l5-5 5 5H7z" />
                          </svg>
                        ) : (
                          <svg className="w-3 h-3" viewBox="0 0 20 20" fill="currentColor">
                            <path d="M17 10l-5 5-5-5h10z" />
                          </svg>
                        )
                      ) : (
                        <svg className="w-3 h-3 opacity-40" viewBox="0 0 20 20" fill="currentColor">
                          <path d="M7 7l5-5 5 5M7 13l5 5 5-5" />
                        </svg>
                      )}
                    </span>
                  )}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {data.map((row, rowIndex) => (
            <tr
              key={rowIndex}
              className={clsx(
                'transition-colors duration-150',
                {
                  'bg-gray-50': striped && rowIndex % 2 === 1,
                  'hover:bg-gray-50': hover,
                  'cursor-pointer': onRowClick,
                  'bg-primary-50 hover:bg-primary-100': selectedRows.includes(rowIndex),
                }
              )}
              onClick={() => onRowClick?.(row, rowIndex)}
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={clsx(
                    cellPadding,
                    'text-sm text-text-primary',
                    alignClasses[column.align || 'left'],
                    column.className
                  )}
                  style={{ width: column.width }}
                >
                  {getCellValue(row, column)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default ModernTable;