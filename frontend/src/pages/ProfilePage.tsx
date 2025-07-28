import React from 'react';
import { UserIcon } from '@heroicons/react/24/outline';

const ProfilePage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="text-center">
        <UserIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h2 className="mt-2 text-lg font-medium text-gray-900">User Profile</h2>
        <p className="mt-1 text-sm text-gray-500">
          Manage your account settings and preferences.
        </p>
        <div className="mt-6">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              👤 Profile page implementation in progress. Features include:
              <br />• User information and settings
              <br />• Activity history and contributions
              <br />• Notification preferences
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
