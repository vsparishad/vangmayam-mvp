import React from 'react';
import { Cog6ToothIcon } from '@heroicons/react/24/outline';

const AdminPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="text-center">
        <Cog6ToothIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h2 className="mt-2 text-lg font-medium text-gray-900">Admin Dashboard</h2>
        <p className="mt-1 text-sm text-gray-500">
          System administration and user management.
        </p>
        <div className="mt-6">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              ⚙️ Admin page implementation in progress. Features include:
              <br />• User management and role assignment
              <br />• System monitoring and analytics
              <br />• Import pipeline management
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPage;
