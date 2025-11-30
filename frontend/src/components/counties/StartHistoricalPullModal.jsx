import { useState } from 'react';
import { X, Database, AlertCircle, CheckCircle } from 'lucide-react';
import { jobsApi } from '../../api/jobs';
import JobProgress from '../jobs/JobProgress';

const StartHistoricalPullModal = ({ county, onClose }) => {
  const [years, setYears] = useState(30);
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [jobCompleted, setJobCompleted] = useState(false);

  const handleStart = async () => {
    setError(null);
    setIsStarting(true);

    try {
      const response = await jobsApi.createInitialPull(county.id, years);

      if (!response.success) {
        throw new Error(response.error || 'Failed to start job');
      }

      setJobId(response.data.job_id);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsStarting(false);
    }
  };

  const handleJobComplete = (job) => {
    setJobCompleted(true);
  };

  const handleJobError = (err) => {
    setError(err.error_message || err.message || 'Job failed');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900 bg-opacity-50 overflow-y-auto">
      <div className="relative w-full max-w-4xl bg-white rounded-xl shadow-2xl animate-slide-in my-8">
        {/* Header */}
        <div className="px-6 py-5 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
                <Database className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  30-Year Historical Pull
                </h2>
                <p className="text-sm text-gray-500 mt-0.5">
                  {county.name} ({county.county_code})
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-500 transition-colors"
              disabled={jobId && !jobCompleted}
            >
              <X className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="px-6 py-6">
          {!jobId ? (
            /* Configuration Form */
            <div className="space-y-6">
              {/* Information */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start">
                  <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5 mr-3" />
                  <div>
                    <h3 className="text-sm font-semibold text-blue-900 mb-1">
                      About Historical Pulls
                    </h3>
                    <p className="text-sm text-blue-800">
                      This will pull all HVAC permits from the past {years} years and automatically:
                    </p>
                    <ul className="mt-2 text-sm text-blue-800 list-disc list-inside space-y-1">
                      <li>Group permits by property address</li>
                      <li>Track most recent HVAC installation per property</li>
                      <li>Calculate lead scores (HOT/WARM/COOL/COLD)</li>
                      <li>Create qualified leads (HVAC 5+ years old)</li>
                    </ul>
                    <p className="mt-3 text-sm text-blue-800 font-medium">
                      This may take several hours depending on permit volume. You can close this
                      window and the job will continue in the background.
                    </p>
                  </div>
                </div>
              </div>

              {/* Years Selection */}
              <div>
                <label htmlFor="years" className="block text-sm font-medium text-gray-700 mb-2">
                  Years to Pull
                </label>
                <select
                  id="years"
                  value={years}
                  onChange={(e) => setYears(parseInt(e.target.value))}
                  className="input-field"
                  disabled={isStarting}
                >
                  <option value={1}>Last 1 year</option>
                  <option value={5}>Last 5 years</option>
                  <option value={10}>Last 10 years</option>
                  <option value={20}>Last 20 years</option>
                  <option value={30}>Last 30 years (recommended)</option>
                </select>
                <p className="mt-2 text-sm text-gray-500">
                  Pulling more years finds older HVAC systems = better leads
                </p>
              </div>

              {/* Error Message */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start">
                    <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 mr-3" />
                    <div>
                      <h3 className="text-sm font-semibold text-red-800 mb-1">Error</h3>
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={onClose}
                  className="btn-secondary"
                  disabled={isStarting}
                >
                  Cancel
                </button>
                <button
                  onClick={handleStart}
                  disabled={isStarting}
                  className="btn-primary"
                >
                  {isStarting ? (
                    <>Starting Job...</>
                  ) : (
                    <>Start {years}-Year Pull</>
                  )}
                </button>
              </div>
            </div>
          ) : (
            /* Job Progress */
            <div className="space-y-6">
              <JobProgress
                jobId={jobId}
                onComplete={handleJobComplete}
                onError={handleJobError}
              />

              {/* Close Button (after job starts) */}
              {jobCompleted && (
                <div className="flex justify-end pt-4 border-t border-gray-200">
                  <button onClick={onClose} className="btn-primary">
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Done
                  </button>
                </div>
              )}

              {!jobCompleted && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <p className="text-sm text-yellow-800">
                    You can close this window. The job will continue running in the background
                    and you can check progress from the Counties page.
                  </p>
                  <div className="flex justify-end mt-3">
                    <button onClick={onClose} className="btn-secondary text-sm">
                      Close and Continue in Background
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StartHistoricalPullModal;
