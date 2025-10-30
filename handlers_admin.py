from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from bot_config import ADMIN_GROUP_ID, CHANNEL_ID
import logging

logger = logging.getLogger(__name__)
router = Router()

# IMPORTANT: You must populate this list with the Telegram user IDs of your administrators.
ADMIN_IDS = [1131741322] 

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Admin only!")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Pending Confessions", callback_data="admin_confessions")],
        [InlineKeyboardButton(text="📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🚫 Ban User", callback_data="admin_ban")]
    ])

    await message.answer(
        "🔐 Admin Panel\n\n"
        "What do you want to do?",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "admin_confessions")
async def admin_view_confessions(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin only!")
        return

    # 🔄 REPLACED: Supabase logic is handled inside db.get_pending_confessions()
    confessions = await db.get_pending_confessions()

    if not confessions:
        await callback.message.edit_text(
            "No pending confessions! ✅",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
            ])
        )
        await callback.answer()
        return

    confession = confessions[0]

    # NOTE: Using the correct keys based on your database.py schema ('campus', 'department', 'text')
    text = (
        f"📋 Confession Review (ID: {confession['id']})\n\n"
        f"Campus: {confession.get('campus', 'N/A')}\n"
        f"Department: {confession.get('department', 'N/A')}\n\n"
        f"💭 {confession['text']}\n\n"
        f"Pending confessions: {len(confessions)}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_conf_{confession['id']}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_conf_{confession['id']}")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("approve_conf_"))
async def approve_confession(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin only!")
        return

    confession_id_str = callback.data.split("approve_conf_")[1]
    confession_id = int(confession_id_str)

    # 🔄 REPLACED: Supabase fetch with new async method
    confession = await db.get_confession(confession_id)

    if not confession:
        await callback.answer("Confession not found 💀")
        return

    # NOTE: Using the correct keys based on your database.py schema ('campus', 'department', 'text')
    channel_text = (
        f"💌 Anonymous Confession 💌\n\n"
        f"📍 Campus: {confession.get('campus', 'AAU')}\n"
        f"📚 Department: {confession.get('department', 'Unknown')}\n\n"
        f"{confession['text']}\n\n"
        f"Is this about you? React with ❤️\n\n"
        f"@CrushConnectBot"
    )

    try:
        sent_message = await callback.bot.send_message(
            CHANNEL_ID,
            channel_text
        )

        # 🔄 REPLACED: db.update_confession_status call is already correct
        await db.update_confession_status(confession_id, 'approved', sent_message.message_id)

        await callback.answer("Confession approved and posted! ✅")
        # Go to the next pending confession
        await admin_view_confessions(callback)

    except Exception as e:
        logger.error(f"Error posting to channel: {e}")
        await callback.answer("Failed to post to channel 💀")

@router.callback_query(F.data.startswith("reject_conf_"))
async def reject_confession(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin only!")
        return

    confession_id_str = callback.data.split("reject_conf_")[1]
    confession_id = int(confession_id_str)

    # 🔄 REPLACED: db.update_confession_status call is already correct
    await db.update_confession_status(confession_id, 'rejected')

    await callback.answer("Confession rejected ❌")
    # Go to the next pending confession
    await admin_view_confessions(callback)

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔️ Admin only!")
        return

    try:
        # 🔄 REPLACED: Multiple Supabase calls with a single async method
        stats = await db.get_global_stats()
        
        text = (
            f"📊 Bot Statistics\n\n"
            f"👥 Total Users: {stats['total_users']}\n"
            f"✅ Active Users: {stats['active_users']}\n"
            f"🔥 Total Matches: {stats['total_matches']}\n"
            f"💌 Total Confessions: {stats['total_confessions']}\n"
            f"⏳ Pending Confessions: {stats['pending_confessions']}\n"
        )

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_stats")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
            ])
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await callback.answer("Error getting stats 💀")

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    # Pass the message object to admin_panel, not the callback message
    await admin_panel(callback.message)
    await callback.answer()

@router.message(Command("broadcast"))
async def broadcast_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Admin only!")
        return

    if len(message.text.split(maxsplit=1)) < 2:
        await message.answer(
            "Usage: /broadcast <message>\n\n"
            "This will send the message to all active users."
        )
        return

    broadcast_text = message.text.split(maxsplit=1)[1]

    # 🔄 REPLACED: Supabase user fetch with new async method
    user_ids = await db.get_all_active_user_ids()
    
    success_count = 0
    fail_count = 0

    await message.answer(f"Starting broadcast to {len(user_ids)} users...")

    for user_id in user_ids:
        try:
            # Loop through IDs directly
            await message.bot.send_message(user_id, broadcast_text)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
            fail_count += 1

    await message.answer(
        f"✅ Broadcast complete!\n\n"
        f"Success: {success_count}\n"
        f"Failed: {fail_count}"
    )

@router.message(Command("set_admin"))
async def set_admin_command(message: Message):
    if message.from_user.id not in ADMIN_IDS and len(ADMIN_IDS) > 0:
        await message.answer("⛔️ Only existing admins can add new admins!")
        return

    if len(message.text.split()) < 2:
        await message.answer("Usage: /set_admin <user_id>")
        return

    try:
        new_admin_id = int(message.text.split()[1])
        if new_admin_id not in ADMIN_IDS:
            ADMIN_IDS.append(new_admin_id)
            await message.answer(f"✅ User {new_admin_id} is now an admin! (Will reset on bot restart)")
        else:
            await message.answer("User is already an admin!")
    except ValueError:
        await message.answer("Invalid user ID!")