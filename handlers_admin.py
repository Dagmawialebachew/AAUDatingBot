from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from database import db
from bot_config import ADMIN_GROUP_ID, CHANNEL_ID
import logging

logger = logging.getLogger(__name__)
router = Router()

# --- Admin IDs ---
ADMIN_IDS = [1131741322]  # Populate with your admin IDs

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# --- Admin Main Menu (Reply Keyboard) ---
def get_admin_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Confessions"), KeyboardButton(text="📊 Stats")],
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="👥 User Management")],
            [KeyboardButton(text="🔙 Exit Admin Mode")]
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="🔐 Admin controls..."
    )

# --- Entry Point ---
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Admin only!")
        return
    await message.answer("🔐 Welcome to the Admin Panel", reply_markup=get_admin_main_menu())

# --- Confessions Panel ---
def get_confessions_panel(confession_id: int = None) -> InlineKeyboardMarkup:
    if confession_id:
        return InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_conf_{confession_id}"),
                InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_conf_{confession_id}")
            ],
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
        ])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])

@router.message(F.text == "📋 Confessions")
async def admin_confessions_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    confessions = await db.get_pending_confessions()
    if not confessions:
        await message.answer("✅ No pending confessions.", reply_markup=get_admin_main_menu())
        return
    confession = confessions[0]
    text = (
        f"📋 Confession Review (ID: {confession['id']})\n\n"
        f"Campus: {confession.get('campus', 'N/A')}\n"
        f"Department: {confession.get('department', 'N/A')}\n\n"
        f"💭 {confession['text']}\n\n"
        f"Pending confessions: {len(confessions)}"
    )
    await message.answer(text, reply_markup=get_confessions_panel(confession['id']))

@router.callback_query(F.data.startswith("approve_conf_"))
async def approve_confession(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    confession_id = int(callback.data.split("_")[-1])
    confession = await db.get_confession(confession_id)
    if not confession:
        return await callback.answer("Confession not found 💀")

    channel_text = (
        f"💌 Anonymous Confession 💌\n\n"
        f"📍 Campus: {confession.get('campus', 'AAU')}\n"
        f"📚 Department: {confession.get('department', 'Unknown')}\n\n"
        f"{confession['text']}\n\n"
        f"Is this about you? React with ❤️\n\n"
        f"@CrushConnectBot"
    )
    try:
        sent = await callback.bot.send_message(CHANNEL_ID, channel_text)
        await db.update_confession_status(confession_id, 'approved', sent.message_id)
        await callback.answer("✅ Approved & posted!")
    except Exception as e:
        logger.error(f"Error posting confession: {e}")
        await callback.answer("Failed to post 💀")

@router.callback_query(F.data.startswith("reject_conf_"))
async def reject_confession(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer("⛔️ Admin only!")
    confession_id = int(callback.data.split("_")[-1])
    await db.update_confession_status(confession_id, 'rejected')
    await callback.answer("❌ Rejected")

# --- Stats Panel ---
@router.message(F.text == "📊 Stats")
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    stats = await db.get_global_stats()
    text = (
        f"📊 Bot Statistics\n\n"
        f"👥 Total Users: {stats['total_users']}\n"
        f"✅ Active Users: {stats['active_users']}\n"
        f"🔥 Total Matches: {stats['total_matches']}\n"
        f"💌 Total Confessions: {stats['total_confessions']}\n"
        f"⏳ Pending Confessions: {stats['pending_confessions']}\n"
    )
    await message.answer(text, reply_markup=get_admin_main_menu())

# --- Broadcast ---
@router.message(F.text == "📢 Broadcast")
async def broadcast_prompt(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("✍️ Send me the broadcast message text:")

@router.message(F.text.startswith("BROADCAST:"))
async def broadcast_message(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("BROADCAST:", "").strip()
    user_ids = await db.get_all_active_user_ids()
    success, fail = 0, 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, text)
            success += 1
        except:
            fail += 1
    await message.answer(f"✅ Broadcast complete!\nSuccess: {success}\nFailed: {fail}")

# --- User Management ---
def get_user_management_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Activate User", callback_data="admin_user_activate")],
        [InlineKeyboardButton(text="⏸️ Deactivate User", callback_data="admin_user_deactivate")],
        [InlineKeyboardButton(text="🗑️ Delete User", callback_data="admin_user_delete")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_back")]
    ])

@router.message(F.text == "👥 User Management")
async def user_management_menu(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("👥 User Management Panel", reply_markup=get_user_management_panel())

@router.callback_query(F.data == "admin_user_activate")
async def activate_user(callback: CallbackQuery):
    await callback.message.answer("Enter user ID to activate:")
    await callback.answer()

@router.callback_query(F.data == "admin_user_deactivate")
async def deactivate_user(callback: CallbackQuery):
    await callback.message.answer("Enter user ID and reason to deactivate (format: ID | reason):")
    await callback.answer()

@router.callback_query(F.data == "admin_user_delete")
async def delete_user(callback: CallbackQuery):
    await callback.message.answer("Enter user ID to permanently delete:")
    await callback.answer()

# --- Back ---
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    await callback.message.answer("🔐 Back to Admin Menu", reply_markup=get_admin_main_menu())
    await callback.answer()
