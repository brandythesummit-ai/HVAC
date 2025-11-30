import { useState, useEffect } from 'react';
import { Loader2, CheckCircle, XCircle, Clock, Database, Home, TrendingUp, Calendar } from 'lucide-react';
import { jobsApi } from '../../api/jobs';
import { formatRelativeTime } from '../../utils/formatters';

const JobProgress = ({ jobId, onComplete, onError }) => {
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!jobId) return;

    const pollJob = async () => {
      try {
        const response = await jobsApi.getJob(jobId);

        if (!response.success) {
          throw new Error(response.error || 'Failed to fetch job status');
        }

        const jobData = response.data;
        setJob(jobData);

        // Call callbacks
        if (jobData.status === 'completed' && onComplete) {
          onComplete(jobData);
        } else if (jobData.status === 'failed' && onError) {
          onError(jobData);
        }
      } catch (err) {
        setError(err.message);
        if (onError) {
          onError(err);
        }
      }
    };

    // Initial fetch
    pollJob();

    // Poll every 5 seconds for running jobs
    const interval = setInterval(() => {
      if (job?.status === 'running' || job?.status === 'pending') {
        pollJob();
      } else {
        clearInterval(interval);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [jobId, job?.status, onComplete, onError]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-start">
          <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-semibold text-red-800">Error Loading Job</h3>
            <p className="mt-1 text-sm text-red-700">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (job.status) {
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'running':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getStatusBadge = () => {
    switch (job.status) {
      case 'pending':
        return <span className="badge badge-warning">Pending</span>;
      case 'running':
        return <span className="badge badge-info">Running</span>;
      case 'completed':
        return <span className="badge badge-success">Completed</span>;
      case 'failed':
        return <span className="badge badge-error">Failed</span>;
      default:
        return null;
    }
  };

  const progressPercent = job.progress_percent || 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          {getStatusIcon()}
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {job.job_type === 'initial_pull' ? '30-Year Historical Pull' : 'Permit Pull'}
            </h3>
            <p className="text-sm text-gray-500">
              {job.status === 'running' && job.current_year && (
                <>Processing year {job.current_year}</>
              )}
              {job.status === 'completed' && (
                <>Completed {formatRelativeTime(job.completed_at)}</>
              )}
              {job.status === 'pending' && <>Waiting to start...</>}
              {job.status === 'failed' && <>Failed {formatRelativeTime(job.updated_at)}</>}
            </p>
          </div>
        </div>
        {getStatusBadge()}
      </div>

      {/* Progress Bar */}
      {(job.status === 'running' || job.status === 'pending') && (
        <div>
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-600 font-medium">Progress</span>
            <span className="text-gray-900 font-semibold">{progressPercent}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>
      )}

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <Database className="h-4 w-4 text-blue-600 mr-2" />
            <span className="text-xs font-medium text-blue-900">Permits Pulled</span>
          </div>
          <p className="text-2xl font-bold text-blue-900">{job.permits_pulled || 0}</p>
        </div>

        <div className="bg-green-50 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <Home className="h-4 w-4 text-green-600 mr-2" />
            <span className="text-xs font-medium text-green-900">Properties</span>
          </div>
          <p className="text-2xl font-bold text-green-900">{job.properties_created || 0}</p>
        </div>

        <div className="bg-purple-50 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <TrendingUp className="h-4 w-4 text-purple-600 mr-2" />
            <span className="text-xs font-medium text-purple-900">Leads Created</span>
          </div>
          <p className="text-2xl font-bold text-purple-900">{job.leads_created || 0}</p>
        </div>

        {job.estimated_completion_at && job.status === 'running' && (
          <div className="bg-yellow-50 rounded-lg p-4">
            <div className="flex items-center mb-2">
              <Calendar className="h-4 w-4 text-yellow-600 mr-2" />
              <span className="text-xs font-medium text-yellow-900">Est. Complete</span>
            </div>
            <p className="text-sm font-semibold text-yellow-900">
              {formatRelativeTime(job.estimated_completion_at)}
            </p>
          </div>
        )}
      </div>

      {/* Performance Metrics */}
      {job.permits_per_second && job.status === 'running' && (
        <div className="text-sm text-gray-600">
          <span className="font-medium">Speed:</span> {job.permits_per_second.toFixed(1)} permits/sec
        </div>
      )}

      {/* Error Message */}
      {job.status === 'failed' && job.error_message && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm font-medium text-red-800 mb-1">Error Details:</p>
          <p className="text-sm text-red-700">{job.error_message}</p>
        </div>
      )}

      {/* Success Summary */}
      {job.status === 'completed' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start">
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 mr-3" />
            <div>
              <p className="text-sm font-semibold text-green-800 mb-1">Job Completed Successfully!</p>
              <p className="text-sm text-green-700">
                Pulled {job.permits_pulled} permits, created {job.properties_created} properties,
                and generated {job.leads_created} qualified leads.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobProgress;
