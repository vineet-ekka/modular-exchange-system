import React from 'react';
import clsx from 'clsx';

interface Column<T> {
  key: string;
  header: string;
  render?: (value: any, item: T) => React.ReactNode;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

interface NeumorphicTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyExtractor: (item: T) => string;
  className?: string;
  onRowClick?: (item: T) => void;
  emptyMessage?: string;
}

function NeumorphicTable<T>({
  columns,
  data,
  keyExtractor,
  className,
  onRowClick,
  emptyMessage = 'No data available'
}: NeumorphicTableProps<T>) {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right'
  };

  return (
    <div className={clsx('bg-neumorphic-bg rounded-xl overflow-hidden shadow-neumorphic', className)}>
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="bg-gradient-to-br from-neumorphic-bg-dark to-neumorphic-bg-light">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={clsx(
                    'px-4 py-3 text-xs font-semibold text-neumorphic-text-secondary uppercase tracking-wider',
                    'shadow-neumorphic-inset-sm',
                    alignClasses[column.align || 'left'],
                    column.className
                  )}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-neumorphic-shadow-dark/10">
            {data.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-neumorphic-text-muted"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((item) => (
                <tr
                  key={keyExtractor(item)}
                  className={clsx(
                    'transition-all duration-200',
                    'hover:bg-gradient-to-br hover:from-neumorphic-bg-light hover:to-neumorphic-bg',
                    'hover:shadow-neumorphic-hover',
                    onRowClick && 'cursor-pointer'
                  )}
                  onClick={() => onRowClick?.(item)}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={clsx(
                        'px-4 py-3 text-sm text-neumorphic-text-primary',
                        alignClasses[column.align || 'left'],
                        column.className
                      )}
                    >
                      {column.render
                        ? column.render((item as any)[column.key], item)
                        : (item as any)[column.key]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default NeumorphicTable;