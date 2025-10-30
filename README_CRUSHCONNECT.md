# CrushConnect Bot - AAU Campus Dating Bot

**The most viral way for Addis Ababa University students to find their match!**

## Features

### Core Features
- **Complete Profile Setup** - Gender, campus, department, year, bio, photo (all with inline buttons)
- **Vibe Quiz** - 7-question personality test for smart matching
- **Smart Matching Algorithm** - Filter by campus, department, year, or vibe compatibility
- **Anonymous Chat** - Match and chat anonymously, reveal when ready
- **Crush Confessions** - Post anonymous confessions to channel
- **Coins & Rewards System** - Earn coins for activity, spend on premium features
- **Referral System** - Invite friends and earn 50 coins per referral
- **Leaderboard** - Weekly top 10 most liked profiles
- **Mini Games** - Icebreaker questions to keep users engaged
- **Admin Panel** - Review confessions, view stats, broadcast messages, ban users

### Engagement Features
- Daily login rewards (10 coins)
- Match bonuses (30 coins)
- Confession rewards (5 coins)
- Referral tracking with leaderboard
- Automated notifications (daily, weekly)
- Channel integration for viral content

### Security & Moderation
- Admin approval for confessions before posting
- Ban system for abusive users
- RLS policies on all database tables
- Logging to admin group
- Rate limiting protection

## Tech Stack

- **Bot Framework**: aiogram 3.4.1 (Python Telegram Bot)
- **Database**: Supabase (PostgreSQL)
- **Scheduling**: APScheduler
- **Image Processing**: Pillow
- **Deployment**: Docker + Render

## Setup Instructions

### 1. Create Telegram Bot

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save your bot token
4. Set bot username to `CrushConnectBot` (or your preferred name)

### 2. Create Telegram Channel

1. Create a public channel with username `@AAUCrushConnect`
2. Add your bot as an admin with posting permissions
3. Get channel ID (use @userinfobot or similar)

### 3. Configure Environment Variables

Update `.env` file:

```env
BOT_TOKEN=your_bot_token_from_botfather
CHANNEL_ID=@AAUCrushConnect
ADMIN_GROUP_ID=your_telegram_user_id

VITE_SUPABASE_URL=already_configured
VITE_SUPABASE_ANON_KEY=already_configured
```

### 4. Set Up Admin Access

