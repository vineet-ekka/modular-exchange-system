import * as React from "react"
import { cn } from "@/lib/utils"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./table"

interface Column<T> {
  key: string;
  header: string | React.ReactNode;
  accessor: keyof T | ((row: T) => React.ReactNode);
  align?: 'left' | 'center' | 'right';
  width?: string;
  sortable?: boolean;
  className?: string;
}

interface DataTableProps<T> {
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

function DataTable<T>({
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
}: DataTableProps<T>) {
  const getCellValue = (row: T, column: Column<T>) => {
    if (typeof column.accessor === 'function') {
      return column.accessor(row);
    }
    return row[column.accessor as keyof T] as React.ReactNode;
  };

  const handleSort = (column: Column<T>) => {
    if (column.sortable && onSort) {
      const newDirection = sortKey === column.key && sortDirection === 'asc' ? 'desc' : 'asc';
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
      <div className="w-full rounded-lg border p-8">
        <div className="flex flex-col items-center justify-center space-y-4">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-muted-foreground text-sm">Loading data...</p>
        </div>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="w-full rounded-lg border p-8">
        <div className="text-center text-muted-foreground">{emptyMessage}</div>
      </div>
    );
  }

  return (
    <div className={cn('w-full overflow-auto rounded-lg border', className)}>
      <Table>
        <TableHeader className={cn(stickyHeader && 'sticky top-0 z-10 bg-muted')}>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.key}
                className={cn(
                  cellPadding,
                  alignClasses[column.align || 'left'],
                  column.sortable && 'cursor-pointer hover:bg-muted/50',
                  column.className
                )}
                style={{ width: column.width }}
                onClick={() => handleSort(column)}
              >
                <div className={cn(
                  "flex items-center gap-1",
                  column.align === 'center' && 'justify-center',
                  column.align === 'right' && 'justify-end'
                )}>
                  <span>{column.header}</span>
                  {column.sortable && sortKey === column.key && (
                    <span className="ml-1">
                      {sortDirection === 'asc' ? '\u25B2' : '\u25BC'}
                    </span>
                  )}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, rowIndex) => (
            <TableRow
              key={rowIndex}
              className={cn(
                striped && rowIndex % 2 === 1 && 'bg-muted/50',
                hover && 'hover:bg-muted/50',
                onRowClick && 'cursor-pointer',
                selectedRows.includes(rowIndex) && 'bg-primary/10'
              )}
              onClick={() => onRowClick?.(row, rowIndex)}
            >
              {columns.map((column) => (
                <TableCell
                  key={column.key}
                  className={cn(cellPadding, alignClasses[column.align || 'left'], column.className)}
                  style={{ width: column.width }}
                >
                  {getCellValue(row, column)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

export { DataTable, type Column };
