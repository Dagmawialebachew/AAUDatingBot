# CrushConnect - Deployment Checklist

## Pre-Deployment Setup

### 1. Telegram Bot Configuration

- [ ] Created bot via @BotFather
- [ ] Saved bot token
- [ ] Set bot username (e.g., @CrushConnectBot)
- [ ] Set bot description and about text
- [ ] Set bot profile picture (optional)

**Commands to set:**
```
/setdescription @BotFather
Description: The hottest way for AAU students to find their match! 🔥

/setabouttext @BotFather
About: CrushConnect is the official AAU campus dating bot. Swipe, match, chat anonymously, and shoot your shot! 💘
```

### 2. Channel Setup

- [ ] Created public channel @AAUCrushConnect
- [ ] Added bot as administrator
- [ ] Gave bot permission to post messages
- [ ] Posted welcome message to channel
- [ ] Set channel description

**Welcome message:**
```
Welcome to AAU CrushConnect! 💘

This is where AAU students:
🔥 Find their match
💌 Post anonymous confessions
🏆 See weekly leaderboards
😍 Discover campus crushes

Start swiping: @CrushConnectBot
```

### 3. Environment Variables

- [ ] BOT_TOKEN - From @BotFather
- [ ] CHANNEL_ID - @AAUCrushConnect
- [ ] ADMIN_GROUP_ID - Your Telegram user ID
- [ ] VITE_SUPABASE_URL - Already configured
- [ ] VITE_SUPABASE_ANON_KEY - Already configured

### 4. Database

- [x] Schema created (users, likes, matches, chats, confessions, etc.)
- [x] RLS policies enabled
- [x] Indexes created for performance
- [ ] Verified database connection works

### 5. Admin Setup

- [ ] Got your Telegram user ID from @userinfobot
- [ ] Set first admin with `/set_admin YOUR_ID`
- [ ] Tested admin panel access
- [ ] Can approve confessions
- [ ] Can view statistics

## Local Testing Checklist

### Basic Functionality
- [ ] Bot responds to /start
- [ ] Profile setup flow works
- [ ] All inline buttons respond
- [ ] Photo upload works
- [ ] Vibe quiz completes
- [ ] Profile creation succeeds
- [ ] User gets 120 starting coins

### Matching System
- [ ] "Find Matches" shows profiles
- [ ] Like button works
- [ ] Pass button works
- [ ] Filters work (campus/dept/year)
- [ ] Match notification appears
- [ ] Both users notified of match
- [ ] 30 coins awarded per match

### Chat System
- [ ] Can view matches in "My Crushes"
- [ ] Can start anonymous chat
- [ ] Messages send successfully
- [ ] Other user receives messages
- [ ] Icebreaker button works
- [ ] Reveal identity costs 30 coins
- [ ] Identity reveal works for both users

### Confession System
- [ ] Can submit confession
- [ ] Confession appears in admin panel
- [ ] Admin can approve confession
- [ ] Approved confession posts to channel
- [ ] User gets 5 coins for posting
- [ ] Can reject confession

### Coins & Rewards
- [ ] Daily login gives 10 coins
- [ ] Profile creation gives 120 coins
- [ ] Confession gives 5 coins
- [ ] Match gives 30 coins
- [ ] Referral gives 50 coins
- [ ] Coin balance updates correctly
- [ ] Spending coins works

### Referral System
- [ ] Referral link generates
- [ ] New user can use referral link
- [ ] Referrer gets 50 coins
- [ ] Referral count updates

### Leaderboard
- [ ] Leaderboard displays top users
- [ ] Weekly data shows correctly
- [ ] Medals show (🥇🥈🥉)
- [ ] Updates when likes change

### Admin Panel
- [ ] /admin shows admin menu
- [ ] Can view pending confessions
- [ ] Can approve/reject confessions
- [ ] Statistics display correctly
- [ ] Can broadcast messages
- [ ] Broadcast reaches users

### Notifications (if time allows)
- [ ] Daily notification scheduled
- [ ] Friday confession reminder works
- [ ] Sunday match reminder works
- [ ] Monday leaderboard posts

## Deployment Steps

### Option 1: Render.com (Recommended)

1. **Prepare Repository**
```bash
git init
git add .
git commit -m "Initial CrushConnect deployment"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

2. **Deploy on Render**
- [ ] Created Render account
- [ ] Connected GitHub repository
- [ ] Created new Web Service
- [ ] Selected "Docker" environment
- [ ] Set region (closest to users)
- [ ] Added all environment variables
- [ ] Clicked "Create Web Service"
- [ ] Waited for deployment (5-10 min)
- [ ] Checked logs for "Bot startup complete!"

3. **Verify Deployment**
- [ ] Bot responds in Telegram
- [ ] All features work
- [ ] No errors in Render logs

### Option 2: Local/VPS Deployment

1. **Server Setup**
```bash
# Clone repository
git clone YOUR_REPO_URL
cd crushconnect-bot

# Install dependencies
pip install -r requirements.txt

# Set up .env file
nano .env
# Add all environment variables

