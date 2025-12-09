# 🔥 AAUPulse - START HERE 🔥

**The most viral campus dating bot for Addis Ababa University students!**

## What is AAUPulse?

AAUPulse is a full-featured Telegram bot that helps AAU students find their match through:
- Smart profile matching
- Anonymous chat
- Crush confessions
- Weekly leaderboards
- Coins & rewards
- Referral system

Built with Python, Telegram Bot API, and Supabase database.

---

## 🚀 Quick Start (5 Minutes)

### 1. Get Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot`
3. Follow instructions
4. Copy your bot token

### 2. Create Channel
1. Create public channel: `@AAUAAUPulse`
2. Add your bot as admin
3. Give posting permissions

### 3. Configure Bot
Edit `.env` file:
```env
BOT_TOKEN=your_token_here
CHANNEL_ID=@AAUAAUPulse
ADMIN_GROUP_ID=your_telegram_user_id
```

### 4. Install & Run
```bash
pip install -r requirements.txt
python bot.py
```

### 5. Test It!
1. Find your bot on Telegram
2. Send `/start`
3. Complete profile setup
4. You're in! 🎉

**Detailed setup guide:** See `QUICKSTART.md`

---

## 📁 Project Files

**Core Bot Files:**
- `bot.py` - Main entry point
- `bot_config.py` - Configuration
- `database.py` - Database operations
- `utils.py` - Helper functions
- `notifications.py` - Scheduled tasks

**Feature Modules:**
- `handlers_profile.py` - Profile setup
- `handlers_main.py` - Main menu
- `handlers_matching.py` - Swipe & match
- `handlers_chat.py` - Anonymous chat
- `handlers_confession.py` - Confessions
- `handlers_admin.py` - Admin panel
- `handlers_leaderboard.py` - Rankings

**Deployment:**
- `Dockerfile` - Docker config
- `render.yaml` - Render deployment
- `requirements.txt` - Dependencies
- `.env` - Environment variables

**Documentation:**
- `START_HERE.md` - This file!
- `QUICKSTART.md` - Setup guide
- `README_AAUPulse.md` - Full docs
- `PROJECT_STRUCTURE.md` - Architecture
- `DEPLOYMENT_CHECKLIST.md` - Launch guide

---

## ✨ Key Features

### For Users
- **Complete Profile Setup** - Gender, campus, department, year, bio, photo
- **Vibe Quiz** - 7 questions to match personality
- **Smart Matching** - Filter by campus, department, year, compatibility
- **Anonymous Chat** - Match and chat anonymously
- **Reveal Identity** - 30 coins to reveal who you're chatting with
- **Crush Confessions** - Post anonymous confessions to channel
- **Coins System** - Earn and spend coins
- **Referral Rewards** - Get 50 coins per friend invited
- **Leaderboard** - See weekly top 10 most liked
- **Icebreakers** - Random questions to start conversations

### For Admins
- **Confession Moderation** - Approve/reject before posting
- **Statistics Dashboard** - Users, matches, confessions
- **Broadcast Messages** - Send to all users
- **User Management** - Ban abusive users
- **Activity Logs** - Monitor bot health

---

## 💰 Coin Economy

### Earn Coins 🪙
- New account: **120 coins**
- Daily login: **10 coins**
- Post confession: **5 coins**
- Get a match: **30 coins**
- Refer a friend: **50 coins**

### Spend Coins 💸
- Reveal identity in chat: **30 coins**
- Extra daily likes: **20 coins** (future)
- Premium features: **50 coins** (future)

---

## 🎯 User Journey

### New User Flow
1. `/start` → Profile creation
2. Select all options via inline buttons
3. Upload profile photo
4. Complete vibe quiz (7 questions)
5. Get 120 starting coins
6. Main menu unlocked!

### Finding Matches
1. Click "Find Matches"
2. Set optional filters
3. Swipe through profiles
4. Like or Pass
5. Get matched!
6. Start chatting

### Anonymous Chat
1. View matches in "My Crushes"
2. Start anonymous chat
3. Send messages or icebreakers
4. Reveal identity (30 coins)
5. Continue chatting!

