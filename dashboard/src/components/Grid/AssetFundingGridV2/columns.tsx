import { ColumnDef } from '@tanstack/react-table';
import { AssetGridData, ViewMode } from './types';
import { getDisplayValue } from './utils';
import { GridCell } from './GridCell';

export interface ColumnContext {
  viewMode: ViewMode;
  highlightMissing: boolean;
}

export const createAssetColumn = (): ColumnDef<AssetGridData> => ({
  id: 'asset',
  accessorKey: 'asset',
  header: ({ column }) => (
    <div
      onClick={() => column.toggleSorting()}
      className="cursor-pointer hover:text-foreground select-none"
    >
      Asset {column.getIsSorted() === 'asc' ? '↑' : column.getIsSorted() === 'desc' ? '↓' : ''}
    </div>
  ),
  cell: ({ getValue }) => {
    const asset = getValue() as string;
    return (
      <span className="text-sm font-medium text-foreground">
        {asset}
      </span>
    );
  },
  meta: {
    headerClassName: 'px-2 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-muted sticky left-0 bg-muted z-10',
    cellClassName: 'px-2 py-3 whitespace-nowrap sticky left-0 bg-background z-10 border-r border-border',
  },
  enableSorting: true,
});

export const createExchangeColumns = (
  exchanges: string[],
  context: ColumnContext
): ColumnDef<AssetGridData>[] => {
  return exchanges.map(exchange => ({
    id: exchange,
    accessorFn: (row) => {
      return getDisplayValue(row, exchange, context.viewMode);
    },
    header: ({ column }) => (
      <div
        onClick={() => column.toggleSorting()}
        className="cursor-pointer hover:text-foreground select-none text-center"
      >
        {exchange}
        {column.getIsSorted() === 'asc' ? ' ↑' : column.getIsSorted() === 'desc' ? ' ↓' : ''}
      </div>
    ),
    cell: ({ row }) => {
      const displayValue = getDisplayValue(row.original, exchange, context.viewMode);
      const isMissing = displayValue === null || displayValue === undefined;
      const shouldHighlight = context.highlightMissing && isMissing;

      return (
        <GridCell
          value={displayValue}
          viewMode={context.viewMode}
          shouldHighlight={shouldHighlight}
        />
      );
    },
    meta: {
      headerClassName: 'px-1 py-2 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:bg-muted min-w-14',
      cellClassName: 'px-1 py-2 text-center whitespace-nowrap text-sm min-w-14',
    },
    enableSorting: true,
    sortingFn: (rowA, rowB, columnId) => {
      const aVal = getDisplayValue(rowA.original, columnId, context.viewMode) ?? -999;
      const bVal = getDisplayValue(rowB.original, columnId, context.viewMode) ?? -999;

      return aVal - bVal;
    },
  }));
};

export const createColumns = (
  exchanges: string[],
  context: ColumnContext
): ColumnDef<AssetGridData>[] => {
  return [
    createAssetColumn(),
    ...createExchangeColumns(exchanges, context),
  ];
};
