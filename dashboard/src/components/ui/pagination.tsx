import * as React from "react"
import { cn } from "@/lib/utils"
import { Button } from "./button"
import { ChevronLeftIcon, ChevronRightIcon } from "@radix-ui/react-icons"

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  className?: string;
}

const Pagination: React.FC<PaginationProps> = ({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  className,
}) => {
  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  if (totalPages <= 1) {
    return (
      <div className={cn('text-sm text-muted-foreground', className)}>
        Showing <span className="font-medium text-foreground">{startItem}</span> to{' '}
        <span className="font-medium text-foreground">{endItem}</span> of{' '}
        <span className="font-medium text-foreground">{totalItems}</span> results
      </div>
    );
  }

  return (
    <div className={cn('flex items-center justify-between', className)}>
      <div className="text-sm text-muted-foreground">
        Showing <span className="font-medium text-foreground">{startItem}</span> to{' '}
        <span className="font-medium text-foreground">{endItem}</span> of{' '}
        <span className="font-medium text-foreground">{totalItems}</span> results
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
        >
          <ChevronLeftIcon className="h-4 w-4 mr-1" />
          Previous
        </Button>

        <div className="px-3 py-1.5 text-sm font-medium bg-muted rounded-md">
          Page {currentPage} of {totalPages}
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
        >
          Next
          <ChevronRightIcon className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  );
};

export { Pagination };
