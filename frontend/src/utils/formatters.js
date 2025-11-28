import { format, formatDistanceToNow, parseISO } from 'date-fns';

export const formatDate = (date, formatStr = 'MMM d, yyyy') => {
  if (!date) return '-';
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return format(dateObj, formatStr);
  } catch (error) {
    return '-';
  }
};

export const formatDateTime = (date) => {
  return formatDate(date, 'MMM d, yyyy h:mm a');
};

export const formatRelativeTime = (date) => {
  if (!date) return '-';
  try {
    const dateObj = typeof date === 'string' ? parseISO(date) : date;
    return formatDistanceToNow(dateObj, { addSuffix: true });
  } catch (error) {
    return '-';
  }
};

export const formatCurrency = (value) => {
  if (value == null) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
};

export const formatNumber = (value) => {
  if (value == null) return '-';
  return new Intl.NumberFormat('en-US').format(value);
};

export const maskApiKey = (key) => {
  if (!key) return '';
  if (key.length <= 8) return '•'.repeat(key.length);
  return key.slice(0, 4) + '•'.repeat(key.length - 8) + key.slice(-4);
};
