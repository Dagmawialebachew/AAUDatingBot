# CrushConnect - Project Structure

## File Organization

```
crushconnect-bot/
├── Core Bot Files
│   ├── bot.py                      # Main bot entry point, starts polling
│   ├── bot_config.py              # All configuration constants
│   ├── database.py                # Database operations wrapper
│   ├── utils.py                   # Helper functions
│   └── notifications.py           # Scheduled notification system
│
├── Handler Modules (Routers)
│   ├── handlers_profile.py        # Profile setup & editing
│   ├── handlers_main.py           # Main menu & navigation
│   ├── handlers_matching.py       # Swipe, match, filters
│   ├── handlers_chat.py           # Anonymous chat system
│   ├── handlers_confession.py     # Confession submission
│   ├── handlers_admin.py          # Admin panel & moderation
│   └── handlers_leaderboard.py    # Weekly leaderboard
│
├── Deployment
│   ├── Dockerfile                 # Docker container config
│   ├── .dockerignore             # Docker ignore patterns
│   ├── render.yaml               # Render.com deployment
│   └── requirements.txt          # Python dependencies
│
├── Configuration
│   ├── .env                      # Environment variables
│   └── .gitignore               # Git ignore patterns
│
└── Documentation
    ├── README_CRUSHCONNECT.md    # Full documentation
    ├── QUICKSTART.md            # Quick setup guide
    ├── PROJECT_STRUCTURE.md     # This file
    └── verify_setup.py          # Setup verification script
```

## Module Breakdown

### bot.py
**Main entry point**
- Initializes bot and dispatcher
- Registers all routers
- Sets up bot commands
- Handles startup/shutdown
- Starts polling

Key functions:
- `main()` - Async main function
- `setup_bot_commands()` - Register bot commands
- `on_startup()` - Startup tasks
- `on_shutdown()` - Cleanup tasks

### bot_config.py
**Configuration management**
- Environment variable loading
- Campus/department/year lists
- Vibe quiz questions
- Coin economy settings
- Channel/admin configuration

Constants:
- `AAU_CAMPUSES` - List of AAU campuses
- `AAU_DEPARTMENTS` - Department options
- `VIBE_QUESTIONS` - Personality quiz
- `COIN_REWARDS` - Earning rates
- `COIN_COSTS` - Spending rates

### database.py
**Database abstraction layer**
- Supabase client initialization
- User CRUD operations
- Match/like operations
- Chat message storage
- Confession management
- Coin transactions
- Leaderboard queries

Key methods:
- `get_user()` - Fetch user profile
- `create_user()` - Register new user
- `add_like()` - Record like, check for match
- `get_matches_for_user()` - Find compatible profiles
- `save_chat_message()` - Store message
- `add_coins()` / `spend_coins()` - Coin operations

### utils.py
**Helper functions**
- Image processing (download, resize)
- Vibe compatibility calculation
- Profile text formatting
- Referral link generation
- Bio validation
- Icebreaker questions

Key functions:
- `download_and_resize_image()` - Process profile photos
- `calculate_vibe_compatibility()` - Match scoring
- `format_profile_text()` - Display profile
- `get_random_icebreaker()` - Chat starters

### notifications.py
**Scheduled engagement**
- APScheduler integration
- Daily notification system
- Weekly special events
- Channel content posting
- Leaderboard updates

Scheduled jobs:
- Daily 7 PM: Engagement reminder
- Friday 12 PM: Confession Friday
- Sunday 2 PM: Blind Date Sunday
- Monday 10 AM: Leaderboard post

### handlers_profile.py
**Profile management**
- Registration flow with FSM
- Inline button keyboards
- Vibe quiz implementation
- Profile editing
- Photo upload handling

States:
- `ProfileSetup.gender`
- `ProfileSetup.seeking_gender`
- `ProfileSetup.campus`
- `ProfileSetup.department`
- `ProfileSetup.year`
- `ProfileSetup.name`
- `ProfileSetup.bio`
- `ProfileSetup.photo`
- `ProfileSetup.vibe_quiz`

### handlers_main.py
**Main navigation**
- Main menu display
- Coins & shop info
- Referral system
- Mini games
- My crushes list

Callbacks:
- `main_menu` - Show main menu
- `coins_shop` - Display coin info
- `referral` - Invite friends
- `mini_games` - Icebreakers
- `my_crushes` - View matches

### handlers_matching.py
**Swipe & match logic**
- Profile browsing
- Like/pass actions
- Match detection
- Filter system
- Candidate selection

States:
- `MatchingState.browsing`
- `MatchingState.filter_selection`

Functions:
- `start_matching()` - Initialize swipe session
- `show_candidate()` - Display profile
- `handle_like()` - Process like, check match
- `handle_pass()` - Skip profile
- `filter_matches()` - Apply filters

### handlers_chat.py
**Anonymous messaging**
- Match-based chat
- Anonymous mode
- Identity reveal (30 coins)
- Icebreaker sending
- Message relay

States:
- `ChatState.in_chat`

Global:
- `active_chats` - Track active sessions

Functions:
- `start_chat()` - Open chat with match
- `send_icebreaker()` - Send random question
- `reveal_identity()` - Spend coins to reveal
- `handle_chat_message()` - Relay message

### handlers_confession.py
**Anonymous confessions**
- Campus selection
- Department selection
- Confession writing
- Submission to admins
- Coin reward (5 coins)

States:
- `ConfessionState.selecting_campus`
- `ConfessionState.selecting_department`
- `ConfessionState.writing_confession`

