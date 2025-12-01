import React, { useRef, memo, useCallback } from 'react';
import {
  flexRender,
  Table as TanStackTable,
  Row,
  Cell,
} from '@tanstack/react-table';
import { useVirtualizer, VirtualItem } from '@tanstack/react-virtual';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../ui/table';
import { Skeleton } from '../../ui/skeleton';
import { Badge } from '../../ui/badge';

const ROW_HEIGHT_COLLAPSED = 48;
const ROW_HEIGHT_EXPANDED = 448;
const VIRTUALIZER_OVERSCAN = 5;
const SKELETON_ROWS = Array.from({ length: 10 }, (_, i) => i);

interface DataTableRowProps<TData extends { asset: string }> {
  row: Row<TData>;
  virtualRow: VirtualItem;
  isExpanded: boolean;
  isAutoExpanded: boolean;
  onToggleExpand: (asset: string) => void;
  renderSubComponent?: (row: Row<TData>) => React.ReactNode;
  viewMode: string;
}

const DataTableRowComponent = <TData extends { asset: string }>({
  row,
  virtualRow,
  isExpanded,
  isAutoExpanded,
  onToggleExpand,
  renderSubComponent,
}: DataTableRowProps<TData>) => {
  const asset = row.original.asset;

  return (
    <React.Fragment>
      <TableRow
        data-index={virtualRow.index}
        data-state={row.getIsSelected() && 'selected'}
        className="hover:bg-muted/50 transition-colors cursor-pointer"
        onClick={() => onToggleExpand(asset)}
      >
        {row.getVisibleCells().map((cell: Cell<TData, unknown>, cellIndex: number) => (
          <TableCell
            key={cell.id}
            className={cell.column.columnDef.meta?.cellClassName}
            style={cell.column.columnDef.meta?.cellStyle}
          >
            {cellIndex === 0 ? (
              <div className="flex items-center space-x-2">
                <span className="text-muted-foreground text-xs">
                  {isExpanded ? '▼' : '▶'}
                </span>
                {flexRender(
                  cell.column.columnDef.cell,
                  cell.getContext()
                )}
                {isAutoExpanded && (
                  <Badge variant="secondary" className="text-xs">
                    Contract Match
                  </Badge>
                )}
              </div>
            ) : (
              flexRender(
                cell.column.columnDef.cell,
                cell.getContext()
              )
            )}
          </TableCell>
        ))}
      </TableRow>
      {isExpanded && renderSubComponent && (
        <TableRow className="expand-animation">
          <TableCell
            colSpan={row.getVisibleCells().length}
            className="p-0"
          >
            {renderSubComponent(row)}
          </TableCell>
        </TableRow>
      )}
    </React.Fragment>
  );
};

const MemoizedDataTableRow = memo(DataTableRowComponent, (prevProps, nextProps) => {
  return (
    prevProps.row.id === nextProps.row.id &&
    prevProps.isExpanded === nextProps.isExpanded &&
    prevProps.isAutoExpanded === nextProps.isAutoExpanded &&
    prevProps.virtualRow.index === nextProps.virtualRow.index &&
    prevProps.row.original === nextProps.row.original &&
    prevProps.viewMode === nextProps.viewMode
  );
}) as typeof DataTableRowComponent;

interface DataTableProps<TData extends { asset: string }> {
  table: TanStackTable<TData>;
  loading?: boolean;
  expandedAssets: Set<string>;
  autoExpandedAssets: Set<string>;
  onToggleExpand: (asset: string) => void;
  renderSubComponent?: (row: Row<TData>) => React.ReactNode;
  viewMode: string;
}

export function DataTable<TData extends { asset: string }>({
  table,
  loading = false,
  expandedAssets,
  autoExpandedAssets,
  onToggleExpand,
  renderSubComponent,
  viewMode,
}: DataTableProps<TData>) {
  const tableContainerRef = useRef<HTMLDivElement>(null);
  const rows = table.getRowModel().rows;

  const estimateSize = useCallback((index: number) => {
    const row = rows[index];
    if (!row) return ROW_HEIGHT_COLLAPSED;
    const isExpanded = expandedAssets.has(row.original.asset);
    return isExpanded ? ROW_HEIGHT_EXPANDED : ROW_HEIGHT_COLLAPSED;
  }, [rows, expandedAssets]);

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize,
    overscan: VIRTUALIZER_OVERSCAN,
  });

  const virtualRows = rowVirtualizer.getVirtualItems();
  const totalSize = rowVirtualizer.getTotalSize();

  const paddingTop = virtualRows.length > 0 ? virtualRows[0]?.start || 0 : 0;
  const paddingBottom = virtualRows.length > 0
    ? totalSize - (virtualRows[virtualRows.length - 1]?.end || 0)
    : 0;

  const shouldUseVirtualization = virtualRows.length > 0;
  const rowsToRender = shouldUseVirtualization
    ? virtualRows.map((vr) => ({ row: rows[vr.index], virtualRow: vr }))
    : rows.map((row, index) => ({ row, virtualRow: { index, start: 0, end: 0, size: 0, key: index, lane: 0 } }));

  if (loading) {
    return (
      <div className="bg-background rounded-xl p-8 shadow-lg border border-border">
        <div className="space-y-4">
          <Skeleton className="h-8 w-1/4" />
          <Skeleton className="h-4 w-full" />
          <div className="space-y-2">
            {SKELETON_ROWS.map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={tableContainerRef}
      className="relative overflow-auto h-[800px] border rounded-md"
    >
      <Table>
        <TableHeader className="sticky top-0 z-20 bg-background">
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id} className="bg-muted">
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className={header.column.columnDef.meta?.headerClassName}
                  style={header.column.columnDef.meta?.headerStyle}
                >
                  {header.isPlaceholder
                    ? null
                    : flexRender(
                        header.column.columnDef.header,
                        header.getContext()
                      )}
                </TableHead>
              ))}
            </TableRow>
          ))}
        </TableHeader>
        <TableBody>
          {rows.length ? (
            <>
              {shouldUseVirtualization && paddingTop > 0 && (
                <tr>
                  <td style={{ height: `${paddingTop}px` }} />
                </tr>
              )}
              {rowsToRender.map(({ row, virtualRow }) => (
                <MemoizedDataTableRow
                  key={row.id}
                  row={row}
                  virtualRow={virtualRow}
                  isExpanded={expandedAssets.has(row.original.asset)}
                  isAutoExpanded={autoExpandedAssets.has(row.original.asset)}
                  onToggleExpand={onToggleExpand}
                  renderSubComponent={renderSubComponent}
                  viewMode={viewMode}
                />
              ))}
              {shouldUseVirtualization && paddingBottom > 0 && (
                <tr>
                  <td style={{ height: `${paddingBottom}px` }} />
                </tr>
              )}
            </>
          ) : (
            <TableRow>
              <TableCell
                colSpan={table.getHeaderGroups()[0]?.headers.length || 1}
                className="h-24 text-center"
              >
                No results found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
