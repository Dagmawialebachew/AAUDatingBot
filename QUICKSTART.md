# CrushConnect - Quick Start Guide

## Step 1: Get Your Bot Token

1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a name: `CrushConnect`
4. Choose a username: `CrushConnectBot` (or any available name ending in 'bot')
5. Copy the bot token (looks like: `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`)

## Step 2: Create Your Channel

1. Create a new Telegram channel
2. Make it public with username: `AAUCrushConnect`
3. Add your bot as admin with posting permissions

## Step 3: Get Your User ID

1. Message [@userinfobot](https://t.me/userinfobot)
2. It will reply with your user ID (a number like `123456789`)

## Step 4: Configure Environment

Edit `.env` file and update:

```env
BOT_TOKEN=paste_your_bot_token_here
CHANNEL_ID=@AAUCrushConnect
ADMIN_GROUP_ID=paste_your_user_id_here
```

## Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 6: Run the Bot

```bash
python bot.py
```

You should see:
```
Bot is starting up...
Bot startup complete!
Starting bot polling...
```

## Step 7: Set Yourself as Admin

1. Open Telegram and find your bot
2. Send: `/start`
3. The bot will guide you through profile setup
4. After setup, send: `/set_admin YOUR_USER_ID`
5. You now have admin access!

## Step 8: Test Features

### Test Profile Setup
- Complete your profile
- Upload a photo
- Answer vibe quiz questions

### Test Matching
- Click "Find Matches"
- You'll need another user to test fully
- Use a second Telegram account for testing

### Test Confessions
- Click "Crush Confession"
- Submit a confession
- Use `/admin` to approve it
- Check your channel to see it posted

### Test Admin Panel
- Send `/admin`
- Review pending confessions
- Check bot statistics
- Test broadcast (carefully!)

## Common Issues

### Bot doesn't respond
- Check BOT_TOKEN is correct
- Make sure bot is running (`python bot.py`)
- Check for errors in console

### Channel posting fails
- Make sure bot is admin in channel
- Check CHANNEL_ID is correct (starts with @)
- Verify channel username matches

### Database errors
- Supabase is already configured
- Check internet connection
- Verify VITE_SUPABASE_URL and KEY are set

## Deploy to Render

1. Push code to GitHub:
```bash
git init
git add .
git commit -m "CrushConnect bot"
git remote add origin YOUR_GITHUB_REPO
git push -u origin main
```

2. Go to [Render.com](https://render.com)
3. Create new Web Service
4. Connect your GitHub repo
5. Select "Docker" environment
6. Add environment variables from `.env`
7. Deploy!

## Environment Variables for Render

```
BOT_TOKEN=your_bot_token
CHANNEL_ID=@AAUCrushConnect
ADMIN_GROUP_ID=your_user_id
VITE_SUPABASE_URL=already_in_env_file
VITE_SUPABASE_ANON_KEY=already_in_env_file
```

## What's Next?

1. Invite friends to test the bot
2. Monitor admin panel for stats
3. Review and approve confessions
4. Check channel engagement
5. Adjust notification times in `notifications.py` if needed
6. Promote bot on AAU campus!

## Bot Commands Reference

- `/start` - Start bot / Main menu
- `/profile` - View your profile
- `/admin` - Admin panel
- `/set_admin <user_id>` - Add admin (admin only)
- `/broadcast <message>` - Send to all users (admin only)

## Need Help?

Check the full README_CRUSHCONNECT.md for detailed documentation.

Common issues:
- Profile photo not showing? Make sure image upload succeeded
- Match not working? Need at least 2 users with compatible preferences
- Confession not posting? Admin must approve first
- Notifications not sending? Check scheduler is running

## Testing Checklist

- [ ] Bot responds to /start
- [ ] Profile setup works (all inline buttons)
- [ ] Photo upload works
- [ ] Vibe quiz completes
- [ ] Main menu displays
- [ ] Coins show correctly (120 start)
- [ ] Can submit confession
- [ ] Admin can approve confession
- [ ] Confession posts to channel
- [ ] Matching shows profiles
- [ ] Like/pass works
- [ ] Match creates (with 2 users)
- [ ] Chat system works
- [ ] Reveal identity works
- [ ] Leaderboard updates
- [ ] Daily login gives coins
- [ ] Referral link works

---

**You're ready to launch! 🚀**

Make AAU campus dating less awkward! 🔥
