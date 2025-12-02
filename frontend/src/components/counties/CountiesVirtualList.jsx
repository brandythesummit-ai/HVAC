import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import CountyCompactRow from './CountyCompactRow';

export default function CountiesVirtualList({ counties, onCountySelect, selectedCountyId }) {
  const parentRef = useRef(null);

  const virtualizer = useVirtualizer({
    count: counties.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60, // Fixed 60px row height
    overscan: 5, // Render 5 extra rows above/below viewport
  });

  return (
    <div
      ref={parentRef}
      className="bg-gray-50 overflow-y-auto"
      style={{ height: `${Math.min(counties.length * 60, 400)}px` }} // Max 400px tall
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const county = counties[virtualRow.index];
          return (
            <div
              key={county.id}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
            >
              <CountyCompactRow
                county={county}
                onClick={() => onCountySelect(county)}
                isSelected={county.id === selectedCountyId}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
