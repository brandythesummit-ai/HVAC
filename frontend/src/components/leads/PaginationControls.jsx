import { ChevronLeft, ChevronRight } from 'lucide-react';

/**
 * PaginationControls - UI controls for pagination
 * Supports page size selection (50/100/150/200) and navigation
 */
const PaginationControls = ({ total, limit, offset, onLimitChange, onPageChange }) => {
  const currentPage = Math.floor(offset / limit) + 1;
  const totalPages = Math.ceil(total / limit);
  const startItem = total === 0 ? 0 : offset + 1;
  const endItem = Math.min(offset + limit, total);

  const handlePrevious = () => {
    if (offset > 0) {
      onPageChange(Math.max(0, offset - limit));
    }
  };

  const handleNext = () => {
    if (offset + limit < total) {
      onPageChange(offset + limit);
    }
  };

  const handlePageSizeChange = (e) => {
    const newLimit = parseInt(e.target.value);
    onLimitChange(newLimit);
    // Reset to first page when changing page size
    onPageChange(0);
  };

  if (total === 0) {
    return null;
  }

  return (
    <div className="card animate-fade-in">
      <div className="card-body">
        <div className="flex items-center justify-between">
          {/* Results info */}
          <div className="flex items-center gap-4">
            <p className="text-sm text-gray-700">
              Showing <span className="font-medium">{startItem}</span> to{' '}
              <span className="font-medium">{endItem}</span> of{' '}
              <span className="font-medium">{total}</span> results
            </p>

            {/* Page size selector */}
            <div className="flex items-center gap-2">
              <label htmlFor="pageSize" className="text-sm text-gray-700">
                Per page:
              </label>
              <select
                id="pageSize"
                value={limit}
                onChange={handlePageSizeChange}
                className="input-field w-24"
              >
                <option value="50">50</option>
                <option value="100">100</option>
                <option value="150">150</option>
                <option value="200">200</option>
              </select>
            </div>
          </div>

          {/* Navigation controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevious}
              disabled={offset === 0}
              className="btn-secondary flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>

            <span className="text-sm text-gray-700 px-3">
              Page <span className="font-medium">{currentPage}</span> of{' '}
              <span className="font-medium">{totalPages}</span>
            </span>

            <button
              onClick={handleNext}
              disabled={offset + limit >= total}
              className="btn-secondary flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PaginationControls;