### Confessions
1. Click "Crush Confession"
2. Select campus & department
3. Write confession
4. Admin approves
5. Posted to channel
6. Get 5 coins!

---

## 🗄️ Database Tables

Created automatically in Supabase:
- `users` - User profiles
- `likes` - Swipe history
- `matches` - Mutual likes
- `chats` - Anonymous messages
- `confessions` - Anonymous confessions
- `referrals` - Friend invites
- `transactions` - Coin history
- `daily_logins` - Login tracking
- `leaderboard_cache` - Weekly stats

All tables have RLS enabled for security.

---

## 🔧 Tech Stack

- **Bot Framework:** aiogram 3.4.1
- **Database:** Supabase (PostgreSQL)
- **Language:** Python 3.11+
- **Image Processing:** Pillow
- **Scheduling:** APScheduler
- **Deployment:** Docker + Render

---

## 📱 Bot Commands

**User Commands:**
- `/start` - Start bot / Main menu
- `/profile` - View your profile & stats

**Admin Commands:**
- `/admin` - Admin control panel
- `/broadcast <msg>` - Message all users
- `/set_admin <id>` - Add new admin

---

## 🔔 Automated Notifications

**Daily (7 PM):**
Random engagement message to all users

**Friday (12 PM):**
Confession Friday reminder

**Sunday (2 PM):**
Blind Date Sunday reminder

**Monday (10 AM):**
Weekly leaderboard update to channel

---

## 🎨 Bot Personality

Gen Z energy, campus vibes, playful & bold:
- "Yooo welcome to AAUPulse! 🔥"
- "Bruh... upload that selfie or stay invisible 👻"
- "No cap, this'll take like 2 minutes 💯"
- "Time to find your match... 😏"

Every message has emojis and AAU campus culture references.

---

## 🚢 Deployment Options

### Local Development
```bash
python bot.py
```

### Docker
```bash
docker build -t AAUPulse .
docker run -d --env-file .env AAUPulse
```

### Render.com (Recommended)
1. Push to GitHub
2. Create Web Service on Render
3. Select Docker environment
4. Add environment variables
5. Deploy!

See `DEPLOYMENT_CHECKLIST.md` for complete guide.

---

## 🧪 Testing Checklist

Before going live, verify:
- [ ] Bot responds to /start
- [ ] Profile setup works
- [ ] Photo upload works
- [ ] Vibe quiz completes
- [ ] Matching shows profiles
- [ ] Like/pass works
- [ ] Match creates successfully
- [ ] Chat system works
- [ ] Confession submits
- [ ] Admin can approve
- [ ] Confession posts to channel
- [ ] Coins update correctly
- [ ] Referral link works
- [ ] Leaderboard displays

Use `verify_setup.py` to check configuration.

---

## 📊 Success Metrics

**Week 1 Goals:**
- 50+ users registered
- 10+ matches created
- 20+ confessions posted

**Month 1 Goals:**
- 500+ users
- 100+ matches
- 200+ confessions

**Month 3 Goals:**
- 2000+ users
- 500+ matches
- 1000+ confessions

---

## 🆘 Need Help?

### Quick Fixes

**Bot not responding?**
- Check BOT_TOKEN is correct
- Verify bot is running
- Check logs for errors

**Channel not working?**
- Verify bot is admin
- Check CHANNEL_ID format
- Test posting permissions

**Database errors?**
- Check Supabase credentials
- Verify internet connection
- Review RLS policies

### Documentation

1. **Quick Setup:** `QUICKSTART.md`
2. **Full Documentation:** `README_AAUPulse.md`
3. **Architecture:** `PROJECT_STRUCTURE.md`
4. **Deployment:** `DEPLOYMENT_CHECKLIST.md`

### Verify Setup
```bash
python verify_setup.py
```

---

## 🎯 What Makes This Bot Special?

