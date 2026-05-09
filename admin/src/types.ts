/** API payloads (camelCase matches FastAPI aliases). */

export type AdminOverview = {
  totalUsers: number;
  totalCompletedRuns: number;
  openRuns: number;
  runsLast24h: number;
  newUsers7d: number;
  dormantUsers14d: number;
  runsByDay: { date: string; count: number }[];
};

export type AdminUserRow = {
  id: number;
  name: string;
  username: string | null;
  photoUrl: string | null;
  language: string | null;
  bestScore: number;
  totalCoins: number;
  runsPlayed: number;
  createdAt: string;
  updatedAt: string;
};

export type AdminUsersPage = {
  total: number;
  page: number;
  pageSize: number;
  items: AdminUserRow[];
};

export type AdminRunRow = {
  id: string;
  score: number;
  coins: number;
  durationMs: number;
  nearMisses: number;
  startedAt: string;
  endedAt: string | null;
};

export type AdminUserDetail = {
  user: AdminUserRow;
  runs: AdminRunRow[];
  runsOpenInSample: number;
  runsCompletedInSample: number;
};

export type AdminOutboundResult = {
  sent: number;
  failed: number;
  errors: string[];
};

export type AdminMessageLogRow = {
  id: number;
  createdAt: string;
  scope: string;
  recipientCount: number;
  successCount: number;
  failCount: number;
  recipientUserId: number | null;
  textPreview: string;
};

export type AdminInsight = {
  title: string;
  count: number;
  sample: {
    id: number;
    name: string;
    username: string | null;
    best_score: number;
    updated_at: string | null;
  }[];
};

export type AdminLiveSession = {
  userId: number;
  name: string;
  username: string | null;
  runId: string;
  startedAt: string;
  presumedInGame: boolean;
};

export type AdminLiveSessions = {
  thresholdMinutes: number;
  totalReturned: number;
  caveat: string;
  items: AdminLiveSession[];
};
