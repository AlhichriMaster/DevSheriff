import { useEffect, useState } from 'react';
import { subscribeToRecentReviews } from '../lib/firestore';

export default function RealtimeIndicator() {
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const unsub = subscribeToRecentReviews(() => {
      setConnected(true);
    });

    return unsub;
  }, []);

  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <span
        className={`h-2 w-2 rounded-full ${
          connected
            ? 'bg-green-400 animate-pulse shadow-[0_0_6px_2px_rgba(74,222,128,0.4)]'
            : 'bg-gray-600'
        }`}
      />
      {connected ? 'Live' : 'Connecting...'}
    </div>
  );
}