Flow:
1. Select campus (inline buttons)
2. Select department (inline buttons)
3. Write confession (text)
4. Submit for approval
5. Admin reviews
6. Posted to channel

### handlers_admin.py
**Moderation & management**
- Confession approval/rejection
- Bot statistics dashboard
- User banning
- Broadcast messaging
- Admin management

Commands:
- `/admin` - Admin panel
- `/broadcast <msg>` - Message all users
- `/set_admin <id>` - Add admin

Functions:
- `admin_confessions()` - Review queue
- `approve_confession()` - Post to channel
- `reject_confession()` - Delete confession
- `admin_stats()` - View metrics
- `broadcast_command()` - Mass message

### handlers_leaderboard.py
**Weekly rankings**
- Most liked users
- Weekly reset
- Top 10 display
- Medal system (🥇🥈🥉)

Functions:
- `show_leaderboard()` - Display rankings
- Queries likes from current week
- Sorts by count

## Data Flow

### User Registration
```
/start → ProfileSetup FSM → Gender → Seeking → Campus →
Department → Year → Name → Bio → Photo → Vibe Quiz →
Create User in DB → Award 120 coins → Main Menu
```

### Matching Flow
```
Find Matches → Get Candidates (filtered) → Show Profile →
Like/Pass → Check Mutual Like → If Match: Create Match,
Award Coins, Notify Both → Continue Browsing
```

### Confession Flow
```
Crush Confession → Select Campus → Select Department →
Write Text → Submit to DB (pending) → Admin Reviews →
Approve → Post to Channel → Update DB (approved)
```

### Chat Flow
```
My Crushes → Select Match → Start Chat → Send Message →
Save to DB → Relay to Other User → Optional: Reveal
Identity (30 coins) → Update Match (revealed=true)
```

## Database Schema

### users
- Profile data
- Coins balance
- Active/banned status
- Vibe score (JSONB)

### likes
- Who liked whom
- Timestamp
- Unique constraint

### matches
- Mutual likes
- Chat active status
- Reveal status
- Ordered user IDs

### chats
- Match-based messages
- Sender ID
- Message text
- Timestamp

### confessions
- Anonymous submissions
- Target campus/dept
- Status (pending/approved/rejected)
- Channel message ID

### referrals
- Referrer → Referred
- Coins awarded
- Unique constraint on referred

### transactions
- User ID
- Amount (+/-)
- Transaction type
- Description

### daily_logins
- User ID
- Login date
- Unique per day

### leaderboard_cache
- Pre-computed stats
- Weekly aggregation
- Performance optimization

## State Management

Uses aiogram FSM (Finite State Machine):
- `ProfileSetup` - Registration flow
- `MatchingState` - Browsing profiles
- `ChatState` - Active chat session
- `ConfessionState` - Confession submission

State data stored in memory during session.

## Error Handling

All modules log to:
- Console (stdout)
- `bot.log` file
- Admin group (critical errors)

Graceful fallbacks for:
- Missing profile photos
- Database connection issues
- Telegram API errors
- Invalid user input
- Rate limiting

## Security Layers

1. **Database**: RLS policies on all tables
2. **Bot**: Service role access only
3. **Moderation**: Admin approval for confessions
4. **Privacy**: Anonymous chat by default
5. **Rate Limiting**: Daily like limits
6. **Validation**: Input sanitization

## Scaling Points

Current bottlenecks:
- Profile image storage (use CDN)
- Notification broadcasting (use queue)
- Leaderboard calculation (cached)

Optimization opportunities:
- Redis caching for hot data
- CDN for profile images
- Message queue for notifications
- Background workers for heavy tasks

## Extension Points

Easy to add:
- New handler routers
- More vibe questions
- Additional filters
- New coin activities
- Custom admin commands
- More notification types

Modular design allows plugging in new features without touching core.

## Testing Strategy

Manual testing checklist:
- [ ] Profile creation flow
- [ ] All inline buttons work
- [ ] Matching algorithm
- [ ] Like/match notifications
- [ ] Chat system
- [ ] Confession approval
- [ ] Coin transactions
- [ ] Referral tracking
- [ ] Leaderboard updates
- [ ] Admin commands

For production:
- Unit tests for utils
- Integration tests for database
- End-to-end tests for flows
- Load testing for scale

## Deployment Options

### Local
```bash
python bot.py
```

### Docker
```bash
docker build -t crushconnect .
docker run -d --env-file .env crushconnect
```

### Render.com
- Push to GitHub
- Connect repo
- Select Docker
- Add env vars
- Deploy

### Other platforms
- Heroku (Dockerfile)
- Railway (Dockerfile)
- DigitalOcean (Docker)
- AWS ECS (Docker)
- Google Cloud Run (Docker)

## Monitoring

Key metrics to track:
- Total users
- Active users (daily/weekly)
- Matches created
- Confessions posted
- Chat activity
- Coin economy balance
- Error rates
- Response times

Tools:
- Bot logs (`bot.log`)
- Admin panel stats
- Database queries
- Telegram bot API stats

## Maintenance Tasks

Daily:
- Review error logs
- Approve confessions
- Monitor user reports
- Check bot uptime

Weekly:
- Update leaderboard
- Review top users
- Analyze engagement
- Adjust coin economy

Monthly:
- Clean old data
- Optimize queries
- Update dependencies
- Plan new features

---

**Built with modular architecture for AAU students! 🚀**
