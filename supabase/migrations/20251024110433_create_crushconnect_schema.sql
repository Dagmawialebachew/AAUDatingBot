/*
  # CrushConnect Database Schema

  ## Overview
  Complete database schema for the CrushConnect Telegram bot serving Addis Ababa University students.
  Supports profiles, matching, anonymous chat, confessions, coins/rewards, referrals, and admin functions.

  ## New Tables
  
  ### 1. `users`
  Core user profiles with all required fields
  - `id` (bigint, primary key) - Telegram user ID
  - `username` (text) - Telegram username
  - `name` (text) - Display name/nickname
  - `gender` (text) - Male/Female/Other
  - `seeking_gender` (text) - Preferred match gender
  - `campus` (text) - AAU campus location
  - `department` (text) - Academic department
  - `year` (text) - Year of study
  - `bio` (text) - Profile description
  - `profile_pic_url` (text) - Profile picture URL
  - `vibe_score` (jsonb) - Personality quiz results
  - `coins` (integer) - In-app currency balance
  - `is_active` (boolean) - Account status
  - `is_banned` (boolean) - Ban status
  - `created_at` (timestamptz) - Registration date
  - `last_active` (timestamptz) - Last activity timestamp
  
  ### 2. `likes`
  Tracks who liked whom
  - `id` (uuid, primary key)
  - `liker_id` (bigint) - User who liked
  - `liked_id` (bigint) - User who was liked
  - `created_at` (timestamptz)
  
  ### 3. `matches`
  Mutual likes become matches
  - `id` (uuid, primary key)
  - `user1_id` (bigint)
  - `user2_id` (bigint)
  - `chat_active` (boolean) - Chat enabled status
  - `revealed` (boolean) - Identity revealed
  - `created_at` (timestamptz)
  
  ### 4. `chats`
  Anonymous chat messages
  - `id` (uuid, primary key)
  - `match_id` (uuid) - Associated match
  - `sender_id` (bigint)
  - `message` (text)
  - `created_at` (timestamptz)
  
  ### 5. `confessions`
  Anonymous confessions to channel
  - `id` (uuid, primary key)
  - `sender_id` (bigint)
  - `target_campus` (text)
  - `target_department` (text)
  - `confession_text` (text)
  - `status` (text) - pending/approved/rejected
  - `channel_message_id` (bigint)
  - `created_at` (timestamptz)
  
  ### 6. `referrals`
  User referral tracking
  - `id` (uuid, primary key)
  - `referrer_id` (bigint) - User who referred
  - `referred_id` (bigint) - New user referred
  - `coins_awarded` (integer)
  - `created_at` (timestamptz)
  
  ### 7. `transactions`
  Coin transaction history
  - `id` (uuid, primary key)
  - `user_id` (bigint)
  - `amount` (integer) - Positive for earn, negative for spend
  - `type` (text) - daily_login/referral/purchase/etc
  - `description` (text)
  - `created_at` (timestamptz)
  
  ### 8. `daily_logins`
  Track daily login streaks
  - `id` (uuid, primary key)
  - `user_id` (bigint)
  - `login_date` (date)
  - `created_at` (timestamptz)
  
  ### 9. `leaderboard_cache`
  Cached leaderboard data
  - `id` (uuid, primary key)
  - `user_id` (bigint)
  - `likes_received` (integer)
  - `matches_count` (integer)
  - `week_start` (date)
  - `updated_at` (timestamptz)
  
  ## Security
  - RLS enabled on all tables
  - Service role access for bot operations
  - Policies restrict direct user access
*/

-- Users table
CREATE TABLE IF NOT EXISTS users (
  id bigint PRIMARY KEY,
  username text,
  name text NOT NULL,
  gender text NOT NULL CHECK (gender IN ('Male', 'Female', 'Other')),
  seeking_gender text NOT NULL CHECK (seeking_gender IN ('Male', 'Female', 'Any')),
  campus text NOT NULL,
  department text NOT NULL,
  year text NOT NULL,
  bio text NOT NULL,
  profile_pic_url text NOT NULL,
  vibe_score jsonb DEFAULT '{}'::jsonb,
  coins integer DEFAULT 100,
  is_active boolean DEFAULT true,
  is_banned boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  last_active timestamptz DEFAULT now()
);

-- Likes table
CREATE TABLE IF NOT EXISTS likes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  liker_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  liked_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),
  UNIQUE(liker_id, liked_id)
);

-- Matches table
CREATE TABLE IF NOT EXISTS matches (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user1_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  user2_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  chat_active boolean DEFAULT true,
  revealed boolean DEFAULT false,
  created_at timestamptz DEFAULT now(),
  CHECK (user1_id < user2_id)
);

-- Chats table
CREATE TABLE IF NOT EXISTS chats (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id uuid NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  sender_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  message text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Confessions table
CREATE TABLE IF NOT EXISTS confessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sender_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  target_campus text,
  target_department text,
  confession_text text NOT NULL,
  status text DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  channel_message_id bigint,
  created_at timestamptz DEFAULT now()
);

-- Referrals table
CREATE TABLE IF NOT EXISTS referrals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  referrer_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  referred_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  coins_awarded integer DEFAULT 50,
  created_at timestamptz DEFAULT now(),
  UNIQUE(referred_id)
);

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  amount integer NOT NULL,
  type text NOT NULL,
  description text NOT NULL,
  created_at timestamptz DEFAULT now()
);

-- Daily logins table
CREATE TABLE IF NOT EXISTS daily_logins (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  login_date date NOT NULL,
  created_at timestamptz DEFAULT now(),
  UNIQUE(user_id, login_date)
);

-- Leaderboard cache table
CREATE TABLE IF NOT EXISTS leaderboard_cache (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  likes_received integer DEFAULT 0,
  matches_count integer DEFAULT 0,
  week_start date NOT NULL,
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, week_start)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_likes_liker ON likes(liker_id);
CREATE INDEX IF NOT EXISTS idx_likes_liked ON likes(liked_id);
CREATE INDEX IF NOT EXISTS idx_matches_user1 ON matches(user1_id);
CREATE INDEX IF NOT EXISTS idx_matches_user2 ON matches(user2_id);
CREATE INDEX IF NOT EXISTS idx_chats_match ON chats(match_id);
CREATE INDEX IF NOT EXISTS idx_chats_created ON chats(created_at);
CREATE INDEX IF NOT EXISTS idx_confessions_status ON confessions(status);
CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_logins_user ON daily_logins(user_id);
CREATE INDEX IF NOT EXISTS idx_leaderboard_week ON leaderboard_cache(week_start);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active, is_banned);

-- Enable Row Level Security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE likes ENABLE ROW LEVEL SECURITY;
ALTER TABLE matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE confessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE referrals ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_logins ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaderboard_cache ENABLE ROW LEVEL SECURITY;

-- RLS Policies (restrictive - bot uses service role)
CREATE POLICY "Service role full access users"
  ON users FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access likes"
  ON likes FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access matches"
  ON matches FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access chats"
  ON chats FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access confessions"
  ON confessions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access referrals"
  ON referrals FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access transactions"
  ON transactions FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access daily_logins"
  ON daily_logins FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

CREATE POLICY "Service role full access leaderboard"
  ON leaderboard_cache FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);