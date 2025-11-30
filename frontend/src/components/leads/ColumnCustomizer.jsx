import { useState, useEffect } from 'react';
import { X, Eye, EyeOff, RotateCcw } from 'lucide-react';

/**
 * ColumnCustomizer - Modal for customizing visible columns in LeadsTable
 * Allows users to show/hide columns and persists preferences in localStorage
 */
const ColumnCustomizer = ({ isOpen, onClose, columns, visibleColumns, onSaveColumns }) => {
  const [localVisibleColumns, setLocalVisibleColumns] = useState(visibleColumns);

  // Update local state when visibleColumns prop changes
  useEffect(() => {
    setLocalVisibleColumns(visibleColumns);
  }, [visibleColumns]);

  const toggleColumn = (columnId) => {
    setLocalVisibleColumns(prev => {
      if (prev.includes(columnId)) {
        return prev.filter(id => id !== columnId);
      } else {
        return [...prev, columnId];
      }
    });
  };

  const handleSave = () => {
    onSaveColumns(localVisibleColumns);
    onClose();
  };

  const handleReset = () => {
    const defaultColumns = columns.filter(col => col.defaultVisible).map(col => col.id);
    setLocalVisibleColumns(defaultColumns);
  };

  const handleCancel = () => {
    setLocalVisibleColumns(visibleColumns); // Reset to original
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={handleCancel}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white rounded-xl shadow-2xl max-w-2xl w-full animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Customize Columns</h2>
              <p className="text-sm text-gray-600 mt-1">
                Select which columns to display in the table
              </p>
            </div>
            <button
              onClick={handleCancel}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Column List */}
          <div className="px-6 py-4 max-h-[60vh] overflow-y-auto custom-scrollbar">
            <div className="space-y-2">
              {columns.map((column) => {
                const isVisible = localVisibleColumns.includes(column.id);
                const isRequired = column.required;

                return (
                  <div
                    key={column.id}
                    className={`flex items-center justify-between p-4 rounded-lg border transition-all ${
                      isVisible
                        ? 'bg-blue-50 border-blue-200'
                        : 'bg-gray-50 border-gray-200'
                    } ${isRequired ? 'opacity-50' : ''}`}
                  >
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => !isRequired && toggleColumn(column.id)}
                        disabled={isRequired}
                        className={`flex items-center justify-center w-10 h-10 rounded-lg transition-colors ${
                          isRequired
                            ? 'bg-gray-300 cursor-not-allowed'
                            : isVisible
                            ? 'bg-blue-600 hover:bg-blue-700'
                            : 'bg-gray-300 hover:bg-gray-400'
                        }`}
                      >
                        {isVisible ? (
                          <Eye className="h-5 w-5 text-white" />
                        ) : (
                          <EyeOff className="h-5 w-5 text-gray-600" />
                        )}
                      </button>
                      <div>
                        <p className="font-semibold text-gray-900">
                          {column.label}
                          {isRequired && (
                            <span className="ml-2 text-xs text-gray-500">(Required)</span>
                          )}
                        </p>
                        {column.description && (
                          <p className="text-sm text-gray-600">{column.description}</p>
                        )}
                      </div>
                    </div>

                    <div className="text-sm font-medium">
                      {isVisible ? (
                        <span className="text-blue-600">Visible</span>
                      ) : (
                        <span className="text-gray-500">Hidden</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
            <button
              onClick={handleReset}
              className="btn-secondary flex items-center gap-2"
            >
              <RotateCcw className="h-4 w-4" />
              Reset to Default
            </button>

            <div className="flex gap-3">
              <button onClick={handleCancel} className="btn-secondary">
                Cancel
              </button>
              <button onClick={handleSave} className="btn-primary">
                Save Changes
              </button>
            </div>
          </div>

          {/* Column Count Info */}
          <div className="px-6 pb-4">
            <p className="text-sm text-gray-600 text-center">
              {localVisibleColumns.length} of {columns.length} columns visible
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ColumnCustomizer;
