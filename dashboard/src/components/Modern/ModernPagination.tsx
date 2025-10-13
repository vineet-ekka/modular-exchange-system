import React from 'react';
import clsx from 'clsx';
import ModernButton from './ModernButton';

interface ModernPaginationProps {
  currentPage: number;
  totalPages: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
  className?: string;
}

const ModernPagination: React.FC<ModernPaginationProps> = ({
  currentPage,
  totalPages,
  pageSize,
  totalItems,
  onPageChange,
  className,
}) => {
  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  const handlePrevious = () => {
    if (currentPage > 1) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (currentPage < totalPages) {
      onPageChange(currentPage + 1);
    }
  };

  const handlePageClick = (page: number) => {
    onPageChange(page);
  };

  const renderPageNumbers = () => {
    const pages: (number | string)[] = [];
    const maxVisible = 7;
    const halfVisible = Math.floor(maxVisible / 2);

    let startPage = Math.max(1, currentPage - halfVisible);
    let endPage = Math.min(totalPages, currentPage + halfVisible);

    if (currentPage <= halfVisible) {
      endPage = Math.min(totalPages, maxVisible);
    }

    if (currentPage > totalPages - halfVisible) {
      startPage = Math.max(1, totalPages - maxVisible + 1);
    }

    if (startPage > 1) {
      pages.push(1);
      if (startPage > 2) {
        pages.push('...');
      }
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(i);
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) {
        pages.push('...');
      }
      pages.push(totalPages);
    }

    return pages.map((page, index) => {
      if (page === '...') {
        return (
          <span
            key={`ellipsis-${index}`}
            className="px-3 py-1 text-text-tertiary"
          >
            ...
          </span>
        );
      }

      const pageNumber = page as number;
      const isActive = pageNumber === currentPage;

      return (
        <button
          key={pageNumber}
          onClick={() => handlePageClick(pageNumber)}
          className={clsx(
            'px-3 py-1 rounded-md font-medium text-sm transition-colors duration-150',
            {
              'bg-primary text-white': isActive,
              'bg-transparent text-text-primary hover:bg-gray-100': !isActive,
            }
          )}
        >
          {pageNumber}
        </button>
      );
    });
  };

  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className={clsx('flex items-center justify-between', className)}>
      <div className="text-sm text-text-secondary">
        Showing <span className="font-medium text-text-primary">{startItem}</span> to{' '}
        <span className="font-medium text-text-primary">{endItem}</span> of{' '}
        <span className="font-medium text-text-primary">{totalItems}</span> results
      </div>

      <div className="flex items-center gap-2">
        <ModernButton
          variant="ghost"
          size="sm"
          onClick={handlePrevious}
          disabled={currentPage === 1}
        >
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 19l-7-7 7-7"
            />
          </svg>
          Previous
        </ModernButton>

        <div className="flex items-center gap-1">
          {renderPageNumbers()}
        </div>

        <ModernButton
          variant="ghost"
          size="sm"
          onClick={handleNext}
          disabled={currentPage === totalPages}
        >
          Next
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </ModernButton>
      </div>
    </div>
  );
};

export default ModernPagination;