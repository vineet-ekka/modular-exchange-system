import '@tanstack/react-table';

declare module '@tanstack/react-table' {
  interface ColumnMeta<TData, TValue> {
    headerClassName?: string;
    headerStyle?: React.CSSProperties;
    cellClassName?: string;
    cellStyle?: React.CSSProperties;
  }
}
