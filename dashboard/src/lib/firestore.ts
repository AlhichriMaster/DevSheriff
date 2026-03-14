import { initializeApp } from 'firebase/app';
import {
  getFirestore,
  collection,
  onSnapshot,
  query,
  orderBy,
  limit,
  doc,
  getDoc,
  getDocs,
  Unsubscribe,
} from 'firebase/firestore';

const app = initializeApp({
  projectId: import.meta.env.VITE_FIRESTORE_PROJECT_ID || 'devsheriff-dev',
});

const db = getFirestore(app);

export interface Review {
  id: string;
  repo: string;
  repo_id: string;
  pr_number: number;
  pr_title: string;
  pr_url: string;
  sha: string;
  author: string;
  status: string;
  finding_count: number;
  critical_count: number;
  high_count: number;
  created_at: { seconds: number; nanoseconds: number };
}

export interface Finding {
  file: string;
  line: number;
  severity: string;
  category: string;
  title: string;
  body: string;
  suggestion: string;
  owasp_category?: string;
  diff_position?: number;
  cve_ids?: string[];
}

export interface ReviewWithFindings extends Review {
  findings: Finding[];
}

export function subscribeToRecentReviews(
  callback: (reviews: Review[]) => void
): Unsubscribe {
  const q = query(
    collection(db, 'reviews'),
    orderBy('created_at', 'desc'),
    limit(50)
  );

  return onSnapshot(q, (snapshot) => {
    const reviews = snapshot.docs.map((doc) => ({
      id: doc.id,
      ...doc.data(),
    })) as Review[];
    callback(reviews);
  });
}

export async function fetchReviewWithFindings(
  reviewId: string
): Promise<ReviewWithFindings | null> {
  const reviewRef = doc(db, 'reviews', reviewId);
  const reviewDoc = await getDoc(reviewRef);

  if (!reviewDoc.exists()) return null;

  const findingsSnap = await getDocs(collection(reviewRef, 'findings'));
  const findings = findingsSnap.docs.map((d) => d.data() as Finding);

  return {
    id: reviewDoc.id,
    ...(reviewDoc.data() as Omit<Review, 'id'>),
    findings,
  };
}

export function formatTimestamp(ts: { seconds: number; nanoseconds: number }): string {
  if (!ts) return 'Unknown';
  return new Date(ts.seconds * 1000).toLocaleString();
}