# Test run
python bot.py
```

2. **Run as Service** (systemd example)
```bash
sudo nano /etc/systemd/system/crushconnect.service
```

Add:
```ini
[Unit]
Description=CrushConnect Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/crushconnect-bot
ExecStart=/usr/bin/python3 /path/to/crushconnect-bot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable crushconnect
sudo systemctl start crushconnect
sudo systemctl status crushconnect
```

### Option 3: Docker

```bash
# Build image
docker build -t crushconnect-bot .

# Run container
docker run -d \
  --name crushconnect \
  --env-file .env \
  --restart unless-stopped \
  crushconnect-bot

# Check logs
docker logs -f crushconnect
```

## Post-Deployment Tasks

### Immediate (Day 1)
- [ ] Test all features in production
- [ ] Set up monitoring
- [ ] Create admin group for logs
- [ ] Invite test users
- [ ] Monitor error logs
- [ ] Test confession approval
- [ ] Verify channel posting works

### First Week
- [ ] Monitor user registrations
- [ ] Review confession queue daily
- [ ] Check database performance
- [ ] Monitor coin economy balance
- [ ] Gather user feedback
- [ ] Fix any critical bugs
- [ ] Adjust notification times if needed

### Ongoing Maintenance
- [ ] Daily: Review error logs
- [ ] Daily: Approve confessions
- [ ] Weekly: Check statistics
- [ ] Weekly: Post leaderboard
- [ ] Monthly: Update dependencies
- [ ] Monthly: Analyze engagement
- [ ] Monthly: Plan new features

## Marketing & Launch

### Pre-Launch
- [ ] Create promotional graphics
- [ ] Write announcement post
- [ ] Identify influencers on campus
- [ ] Create Instagram/Twitter accounts (optional)
- [ ] Prepare FAQ document

### Launch Day
- [ ] Post in AAU student groups
- [ ] Share on social media
- [ ] Ask friends to share
- [ ] Monitor closely for issues
- [ ] Be ready for quick fixes

### Growth Strategy
- [ ] Encourage referrals (50 coins!)
- [ ] Post best confessions to social
- [ ] Run weekly contests
- [ ] Feature top users
- [ ] Engage with community
- [ ] Listen to feedback

## Troubleshooting Guide

### Bot not responding
1. Check bot token is correct
2. Verify bot is running (check logs)
3. Test with /start command
4. Check Telegram API status

### Channel not receiving posts
1. Verify bot is admin in channel
2. Check bot has posting permissions
3. Verify CHANNEL_ID format (@username)
4. Test with manual post

### Database errors
1. Check Supabase URL and key
2. Verify internet connection
3. Check RLS policies
4. Review query logs

### Matches not working
1. Need at least 2 users
2. Check gender preferences
3. Verify users aren't banned
4. Check likes table

### Coins not updating
1. Check transaction logs
2. Verify database writes
3. Test with manual coin addition
4. Review coin economy logic

### Notifications not sending
1. Check scheduler is running
2. Verify time zones
3. Test with manual trigger
4. Check user count

## Monitoring & Metrics

### Key Metrics to Track
- Total users
- Daily active users
- Matches per day
- Confessions per day
- Coin transactions
- Error rate
- Response time
- Retention rate

### Tools
- Render logs (production)
- bot.log file
- Admin panel statistics
- Database queries
- Telegram bot API insights

### Alerts to Set Up
- Bot goes offline
- Error rate spike
- Database connection issues
- Low coin balance (economy check)
- Spam/abuse reports

## Success Criteria

### Week 1
- [ ] 50+ registered users
- [ ] 10+ matches created
- [ ] 20+ confessions posted
- [ ] No critical bugs
- [ ] Positive user feedback

### Month 1
- [ ] 500+ registered users
- [ ] 100+ matches created
- [ ] 200+ confessions posted
- [ ] Active daily engagement
- [ ] Growing organically

### Month 3
- [ ] 2000+ registered users
- [ ] 500+ matches created
- [ ] 1000+ confessions posted
- [ ] Community established
- [ ] Self-sustaining growth

## Emergency Contacts

- Bot Developer: [Your contact]
- Database Admin: [Supabase support]
- Telegram Support: @BotSupport
- Server Host: [Render/VPS support]

## Backup & Recovery

### Regular Backups
- [ ] Database backup weekly
- [ ] Code repository up to date
- [ ] Environment variables documented
- [ ] User data export capability

### Recovery Plan
1. Restore from last database backup
2. Redeploy bot from repository
3. Verify environment variables
4. Test all critical features
5. Notify users of downtime

---

## Launch Checklist Summary

**Before Launch:**
- [x] All features implemented
- [x] Database schema created
- [ ] Local testing complete
- [ ] Environment variables set
- [ ] Bot and channel configured
- [ ] Admin access verified

**Launch Day:**
- [ ] Deploy to production
- [ ] Verify everything works
- [ ] Start marketing
- [ ] Monitor closely

**First Week:**
- [ ] Approve confessions daily
- [ ] Monitor for bugs
- [ ] Engage with users
- [ ] Gather feedback

---

**You're ready to launch! 🚀**

Make AAU campus dating legendary! 🔥
