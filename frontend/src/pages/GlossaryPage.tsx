import React from 'react';
import { BookmarkIcon } from '@heroicons/react/24/outline';

const GlossaryPage: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="text-center">
        <BookmarkIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h2 className="mt-2 text-lg font-medium text-gray-900">Sanskrit Glossary</h2>
        <p className="mt-1 text-sm text-gray-500">
          Comprehensive dictionary with etymology and pronunciation.
        </p>
        <div className="mt-6">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              📚 Glossary page implementation in progress. Features include:
              <br />• Multi-dictionary search and lookup
              <br />• Etymology and pronunciation guides
              <br />• Collaborative dictionary editing
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GlossaryPage;