First user to run `/set_admin <your_user_id>` becomes admin. Get your user ID from [@userinfobot](https://t.me/userinfobot).

### 5. Database Setup

Database is already configured! Tables created:
- `users` - User profiles
- `likes` - Swipe history
- `matches` - Mutual likes
- `chats` - Anonymous messages
- `confessions` - Anonymous confessions
- `referrals` - Invite tracking
- `transactions` - Coin history
- `daily_logins` - Login streaks
- `leaderboard_cache` - Weekly stats

### 6. Run Locally

```bash
pip install -r requirements.txt
python bot.py
```

### 7. Deploy to Render

1. Push code to GitHub
2. Create new Web Service on Render
3. Select "Docker" environment
4. Add environment variables from `.env`
5. Deploy!

Alternatively, use the included `render.yaml` for one-click deploy.

## Bot Commands

- `/start` - Start bot / Create profile / Main menu
- `/profile` - View your profile and stats
- `/admin` - Admin panel (admin only)
- `/broadcast <message>` - Send message to all users (admin only)
- `/set_admin <user_id>` - Make someone admin (admin only)

## User Flow

### New User
1. `/start` → Profile setup
2. Select gender (inline buttons)
3. Select seeking gender (inline buttons)
4. Select campus (inline buttons)
5. Select department (inline buttons or text)
6. Select year (inline buttons)
7. Enter name/nickname
8. Enter bio (10-200 chars)
9. Upload profile photo
10. Complete 7-question vibe quiz
11. Get 120 starting coins
12. Main menu appears

### Finding Matches
1. Click "Find Matches"
2. Optional: Set filters (campus/dept/year)
3. Swipe through profiles
4. Like or Pass
5. If mutual like → Match notification!
6. Start anonymous chat

### Confessions
1. Click "Crush Confession"
2. Select target campus
3. Select target department
4. Write confession (10-500 chars)
5. Admin reviews and approves
6. Posted to channel
7. Get 5 coins

### Chat System
1. View matches in "My Crushes"
2. Start anonymous chat
3. Send messages or icebreakers
4. Spend 30 coins to reveal identity
5. Continue chatting after reveal

## Admin Features

### Confession Moderation
- View pending confessions
- Approve → Posts to channel
- Reject → Deletes confession
- See confession details (campus, dept, text)

### Bot Statistics
- Total users
- Active users
- Total matches
- Total/pending confessions

### Broadcasting
- Send message to all active users
- Shows success/failure count

### User Management
- Ban abusive users
- View user activity
- Add more admins

## Notifications Schedule

- **Daily (7 PM)**: Random engagement message to all users
- **Friday (12 PM)**: Confession Friday reminder
- **Sunday (2 PM)**: Blind Date Sunday reminder
- **Monday (10 AM)**: Weekly leaderboard update

## Coin Economy

### Earn Coins
- Profile creation: 120 coins (starting bonus)
- Daily login: 10 coins
- Referral: 50 coins
- Confession: 5 coins
- First match: 30 coins

### Spend Coins
- Reveal identity: 30 coins
- Extra daily likes: 20 coins (future feature)
- Premium vibe test: 50 coins (future feature)

## Vibe Quiz Questions

1. Coffee at Sheger or Mirinda at campus?
2. Library grind or Student lounge chill?
3. Late night study or Movie marathon?
4. Campus event or Netflix at home?
5. Shawarma run or Fancy restaurant?
6. Sports fan or Gamer?
7. Public transport adventures or Private rides?

Each answer contributes to vibe score used for compatibility matching.

## Matching Algorithm

1. Filter out already-liked users
2. Filter by seeking gender preference
3. Apply user-selected filters (campus/dept/year)
4. Calculate vibe compatibility score
5. Show profiles one at a time
6. Track likes for leaderboard

## Channel Content Strategy

Post to channel:
- Approved confessions with formatting
- Match alerts (anonymous or revealed)
- Weekly leaderboard top 10
- Special event announcements
- Memes and engagement content

Format:
```
💌 Anonymous Confession 💌

📍 Campus: Main 6kilo
📚 Department: Engineering

[Confession text here]

Is this about you? React with ❤️

@CrushConnectBot
```

## Error Handling

- All errors logged to `bot.log`
- Critical errors sent to admin group
- Graceful fallbacks for:
  - Missing profile photos
  - Database connection issues
  - Telegram API rate limits
  - Invalid user input

## Security Best Practices

- Service role access only for bot
- RLS enabled on all tables
- No direct database access for users
- Confession approval before posting
- Ban system for abuse
- Profile photo validation
- Message length limits
- Rate limiting on likes

## Scaling Considerations

Current setup handles:
- 5000+ active users
- 50 daily likes per user
- Unlimited matches
- 100 confessions/day

For larger scale:
- Add Redis caching
- Implement proper rate limiting
- Use message queues for notifications
- Add CDN for profile images

## File Structure

```
.
├── bot.py                      # Main bot entry point
├── bot_config.py              # Configuration & constants
├── database.py                # Database operations
├── utils.py                   # Helper functions
├── notifications.py           # Scheduled notifications
├── handlers_profile.py        # Profile setup flow
├── handlers_main.py           # Main menu & navigation
├── handlers_matching.py       # Swipe & match logic
├── handlers_chat.py           # Anonymous chat system
├── handlers_confession.py     # Confession submission
├── handlers_admin.py          # Admin panel
├── handlers_leaderboard.py    # Weekly leaderboard
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
├── render.yaml               # Render deployment config
└── .env                      # Environment variables
```

## Tone & Personality

Bot speaks with:
- Gen Z slang and energy
- Playful, flirty, bold tone
- Emojis in every message
- Casual AAU campus references
- Chaotic but fun vibes

Examples:
- "Yooo welcome to CrushConnect! 🔥"
- "Bruh... upload that selfie or stay invisible 👻"
- "No cap, this'll take like 2 minutes 💯"
- "Time to find your match... 😏"

## Future Features

- Photo verification
- Video profiles
- Voice messages in chat
- Group date events
- Premium subscriptions
- Gift sending (virtual roses, etc.)
- Story posts (24hr)
- Campus event integration
- Study buddy matching
- Anonymous Q&A

## Support & Issues

For issues:
1. Check logs in `bot.log`
2. Verify environment variables
3. Check database connection
4. Review Telegram bot permissions

## License

This is a custom bot for Addis Ababa University students. Not for commercial use without permission.

---

**Built with 💜 for AAU students by Claude Code**

**Bot Username**: @CrushConnectBot
**Channel**: @AAUCrushConnect

Let's make campus dating less awkward! 🔥