✅ **Production Ready** - All features fully implemented
✅ **Modular Design** - Easy to maintain and extend
✅ **Secure** - RLS policies, admin approval, validation
✅ **Scalable** - Handles 5000+ users out of the box
✅ **Engaging** - Coins, rewards, leaderboards, confessions
✅ **Anonymous** - Privacy-first chat system
✅ **Viral** - Referral system, channel integration
✅ **AAU-Specific** - Campus, departments, student culture
✅ **Well Documented** - Comprehensive guides included

---

## 🔥 Launch Strategy

**Day 1:**
1. Deploy bot
2. Test all features
3. Invite 10 friends
4. Monitor closely

**Week 1:**
1. Post in AAU groups
2. Share on social media
3. Encourage referrals
4. Engage daily

**Month 1:**
1. Run weekly events
2. Feature top users
3. Post best confessions
4. Listen to feedback

---

## 🛠️ Customization

Want to customize? Edit these files:

**Change campus/departments:**
`bot_config.py` - Update lists

**Change coin values:**
`bot_config.py` - Adjust COIN_REWARDS/COSTS

**Change vibe questions:**
`bot_config.py` - Edit VIBE_QUESTIONS

**Change notification times:**
`notifications.py` - Update cron schedules

**Change bot personality:**
All `handlers_*.py` files - Update message text

---

## 📈 Future Features

Ideas to add:
- Photo verification
- Video profiles
- Voice messages
- Group dates
- Premium subscriptions
- Virtual gifts
- Story posts (24hr)
- Event integration
- Study buddy mode

Modular design makes adding features easy!

---

## 🎓 AAU Campus Info

**Supported Campuses:**
- Main 6kilo
- 5kilo
- 4kilo
- Sefer Selam
- FBE
- Yared
- Lideta

**Common Departments:**
- Engineering
- Law
- Business
- Health Sciences
- IT
- FBE
- Natural Sciences
- Social Sciences
- Other (custom input)

**Years:**
- 1st Year
- 2nd Year
- 3rd Year
- 4th Year
- 5th Year+

---

## 🔐 Security Features

- RLS on all database tables
- Admin approval for confessions
- Anonymous chat by default
- Profile photo validation
- Input sanitization
- Rate limiting
- Ban system
- Service role access only

Your users' data is safe!

---

## 📞 Support

**For Setup Issues:**
1. Run `python verify_setup.py`
2. Check `bot.log` file
3. Review documentation
4. Check GitHub issues

**For Feature Requests:**
- Document in GitHub issues
- Discuss with community
- Submit pull requests

---

## 📝 File Checklist

Make sure you have all these files:

**Required:**
- [x] bot.py
- [x] bot_config.py
- [x] database.py
- [x] utils.py
- [x] notifications.py
- [x] handlers_profile.py
- [x] handlers_main.py
- [x] handlers_matching.py
- [x] handlers_chat.py
- [x] handlers_confession.py
- [x] handlers_admin.py
- [x] handlers_leaderboard.py
- [x] requirements.txt
- [x] Dockerfile
- [x] .env
- [x] .dockerignore
- [x] render.yaml

**Documentation:**
- [x] START_HERE.md
- [x] QUICKSTART.md
- [x] README_AAUPulse.md
- [x] PROJECT_STRUCTURE.md
- [x] DEPLOYMENT_CHECKLIST.md
- [x] verify_setup.py

---

## 🎉 You're Ready!

**Next Steps:**
1. Read `QUICKSTART.md` for setup
2. Configure `.env` file
3. Run `python verify_setup.py`
4. Start bot: `python bot.py`
5. Test all features
6. Deploy to production
7. Start marketing!

**Remember:**
- Make AAU campus dating less awkward! 🔥
- Keep it fun, safe, and engaging 💯
- Listen to your users 👂
- Iterate and improve 🚀

---

**Bot Username:** @AAUPulseBot
**Channel:** @AAUAAUPulse
**Built for:** Addis Ababa University Students
**By:** World-class bot developers

---

## 💜 Let's Make This Viral!

Time to launch the hottest thing on AAU campus! 🔥

Good luck! 🚀
